#include <stdint.h>

#include "pwm_profile.h"
#include "stm32f429_regs.h"

extern uint32_t SystemCoreClock;
void SystemCoreClockUpdate(void);

static void clock_180mhz_init(void);
static void gpio_init(void);
static void tim8_pwm_init(void);
static uint32_t deadtime_ns_to_dtg(uint32_t deadtime_ns);
static void fail_stop(void);

volatile uint32_t g_pwm_profile_id = PWM_PROFILE_ID;
volatile uint32_t g_pwm_frequency_hz = PWM_FREQUENCY_HZ;
volatile uint32_t g_pwm_duty_permille = PWM_DUTY_PERMILLE;
volatile uint32_t g_pwm_deadtime_ns = PWM_DEADTIME_NS;
volatile uint32_t g_pwm_deadtime_dtg;

static uint32_t div_round_closest_u64(uint64_t numerator, uint64_t denominator)
{
    return (uint32_t)((numerator + (denominator / 2ULL)) / denominator);
}

/*
 * STM32F429 RM0090 TIMx_BDTR.DTG encoding with TIM8 CKD=DIV1:
 *   0xx: DT = DTG * tDTS
 *   10x: DT = (64 + DTG[5:0]) * 2 * tDTS
 *   110: DT = (32 + DTG[4:0]) * 8 * tDTS
 *   111: DT = (32 + DTG[4:0]) * 16 * tDTS
 */
static uint32_t deadtime_ns_to_dtg(uint32_t deadtime_ns)
{
    uint32_t ticks = div_round_closest_u64(
        (uint64_t)deadtime_ns * (uint64_t)HIL_APB2_TIMER_HZ,
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

int main(void)
{
    clock_180mhz_init();
    gpio_init();
    tim8_pwm_init();

    /* LD3 green (PG13) indicates that TIM8 outputs are active. */
    GPIO_ODR(GPIOG_BASE) |= (1UL << 13);

    for (;;) {
        cpu_wfi();
    }
}

static void clock_180mhz_init(void)
{
    uint32_t timeout;

    RCC_APB1ENR |= RCC_APB1ENR_PWREN;
    (void)RCC_APB1ENR;

    PWR_CR = (PWR_CR & ~(3UL << 14)) | PWR_CR_VOS_SCALE1;

    FLASH_ACR =
        FLASH_ACR_LATENCY_5WS |
        FLASH_ACR_PRFTEN |
        FLASH_ACR_ICEN |
        FLASH_ACR_DCEN;

    /* STM32F429I-DISC1 factory routing: ST-LINK MCO 8 MHz -> PH0/OSC_IN. */
    RCC_CR |= RCC_CR_HSEBYP;
    RCC_CR |= RCC_CR_HSEON;
    timeout = 1000000UL;
    while (((RCC_CR & RCC_CR_HSERDY) == 0UL) && (timeout-- != 0UL)) {
    }
    if ((RCC_CR & RCC_CR_HSERDY) == 0UL) {
        fail_stop();
    }

    RCC_CR &= ~RCC_CR_PLLON;
    while ((RCC_CR & RCC_CR_PLLRDY) != 0UL) {
    }

    RCC_PLLCFGR =
        (8UL << 0) |
        (360UL << 6) |
        (0UL << 16) |
        RCC_PLLCFGR_PLLSRC_HSE |
        (7UL << 24);

    RCC_CR |= RCC_CR_PLLON;
    timeout = 1000000UL;
    while (((RCC_CR & RCC_CR_PLLRDY) == 0UL) && (timeout-- != 0UL)) {
    }
    if ((RCC_CR & RCC_CR_PLLRDY) == 0UL) {
        fail_stop();
    }

    PWR_CR |= PWR_CR_ODEN;
    timeout = 1000000UL;
    while (((PWR_CSR & PWR_CSR_ODRDY) == 0UL) && (timeout-- != 0UL)) {
    }
    if ((PWR_CSR & PWR_CSR_ODRDY) == 0UL) {
        fail_stop();
    }

    PWR_CR |= PWR_CR_ODSWEN;
    timeout = 1000000UL;
    while (((PWR_CSR & PWR_CSR_ODSWRDY) == 0UL) && (timeout-- != 0UL)) {
    }
    if ((PWR_CSR & PWR_CSR_ODSWRDY) == 0UL) {
        fail_stop();
    }

    RCC_CFGR =
        (RCC_CFGR & ~((7UL << 10) | (7UL << 13) | 3UL)) |
        RCC_CFGR_PPRE1_DIV4 |
        RCC_CFGR_PPRE2_DIV2 |
        RCC_CFGR_SW_PLL;

    timeout = 1000000UL;
    while (((RCC_CFGR & RCC_CFGR_SWS_MASK) != RCC_CFGR_SWS_PLL) &&
           (timeout-- != 0UL)) {
    }
    if ((RCC_CFGR & RCC_CFGR_SWS_MASK) != RCC_CFGR_SWS_PLL) {
        fail_stop();
    }

    SystemCoreClockUpdate();
    SystemCoreClock = HIL_SYSCLK_HZ;
}

static void gpio_init(void)
{
    uint32_t value;

    RCC_AHB1ENR |=
        RCC_AHB1ENR_GPIOAEN |
        RCC_AHB1ENR_GPIOCEN |
        RCC_AHB1ENR_GPIOGEN;
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

    /* PG13 = LD3 green status LED. */
    value = GPIO_MODER(GPIOG_BASE);
    value &= ~(3UL << (13U * 2U));
    value |=  (1UL << (13U * 2U));
    GPIO_MODER(GPIOG_BASE) = value;
    GPIO_OTYPER(GPIOG_BASE) &= ~(1UL << 13);
    GPIO_PUPDR(GPIOG_BASE) &= ~(3UL << (13U * 2U));
    GPIO_ODR(GPIOG_BASE) &= ~(1UL << 13);
}

static void tim8_pwm_init(void)
{
    uint32_t dtg;

    RCC_APB2ENR |= RCC_APB2ENR_TIM8EN;
    (void)RCC_APB2ENR;

    TIM8_CR1 = 0UL;
    TIM8_PSC = 0UL;
    TIM8_ARR = HIL_PWM_ARR;
    TIM8_CCR1 = HIL_PWM_CCR1;

    TIM8_CCMR1 =
        TIM_CCMR1_OC1PE |
        TIM_CCMR1_OC1M_PWM1;

    /* Active-high CH1 and active-high complementary CH1N. */
    TIM8_CCER = TIM_CCER_CC1E | TIM_CCER_CC1NE;

    dtg = deadtime_ns_to_dtg(PWM_DEADTIME_NS);
    g_pwm_deadtime_dtg = dtg;
    TIM8_BDTR = (dtg & 0xFFUL) | TIM_BDTR_MOE;

    TIM8_CR1 = TIM_CR1_ARPE;
    TIM8_EGR = TIM_EGR_UG;
    TIM8_CR1 |= TIM_CR1_CEN;
}

static void fail_stop(void)
{
    TIM8_BDTR = 0UL;
    GPIO_ODR(GPIOG_BASE) &= ~(1UL << 13);
    for (;;) {
    }
}
