#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "pwm_capture_core.h"

static void test_nominal_and_faults(void)
{
    struct hil_pwm_shared shared;

    hil_pwm_capture_init(&shared, 200000000u, 100u);
    assert(shared.magic == HIL_PWM_SHARED_MAGIC);
    assert(shared.total_size == sizeof(shared));
    hil_pwm_capture_start(&shared, 0u, 0u);

    /* U high: rise at 100, fall at 300 => high time 200 ticks. */
    hil_pwm_capture_process(&shared, 100u, 1u << HIL_PWM_CH_UH);
    hil_pwm_capture_process(&shared, 300u, 0u);
    assert(shared.channel[HIL_PWM_CH_UH].high_ticks == 200u);
    assert((shared.channel[HIL_PWM_CH_UH].flags & HIL_PWM_CH_HIGH_VALID) != 0u);

    /* U low rises 100 ticks after U high falls. */
    hil_pwm_capture_process(&shared, 400u, 1u << HIL_PWM_CH_UL);
    assert(shared.pair[0].deadtime_high_to_low_ticks == 100u);
    assert(shared.pair[0].deadtime_high_to_low_count == 1u);
    assert(shared.fault_flags == 0u);

    /* U low falls at 700, U high rises at 800 => reverse dead-time 100. */
    hil_pwm_capture_process(&shared, 700u, 0u);
    hil_pwm_capture_process(&shared, 800u, 1u << HIL_PWM_CH_UH);
    assert(shared.channel[HIL_PWM_CH_UH].period_ticks == 700u);
    assert(shared.channel[HIL_PWM_CH_UH].low_ticks == 500u);
    assert(shared.pair[0].deadtime_low_to_high_ticks == 100u);
    assert(shared.pair[0].deadtime_low_to_high_count == 1u);

    /* 50-tick high->low dead-time violates the configured 100-tick minimum. */
    hil_pwm_capture_process(&shared, 900u, 0u);
    hil_pwm_capture_process(&shared, 950u, 1u << HIL_PWM_CH_UL);
    assert(shared.pair[0].deadtime_high_to_low_ticks == 50u);
    assert(shared.pair[0].violation_count == 1u);
    assert((shared.fault_flags & HIL_PWM_FAULT_DEADTIME(0u)) != 0u);

    /* Assert U high while U low remains high: overlap/shoot-through command. */
    hil_pwm_capture_process(
        &shared,
        1000u,
        (1u << HIL_PWM_CH_UH) | (1u << HIL_PWM_CH_UL));
    assert(shared.pair[0].overlap_count == 1u);
    assert((shared.fault_flags & HIL_PWM_FAULT_OVERLAP(0u)) != 0u);

    assert((shared.seq_lock & 1u) == 0u);
    assert(shared.ring_count > 0u);
}

static void test_ring_wrap(void)
{
    struct hil_pwm_shared shared;
    uint32_t i;
    uint32_t inputs = 0u;

    hil_pwm_capture_init(&shared, 200000000u, 0u);
    hil_pwm_capture_start(&shared, 0u, inputs);

    for (i = 0u; i < (HIL_PWM_RING_CAPACITY + 32u); ++i) {
        inputs ^= 1u << HIL_PWM_CH_UH;
        hil_pwm_capture_process(&shared, i + 1u, inputs);
    }

    assert(shared.ring_count == HIL_PWM_RING_CAPACITY);
    assert(shared.event_seq == HIL_PWM_RING_CAPACITY + 32u);
    assert(shared.ring_head == 32u);
}

int main(void)
{
    test_nominal_and_faults();
    test_ring_wrap();
    puts("PASS: pwm_capture_core");
    return 0;
}
