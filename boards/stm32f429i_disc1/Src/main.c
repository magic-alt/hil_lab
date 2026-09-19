#include <stdint.h>

#include "pwm_profile.h"
#include "stm32f429_regs.h"

extern uint32_t SystemCoreClock;

#define CLOCK_SOURCE_NONE          (0UL)
#define CLOCK_SOURCE_HSE_XTAL_PLL  (1UL)

#define CLOCK_FAULT_HSI_TIMEOUT    (1UL << 0)
#define CLOCK_FAULT_HSE_TIMEOUT    (1UL << 1)
#define CLOCK_FAULT_PLL_TIMEOUT    (1UL << 2)
#define CLOCK_FAULT_OD_TIMEOUT     (1UL << 3)
#define CLOCK_FAULT_ODSW_TIMEOUT   (1UL << 4)
#define CLOCK_FAULT_SWITCH_TIMEOUT (1UL << 5)

#define CLOCK_WAIT_LOOPS (1000000UL)

static void status_gpio_init(void);
static uint32_t clock_init(void)
{
    g_clock_fault_flags = 0UL;
    g_clock_source = CLOCK_SOURCE_NONE;
    g_sysclk_hz = HIL_HSI_HZ;

    /*
     * Reset starts from HSI. Keep it enabled only as the boot clock while the
     * MB1075-F429I-E01 board's X3 8 MHz crystal is qualified.
     */
    RCC_CR |= RCC_CR_HSION;
    if (wait_rcc_cr_set(RCC_CR_HSIRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_HSI_TIMEOUT;
        fail_stop();
    }

    RCC_APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC_APB1ENR;

    PWR_CR = (PWR_CR & ~(3UL << 14)) | PWR_CR_VOS_SCALE1;

    FLASH_ACR =
        FLASH_ACR_LATENCY_5WS |
        FLASH_ACR_PRFTEN |
        FLASH_ACR_ICEN |
        FLASH_ACR_DCEN;

    /*
     * Timing qualification reference:
     * MB1075-F429I-E01 uses the onboard X3 8 MHz crystal on PH0/PH1.
     * HSEBYP must be 0 for crystal/ceramic-resonator mode. A missing HSE is a
     * hard failure: silently falling back to HSI would invalidate PWM period
     * and dead-time measurements.
     */
    RCC_CR &= ~RCC_CR_HSEON;
    if (wait_rcc_cr_clear(RCC_CR_HSERDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_HSE_TIMEOUT;
        fail_stop();
    }

    RCC_CR &= ~RCC_CR_HSEBYP;
    RCC_CR |= RCC_CR_HSEON;
    if (wait_rcc_cr_set(RCC_CR_HSERDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_HSE_TIMEOUT;
        fail_stop();
    }

    RCC_CR &= ~RCC_CR_PLLON;
    if (wait_rcc_cr_clear(RCC_CR_PLLRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_PLL_TIMEOUT;
        fail_stop();
    }

    RCC_PLLCFGR =
        (8UL << 0) |
        (360UL << 6) |
        (0UL << 16) |
        RCC_PLLCFGR_PLLSRC_HSE |
        (7UL << 24);

    RCC_CR |= RCC_CR_PLLON;
    if (wait_rcc_cr_set(RCC_CR_PLLRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_PLL_TIMEOUT;
        fail_stop();
    }

    PWR_CR |= PWR_CR_ODEN;
    if (wait_pwr_csr_set(PWR_CSR_ODRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_OD_TIMEOUT;
        fail_stop();
    }

    PWR_CR |= PWR_CR_ODSWEN;
    if (wait_pwr_csr_set(PWR_CSR_ODSWRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_ODSW_TIMEOUT;
        fail_stop();
    }

    RCC_CFGR =
        (RCC_CFGR &
         ~(RCC_CFGR_SW_MASK |
           RCC_CFGR_HPRE_MASK |
           RCC_CFGR_PPRE1_MASK |
           RCC_CFGR_PPRE2_MASK)) |
        RCC_CFGR_PPRE1_DIV4 |
        RCC_CFGR_PPRE2_DIV2 |
        RCC_CFGR_SW_PLL;

    if (wait_sysclk_pll() == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_SWITCH_TIMEOUT;
        fail_stop();
    }

    SystemCoreClock = HIL_PLL_SYSCLK_HZ;
    g_sysclk_hz = HIL_PLL_SYSCLK_HZ;
    g_clock_source = CLOCK_SOURCE_HSE_XTAL_PLL;

    /*
     * APB2 is SYSCLK/2, and STM32F4 timer clocks double APB clocks when the
     * APB prescaler is greater than 1. TIM8 is therefore exactly referenced
     * to the 180 MHz HSE-derived PLL clock tree.
     */
    return HIL_PLL_SYSCLK_HZ;
}

static void pwm_gpio_init(void);
static void tim8_pwm_init(uint32_t timer_clock_hz);
static uint32_t deadtime_ns_to_dtg(uint32_t deadtime_ns, uint32_t timer_hz);
static uint32_t dtg_to_ticks(uint32_t dtg);
static void fail_stop(void);

volatile uint32_t g_boot_stage;
volatile uint32_t g_pwm_profile_id = PWM_PROFILE_ID;
volatile uint32_t g_pwm_frequency_hz = PWM_FREQUENCY_HZ;
volatile uint32_t g_pwm_duty_permille = PWM_DUTY_PERMILLE;
volatile uint32_t g_pwm_deadtime_ns = PWM_DEADTIME_NS;
volatile uint32_t g_pwm_deadtime_dtg;
volatile uint32_t g_pwm_deadtime_actual_ns;
volatile uint32_t g_pwm_period_ticks;
volatile uint32_t g_pwm_ccr1;
volatile uint32_t g_clock_source;
volatile uint32_t g_clock_fault_flags;
volatile uint32_t g_sysclk_hz;
volatile uint32_t g_tim8_clock_hz;
volatile uint32_t g_tim8_cr1_snapshot;
volatile uint32_t g_tim8_ccer_snapshot;
volatile uint32_t g_tim8_bdtr_snapshot;

static uint32_t div_round_closest_u64(uint64_t numerator, uint64_t denominator)
{
    return (uint32_t)((numerator + (denominator / 2ULL)) / denominator);
}

static uint32_t wait_rcc_cr_set(uint32_t mask)
{
    uint32_t timeout = CLOCK_WAIT_LOOPS;

    while (((RCC_CR & mask) == 0UL) && (timeout-- != 0UL)) {
    }

    return ((RCC_CR & mask) != 0UL) ? 1UL : 0UL;
}

static uint32_t wait_rcc_cr_clear(uint32_t mask)
{
    uint32_t timeout = CLOCK_WAIT_LOOPS;

    while (((RCC_CR & mask) != 0UL) && (timeout-- != 0UL)) {
    }

    return ((RCC_CR & mask) == 0UL) ? 1UL : 0UL;
}

static uint32_t wait_pwr_csr_set(uint32_t mask)
{
    uint32_t timeout = CLOCK_WAIT_LOOPS;

    while (((PWR_CSR & mask) == 0UL) && (timeout-- != 0UL)) {
    }

    return ((PWR_CSR & mask) != 0UL) ? 1UL : 0UL;
}

static uint32_t wait_sysclk_pll(void)
{
    uint32_t timeout = CLOCK_WAIT_LOOPS;

    while (((RCC_CFGR & RCC_CFGR_SWS_MASK) != RCC_CFGR_SWS_PLL) &&
           (timeout-- != 0UL)) {
    }

    return ((RCC_CFGR & RCC_CFGR_SWS_MASK) == RCC_CFGR_SWS_PLL) ? 1UL : 0UL;
}

/*
 * STM32F429 RM0090 TIMx_BDTR.DTG encoding with CKD=DIV1.
 */
static uint32_t deadtime_ns_to_dtg(uint32_t deadtime_ns, uint32_t timer_hz)
{
    uint32_t ticks = div_round_closest_u64(
        (uint64_t)deadtime_ns * (uint64_t)timer_hz,
        1000000000ULL);

    if (ticks <= 127U) {
        return ticks;
    }

    if (ticks <= 254U) {
        uint32_t scaled = (ticks + 1U) / 2U;
        if (scaled < 64U) {
            scaled = 64U;
        }
        if (scaled > 127U) {
            scaled = 127U;
        }
        return 0x80U | (scaled - 64U);
    }

    if (ticks <= 504U) {
        uint32_t scaled = (ticks + 4U) / 8U;
        if (scaled < 32U) {
            scaled = 32U;
        }
        if (scaled > 63U) {
            scaled = 63U;
        }
        return 0xC0U | (scaled - 32U);
    }

    {
        uint32_t scaled = (ticks + 8U) / 16U;
        if (scaled < 32U) {
            scaled = 32U;
        }
        if (scaled > 63U) {
            scaled = 63U;
        }
        return 0xE0U | (scaled - 32U);
    }
}

static uint32_t dtg_to_ticks(uint32_t dtg)
{
    if ((dtg & 0x80U) == 0U) {
        return dtg;
    }
    if ((dtg & 0xC0U) == 0x80U) {
        return (64U + (dtg & 0x3FU)) * 2U;
    }
    if ((dtg & 0xE0U) == 0xC0U) {
        return (32U + (dtg & 0x1FU)) * 8U;
    }
    return (32U + (dtg & 0x1FU)) * 16U;
}

int main(void)
{
    g_boot_stage = 1UL;

    /*
     * Configure LEDs before the high-speed clock tree. Red means boot/clock
     * fallback; green means TIM8 PWM has reached the active state.
     */
    status_gpio_init();
    g_boot_stage = 2UL;

    g_tim8_clock_hz = clock_init();
    g_boot_stage = 3UL;

    pwm_gpio_init();
    g_boot_stage = 4UL;

    tim8_pwm_init(g_tim8_clock_hz);
    g_boot_stage = 5UL;

    /* Green = qualified X3/HSE PWM active; red stays off only on that path. */
    GPIO_ODR(GPIOG_BASE) |= (1UL << 13);
    if (g_clock_source == CLOCK_SOURCE_HSE_XTAL_PLL) {
        GPIO_ODR(GPIOG_BASE) &= ~(1UL << 14);
    } else {
        fail_stop();
    }

    for (;;) {
        cpu_wfi();
    }
}

static void status_gpio_init(void)
{
    uint32_t value;

    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOGEN;
    (void)RCC_AHB1ENR;

    value = GPIO_MODER(GPIOG_BASE);
    value &= ~((3UL << (13U * 2U)) | (3UL << (14U * 2U)));
    value |=  ((1UL << (13U * 2U)) | (1UL << (14U * 2U)));
    GPIO_MODER(GPIOG_BASE) = value;

    GPIO_OTYPER(GPIOG_BASE) &= ~((1UL << 13) | (1UL << 14));
    GPIO_PUPDR(GPIOG_BASE) &=
        ~((3UL << (13U * 2U)) | (3UL << (14U * 2U)));

    /* Booting: red on, green off. */
    GPIO_ODR(GPIOG_BASE) &= ~(1UL << 13);
    GPIO_ODR(GPIOG_BASE) |=  (1UL << 14);
}

static uint32_t clock_init(void)
{
    uint32_t pll_m;
    uint32_t use_hse;

    g_clock_fault_flags = 0UL;
    g_clock_source = CLOCK_SOURCE_HSI_DIRECT;
    g_sysclk_hz = HIL_HSI_HZ;

    /*
     * HSI is the guaranteed reset clock. Keep it enabled as the recovery path
     * even when the preferred ST-LINK MCO/HSE input is available.
     */
    RCC_CR |= RCC_CR_HSION;
    if (wait_rcc_cr_set(RCC_CR_HSIRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_HSI_TIMEOUT;
        fail_stop();
    }

    RCC_APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC_APB1ENR;

    PWR_CR = (PWR_CR & ~(3UL << 14)) | PWR_CR_VOS_SCALE1;

    FLASH_ACR =
        FLASH_ACR_LATENCY_5WS |
        FLASH_ACR_PRFTEN |
        FLASH_ACR_ICEN |
        FLASH_ACR_DCEN;

    /*
     * Preferred clock:
     * STM32F429I-DISC1 factory routing can supply fixed 8 MHz ST-LINK MCO to
     * PH0/OSC_IN. A modified board may not have that solder-bridge route, so
     * HSE readiness is optional rather than a fatal boot condition.
     */
    RCC_CR &= ~RCC_CR_HSEON;
    RCC_CR |= RCC_CR_HSEBYP;
    RCC_CR |= RCC_CR_HSEON;

    use_hse = wait_rcc_cr_set(RCC_CR_HSERDY);
    if (use_hse != 0UL) {
        pll_m = 8UL;
        g_clock_source = CLOCK_SOURCE_HSE_PLL;
    } else {
        pll_m = 16UL;
        g_clock_source = CLOCK_SOURCE_HSI_PLL;
        g_clock_fault_flags |= CLOCK_FAULT_HSE_TIMEOUT;
    }

    RCC_CR &= ~RCC_CR_PLLON;
    {
        uint32_t timeout = CLOCK_WAIT_LOOPS;
        while (((RCC_CR & RCC_CR_PLLRDY) != 0UL) && (timeout-- != 0UL)) {
        }
    }

    RCC_PLLCFGR =
        (pll_m << 0) |
        (360UL << 6) |
        (0UL << 16) |
        ((use_hse != 0UL) ? RCC_PLLCFGR_PLLSRC_HSE : 0UL) |
        (7UL << 24);

    RCC_CR |= RCC_CR_PLLON;
    if (wait_rcc_cr_set(RCC_CR_PLLRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_PLL_TIMEOUT;
        goto use_direct_hsi;
    }

    PWR_CR |= PWR_CR_ODEN;
    if (wait_pwr_csr_set(PWR_CSR_ODRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_OD_TIMEOUT;
        goto use_direct_hsi;
    }

    PWR_CR |= PWR_CR_ODSWEN;
    if (wait_pwr_csr_set(PWR_CSR_ODSWRDY) == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_ODSW_TIMEOUT;
        goto use_direct_hsi;
    }

    RCC_CFGR =
        (RCC_CFGR &
         ~(RCC_CFGR_SW_MASK |
           RCC_CFGR_HPRE_MASK |
           RCC_CFGR_PPRE1_MASK |
           RCC_CFGR_PPRE2_MASK)) |
        RCC_CFGR_PPRE1_DIV4 |
        RCC_CFGR_PPRE2_DIV2 |
        RCC_CFGR_SW_PLL;

    if (wait_sysclk_pll() == 0UL) {
        g_clock_fault_flags |= CLOCK_FAULT_SWITCH_TIMEOUT;
        goto use_direct_hsi;
    }

    SystemCoreClock = HIL_PLL_SYSCLK_HZ;
    g_sysclk_hz = HIL_PLL_SYSCLK_HZ;

    /*
     * APB2 is SYSCLK/2, and STM32F4 timer clocks are doubled when APB
     * prescaler is greater than 1. Therefore TIM8 runs at SYSCLK = 180 MHz.
     */
    return HIL_PLL_SYSCLK_HZ;

use_direct_hsi:
    /*
     * Last-resort functional mode. This still produces 20 kHz PWM, but
     * dead-time resolution becomes 62.5 ns and HSI absolute accuracy applies.
     */
    RCC_CFGR &=
        ~(RCC_CFGR_SW_MASK |
          RCC_CFGR_HPRE_MASK |
          RCC_CFGR_PPRE1_MASK |
          RCC_CFGR_PPRE2_MASK);
    (void)wait_sysclk_hsi();
    RCC_CR &= ~RCC_CR_PLLON;

    g_clock_source = CLOCK_SOURCE_HSI_DIRECT;
    SystemCoreClock = HIL_HSI_HZ;
    g_sysclk_hz = HIL_HSI_HZ;
    return HIL_HSI_HZ;
}

static void pwm_gpio_init(void)
{
    uint32_t value;

    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOAEN | RCC_AHB1ENR_GPIOCEN;
    (void)RCC_AHB1ENR;

    /* PC6 = AF3 TIM8_CH1, very-high speed, push-pull, no pull. */
    value = GPIO_MODER(GPIOC_BASE);
    value &= ~(3UL << (6U * 2U));
    value |=  (2UL << (6U * 2U));
    GPIO_MODER(GPIOC_BASE) = value;
    GPIO_OTYPER(GPIOC_BASE) &= ~(1UL << 6);
    GPIO_OSPEEDR(GPIOC_BASE) =
        (GPIO_OSPEEDR(GPIOC_BASE) & ~(3UL << (6U * 2U))) |
        (3UL << (6U * 2U));
    GPIO_PUPDR(GPIOC_BASE) &= ~(3UL << (6U * 2U));
    GPIO_AFRL(GPIOC_BASE) =
        (GPIO_AFRL(GPIOC_BASE) & ~(0xFUL << (6U * 4U))) |
        (3UL << (6U * 4U));

    /* PA5 = AF3 TIM8_CH1N, very-high speed, push-pull, no pull. */
    value = GPIO_MODER(GPIOA_BASE);
    value &= ~(3UL << (5U * 2U));
    value |=  (2UL << (5U * 2U));
    GPIO_MODER(GPIOA_BASE) = value;
    GPIO_OTYPER(GPIOA_BASE) &= ~(1UL << 5);
    GPIO_OSPEEDR(GPIOA_BASE) =
        (GPIO_OSPEEDR(GPIOA_BASE) & ~(3UL << (5U * 2U))) |
        (3UL << (5U * 2U));
    GPIO_PUPDR(GPIOA_BASE) &= ~(3UL << (5U * 2U));
    GPIO_AFRL(GPIOA_BASE) =
        (GPIO_AFRL(GPIOA_BASE) & ~(0xFUL << (5U * 4U))) |
        (3UL << (5U * 4U));
}

static void tim8_pwm_init(uint32_t timer_clock_hz)
{
    uint32_t period_ticks;
    uint32_t duty_ticks;
    uint32_t dtg;
    uint32_t dead_ticks;

    if ((timer_clock_hz == 0UL) ||
        ((timer_clock_hz % PWM_FREQUENCY_HZ) != 0UL)) {
        fail_stop();
    }

    period_ticks = timer_clock_hz / PWM_FREQUENCY_HZ;
    duty_ticks = div_round_closest_u64(
        (uint64_t)period_ticks * (uint64_t)PWM_DUTY_PERMILLE,
        1000ULL);

    if ((period_ticks < 2UL) ||
        (period_ticks > 65536UL) ||
        (duty_ticks == 0UL) ||
        (duty_ticks >= period_ticks)) {
        fail_stop();
    }

    dtg = deadtime_ns_to_dtg(PWM_DEADTIME_NS, timer_clock_hz);
    dead_ticks = dtg_to_ticks(dtg);

    g_pwm_period_ticks = period_ticks;
    g_pwm_ccr1 = duty_ticks;
    g_pwm_deadtime_dtg = dtg;
    g_pwm_deadtime_actual_ns = div_round_closest_u64(
        (uint64_t)dead_ticks * 1000000000ULL,
        (uint64_t)timer_clock_hz);

    RCC_APB2ENR |= RCC_APB2ENR_TIM8EN;
    (void)RCC_APB2ENR;

    TIM8_CR1 = 0UL;
    TIM8_PSC = 0UL;
    TIM8_ARR = period_ticks - 1UL;
    TIM8_CCR1 = duty_ticks;

    TIM8_CCMR1 = TIM_CCMR1_OC1PE | TIM_CCMR1_OC1M_PWM1;

    /* Active-high CH1 and active-high complementary CH1N. */
    TIM8_CCER = TIM_CCER_CC1E | TIM_CCER_CC1NE;

    TIM8_BDTR = (dtg & 0xFFUL) | TIM_BDTR_MOE;

    TIM8_CR1 = TIM_CR1_ARPE;
    TIM8_EGR = TIM_EGR_UG;
    TIM8_CR1 |= TIM_CR1_CEN;

    g_tim8_cr1_snapshot = TIM8_CR1;
    g_tim8_ccer_snapshot = TIM8_CCER;
    g_tim8_bdtr_snapshot = TIM8_BDTR;
}

static void fail_stop(void)
{
    TIM8_BDTR = 0UL;

    /* Red on, green off. */
    RCC_AHB1ENR |= RCC_AHB1ENR_GPIOGEN;
    GPIO_ODR(GPIOG_BASE) &= ~(1UL << 13);
    GPIO_ODR(GPIOG_BASE) |=  (1UL << 14);

    for (;;) {
    }
}
