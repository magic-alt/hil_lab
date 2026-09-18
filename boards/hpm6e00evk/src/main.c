#include "board.h"
#include "hpm_clock_drv.h"
#include "hpm_pwmv2_drv.h"
#include "pwm_profile.h"

#include <stdio.h>

#define PWM_BASE BOARD_APP_PWM
#define PWM_CLOCK_NAME BOARD_APP_PWM_CLOCK_NAME

volatile uint32_t g_pwm_profile_id = PWM_PROFILE_ID;
volatile uint32_t g_pwm_frequency_hz = PWM_FREQUENCY_HZ;
volatile uint32_t g_pwm_duty_permille = PWM_DUTY_PERMILLE;
volatile uint32_t g_pwm_deadtime_ns = PWM_DEADTIME_NS;
volatile uint32_t g_pwm_clock_hz;
volatile uint32_t g_pwm_reload;
volatile uint32_t g_pwm_deadtime_ticks;
volatile uint32_t g_pwm_cmp_low;
volatile uint32_t g_pwm_cmp_high;

static uint32_t round_div_u64(uint64_t numerator, uint64_t denominator)
{
    return (uint32_t)((numerator + denominator / 2U) / denominator);
}

static void fail_stop(const char *message)
{
    printf("ERROR: %s\n", message);
    while (1) {
    }
}

static void configure_pair(pwm_channel_t pair_channel,
                           uint8_t cmp_start_index,
                           uint8_t shadow_low_index,
                           uint8_t shadow_high_index,
                           uint32_t dead_ticks)
{
    pwmv2_cmp_config_t cmp_cfg[2] = {0};
    pwmv2_pair_config_t pair_cfg = {0};

    cmp_cfg[0].cmp = g_pwm_cmp_low;
    cmp_cfg[0].enable_half_cmp = false;
    cmp_cfg[0].enable_hrcmp = false;
    cmp_cfg[0].cmp_source = cmp_value_from_shadow_val;
    cmp_cfg[0].cmp_source_index = PWMV2_SHADOW_INDEX(shadow_low_index);
    cmp_cfg[0].update_trigger = pwm_shadow_register_update_on_reload;

    cmp_cfg[1].cmp = g_pwm_cmp_high;
    cmp_cfg[1].enable_half_cmp = false;
    cmp_cfg[1].enable_hrcmp = false;
    cmp_cfg[1].cmp_source = cmp_value_from_shadow_val;
    cmp_cfg[1].cmp_source_index = PWMV2_SHADOW_INDEX(shadow_high_index);
    cmp_cfg[1].update_trigger = pwm_shadow_register_update_on_reload;

    pwmv2_get_default_config(&pair_cfg.pwm[0]);
    pwmv2_get_default_config(&pair_cfg.pwm[1]);

    pair_cfg.pwm[0].enable_output = true;
    pair_cfg.pwm[0].enable_async_fault = false;
    pair_cfg.pwm[0].enable_sync_fault = false;
    pair_cfg.pwm[0].invert_output = false;
    pair_cfg.pwm[0].enable_four_cmp = false;
    pair_cfg.pwm[0].update_trigger = pwm_reload_update_on_reload;
    pair_cfg.pwm[0].dead_zone_in_half_cycle = dead_ticks;

    pair_cfg.pwm[1].enable_output = true;
    pair_cfg.pwm[1].enable_async_fault = false;
    pair_cfg.pwm[1].enable_sync_fault = false;
    pair_cfg.pwm[1].invert_output = false;
    pair_cfg.pwm[1].enable_four_cmp = false;
    pair_cfg.pwm[1].update_trigger = pwm_reload_update_on_reload;
    pair_cfg.pwm[1].dead_zone_in_half_cycle = dead_ticks;

    if (status_success != pwmv2_setup_waveform_in_pair(
                              PWM_BASE,
                              pair_channel,
                              &pair_cfg,
                              cmp_start_index,
                              cmp_cfg,
                              2U)) {
        fail_stop("pwmv2_setup_waveform_in_pair");
    }
}

static void pwm_stimulus_init(void)
{
    uint32_t period_ticks;
    uint32_t high_ticks;

    g_pwm_clock_hz = clock_get_frequency(PWM_CLOCK_NAME);
    if ((g_pwm_clock_hz == 0U) ||
        ((g_pwm_clock_hz % PWM_FREQUENCY_HZ) != 0U)) {
        fail_stop("PWM clock must divide exactly by PWM_FREQUENCY_HZ");
    }

    period_ticks = g_pwm_clock_hz / PWM_FREQUENCY_HZ;
    g_pwm_reload = period_ticks - 1U;

    high_ticks = round_div_u64(
        (uint64_t)period_ticks * (uint64_t)PWM_DUTY_PERMILLE,
        1000U);

    if ((high_ticks == 0U) || (high_ticks >= period_ticks)) {
        fail_stop("invalid duty");
    }

    g_pwm_cmp_low = (period_ticks - high_ticks) / 2U;
    g_pwm_cmp_high = g_pwm_cmp_low + high_ticks;
    g_pwm_deadtime_ticks = round_div_u64(
        (uint64_t)g_pwm_clock_hz * (uint64_t)PWM_DEADTIME_NS,
        1000000000ULL);

    if (g_pwm_deadtime_ticks > 0xFFFFU) {
        fail_stop("dead time exceeds PWMV2 integer dead-zone range");
    }

    pwmv2_deinit(PWM_BASE);
    pwmv2_disable_counter(PWM_BASE, pwm_counter_0);
    pwmv2_disable_counter(PWM_BASE, pwm_counter_1);
    pwmv2_disable_counter(PWM_BASE, pwm_counter_2);
    pwmv2_reset_counter(PWM_BASE, pwm_counter_0);
    pwmv2_reset_counter(PWM_BASE, pwm_counter_1);
    pwmv2_reset_counter(PWM_BASE, pwm_counter_2);

    pwmv2_shadow_register_unlock(PWM_BASE);
    pwmv2_set_shadow_val(PWM_BASE, PWMV2_SHADOW_INDEX(0), g_pwm_reload, 0U, false);
    pwmv2_set_shadow_val(PWM_BASE, PWMV2_SHADOW_INDEX(1), g_pwm_cmp_low, 0U, false);
    pwmv2_set_shadow_val(PWM_BASE, PWMV2_SHADOW_INDEX(2), g_pwm_cmp_high, 0U, false);
    pwmv2_set_shadow_val(PWM_BASE, PWMV2_SHADOW_INDEX(3), g_pwm_cmp_low, 0U, false);
    pwmv2_set_shadow_val(PWM_BASE, PWMV2_SHADOW_INDEX(4), g_pwm_cmp_high, 0U, false);
    pwmv2_set_shadow_val(PWM_BASE, PWMV2_SHADOW_INDEX(5), g_pwm_cmp_low, 0U, false);
    pwmv2_set_shadow_val(PWM_BASE, PWMV2_SHADOW_INDEX(6), g_pwm_cmp_high, 0U, false);
    pwmv2_shadow_register_lock(PWM_BASE);

    configure_pair(pwm_channel_0, PWMV2_CMP_INDEX(0), 1U, 2U, g_pwm_deadtime_ticks);
    configure_pair(pwm_channel_2, PWMV2_CMP_INDEX(4), 3U, 4U, g_pwm_deadtime_ticks);
    configure_pair(pwm_channel_4, PWMV2_CMP_INDEX(8), 5U, 6U, g_pwm_deadtime_ticks);

    pwmv2_counter_select_data_offset_from_shadow_value(
        PWM_BASE, pwm_counter_0, PWMV2_SHADOW_INDEX(0));
    pwmv2_counter_select_data_offset_from_shadow_value(
        PWM_BASE, pwm_counter_1, PWMV2_SHADOW_INDEX(0));
    pwmv2_counter_select_data_offset_from_shadow_value(
        PWM_BASE, pwm_counter_2, PWMV2_SHADOW_INDEX(0));

    pwmv2_counter_burst_disable(PWM_BASE, pwm_counter_0);
    pwmv2_counter_burst_disable(PWM_BASE, pwm_counter_1);
    pwmv2_counter_burst_disable(PWM_BASE, pwm_counter_2);

    pwmv2_set_reload_update_time(PWM_BASE, pwm_counter_0, pwm_reload_update_on_reload);
    pwmv2_set_reload_update_time(PWM_BASE, pwm_counter_1, pwm_reload_update_on_reload);
    pwmv2_set_reload_update_time(PWM_BASE, pwm_counter_2, pwm_reload_update_on_reload);

    pwmv2_issue_shadow_register_lock_event(PWM_BASE);
    pwmv2_enable_multi_counter_sync(PWM_BASE, 0x07U);
    pwmv2_start_pwm_output_sync(PWM_BASE, 0x07U);
}

int main(void)
{
    board_init();
    init_pwm_pins(PWM_BASE);

    printf("\nHPM6E00EVK BBB B1 PWM stimulus\n");
    printf("profile=%u freq=%u duty_permille=%u deadtime_ns=%u\n",
           (unsigned)PWM_PROFILE_ID,
           (unsigned)PWM_FREQUENCY_HZ,
           (unsigned)PWM_DUTY_PERMILLE,
           (unsigned)PWM_DEADTIME_NS);

    pwm_stimulus_init();

    printf("PWM1 PE08..PE13 active\n");
    printf("clock=%u reload=%u cmp=[%u,%u] dead_ticks=%u\n",
           (unsigned)g_pwm_clock_hz,
           (unsigned)g_pwm_reload,
           (unsigned)g_pwm_cmp_low,
           (unsigned)g_pwm_cmp_high,
           (unsigned)g_pwm_deadtime_ticks);

    while (1) {
        __asm volatile("wfi");
    }
}
