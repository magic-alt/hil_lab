#include "gd32h75e.h"
#include "gd32h75e_gpio.h"
#include "gd32h75e_rcu.h"
#include "gd32h75e_timer.h"
#include "pwm_profile.h"

#include <stdint.h>

volatile uint32_t g_pwm_profile_id = PWM_PROFILE_ID;
volatile uint32_t g_pwm_frequency_hz = PWM_FREQUENCY_HZ;
volatile uint32_t g_pwm_duty_permille = PWM_DUTY_PERMILLE;
volatile uint32_t g_pwm_deadtime_ns = PWM_DEADTIME_NS;
volatile uint32_t g_timer_clock_hz;
volatile uint32_t g_timer_period_ticks;
volatile uint32_t g_timer_pulse_ticks;
volatile uint32_t g_timer_deadtime_dtg;
volatile uint32_t g_timer_deadtime_actual_ns;

static uint32_t round_div_u64(uint64_t numerator, uint64_t denominator)
{
    return (uint32_t)((numerator + denominator / 2U) / denominator);
}

static uint32_t deadtime_ns_to_dtg(uint32_t deadtime_ns, uint32_t timer_hz)
{
    uint32_t ticks = round_div_u64(
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

static uint32_t timer0_clock_hz(void)
{
    uint32_t ahb;
    uint32_t apb2;

    rcu_timer_clock_prescaler_config(RCU_TIMER_PSC_MUL4);

    ahb = rcu_clock_freq_get(CK_AHB);
    apb2 = rcu_clock_freq_get(CK_APB2);

    /*
     * With MUL4 selection, TIMER0 follows AHB when APB2 is AHB, AHB/2,
     * or AHB/4. For larger APB2 divisors it is 4 x APB2.
     */
    if ((apb2 == ahb) ||
        ((apb2 * 2U) == ahb) ||
        ((apb2 * 4U) == ahb)) {
        return ahb;
    }

    return apb2 * 4U;
}

static void gpio_pwm_init(void)
{
    rcu_periph_clock_enable(RCU_GPIOA);
    rcu_periph_clock_enable(RCU_GPIOB);
    rcu_periph_clock_enable(RCU_GPIOE);

    /* U: PA8=TIMER0_CH0, PA7=TIMER0_MCH0 */
    gpio_af_set(GPIOA, GPIO_AF_1, GPIO_PIN_8 | GPIO_PIN_7);
    gpio_mode_set(GPIOA, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO_PIN_8 | GPIO_PIN_7);
    gpio_output_options_set(
        GPIOA, GPIO_OTYPE_PP, GPIO_OSPEED_85MHZ, GPIO_PIN_8 | GPIO_PIN_7);

    /* V: PE11=TIMER0_CH1, PB0=TIMER0_MCH1 */
    gpio_af_set(GPIOE, GPIO_AF_1, GPIO_PIN_11);
    gpio_mode_set(GPIOE, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO_PIN_11);
    gpio_output_options_set(GPIOE, GPIO_OTYPE_PP, GPIO_OSPEED_85MHZ, GPIO_PIN_11);

    gpio_af_set(GPIOB, GPIO_AF_1, GPIO_PIN_0);
    gpio_mode_set(GPIOB, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO_PIN_0);
    gpio_output_options_set(GPIOB, GPIO_OTYPE_PP, GPIO_OSPEED_85MHZ, GPIO_PIN_0);

    /* W: PE13=TIMER0_CH2, PE12=TIMER0_MCH2 */
    gpio_af_set(GPIOE, GPIO_AF_1, GPIO_PIN_13 | GPIO_PIN_12);
    gpio_mode_set(
        GPIOE, GPIO_MODE_AF, GPIO_PUPD_NONE, GPIO_PIN_13 | GPIO_PIN_12);
    gpio_output_options_set(
        GPIOE, GPIO_OTYPE_PP, GPIO_OSPEED_85MHZ, GPIO_PIN_13 | GPIO_PIN_12);
}

static void configure_channel(uint16_t channel, uint32_t pulse)
{
    timer_oc_parameter_struct oc;

    timer_channel_output_struct_para_init(&oc);
    oc.outputstate = TIMER_CCX_ENABLE;
    oc.outputnstate = TIMER_CCXN_ENABLE;
    oc.ocpolarity = TIMER_OC_POLARITY_HIGH;
    oc.ocnpolarity = TIMER_OCN_POLARITY_HIGH;
    oc.ocidlestate = TIMER_OC_IDLE_STATE_LOW;
    oc.ocnidlestate = TIMER_OCN_IDLE_STATE_LOW;

    timer_channel_output_config(TIMER0, channel, &oc);
    timer_channel_output_mode_config(TIMER0, channel, TIMER_OC_MODE_PWM0);
    timer_channel_output_pulse_value_config(TIMER0, channel, pulse);
    timer_channel_output_shadow_config(TIMER0, channel, TIMER_OC_SHADOW_ENABLE);
    timer_channel_output_state_config(TIMER0, channel, TIMER_CCX_ENABLE);
    timer_channel_complementary_output_state_config(
        TIMER0, channel, TIMER_CCXN_ENABLE);
}

static void timer0_pwm_init(void)
{
    timer_parameter_struct timer_cfg;
    timer_break_parameter_struct break_cfg;
    uint32_t dead_ticks;

    rcu_periph_clock_enable(RCU_TIMER0);
    timer_deinit(TIMER0);

    g_timer_clock_hz = timer0_clock_hz();
    if ((g_timer_clock_hz == 0U) ||
        ((g_timer_clock_hz % PWM_FREQUENCY_HZ) != 0U)) {
        while (1) {
        }
    }

    g_timer_period_ticks = g_timer_clock_hz / PWM_FREQUENCY_HZ;
    g_timer_pulse_ticks = round_div_u64(
        (uint64_t)g_timer_period_ticks * (uint64_t)PWM_DUTY_PERMILLE,
        1000U);

    if ((g_timer_pulse_ticks == 0U) ||
        (g_timer_pulse_ticks >= g_timer_period_ticks)) {
        while (1) {
        }
    }

    timer_struct_para_init(&timer_cfg);
    timer_cfg.prescaler = 0U;
    timer_cfg.alignedmode = TIMER_COUNTER_EDGE;
    timer_cfg.counterdirection = TIMER_COUNTER_UP;
    timer_cfg.period = g_timer_period_ticks - 1U;
    timer_cfg.clockdivision = TIMER_CKDIV_DIV1;
    timer_cfg.repetitioncounter = 0U;
    gd32_timer_init(TIMER0, &timer_cfg);

    configure_channel(TIMER_CH_0, g_timer_pulse_ticks);
    configure_channel(TIMER_CH_1, g_timer_pulse_ticks);
    configure_channel(TIMER_CH_2, g_timer_pulse_ticks);

    g_timer_deadtime_dtg = deadtime_ns_to_dtg(PWM_DEADTIME_NS, g_timer_clock_hz);
    dead_ticks = dtg_to_ticks(g_timer_deadtime_dtg);
    g_timer_deadtime_actual_ns = round_div_u64(
        (uint64_t)dead_ticks * 1000000000ULL,
        (uint64_t)g_timer_clock_hz);

    timer_break_struct_para_init(&break_cfg);
    break_cfg.deadtime = g_timer_deadtime_dtg;
    break_cfg.runoffstate = TIMER_ROS_STATE_DISABLE;
    break_cfg.ideloffstate = TIMER_IOS_STATE_DISABLE;
    break_cfg.outputautostate = TIMER_OUTAUTO_DISABLE;
    break_cfg.protectmode = TIMER_CCHP_PROT_OFF;
    break_cfg.break0state = TIMER_BREAK0_DISABLE;
    break_cfg.break1state = TIMER_BREAK1_DISABLE;
    timer_break_config(TIMER0, &break_cfg);

    timer_auto_reload_shadow_enable(TIMER0);
    timer_primary_output_config(TIMER0, ENABLE);
    timer_enable(TIMER0);
}

int main(void)
{
    gpio_pwm_init();
    timer0_pwm_init();

    for (;;) {
        __WFI();
    }
}
