#include "pwm_capture_core.h"

static void begin_update(volatile struct hil_pwm_shared *shared)
{
    shared->seq_lock += 1u;
}

static void end_update(volatile struct hil_pwm_shared *shared)
{
    shared->seq_lock += 1u;
}

static void clear_words(volatile uint32_t *words, uint32_t word_count)
{
    uint32_t i;
    for (i = 0u; i < word_count; ++i)
        words[i] = 0u;
}

static void push_edge_record(
    volatile struct hil_pwm_shared *shared,
    uint32_t timestamp_ticks,
    uint32_t logical_inputs,
    uint32_t changed_inputs)
{
    uint32_t slot = shared->ring_head;
    volatile struct hil_pwm_edge_record *record = &shared->ring[slot];

    record->timestamp_ticks = timestamp_ticks;
    record->logical_inputs = logical_inputs;
    record->changed_inputs = changed_inputs;
    record->fault_flags = shared->fault_flags;

    slot += 1u;
    if (slot >= HIL_PWM_RING_CAPACITY)
        slot = 0u;
    shared->ring_head = slot;
    if (shared->ring_count < HIL_PWM_RING_CAPACITY)
        shared->ring_count += 1u;
}

static void record_deadtime(
    volatile struct hil_pwm_shared *shared,
    uint32_t pair_index,
    uint32_t high_to_low,
    uint32_t deadtime_ticks)
{
    volatile struct hil_pwm_pair_snapshot *pair = &shared->pair[pair_index];

    if (high_to_low != 0u) {
        pair->deadtime_high_to_low_ticks = deadtime_ticks;
        pair->deadtime_high_to_low_count += 1u;
        pair->flags |= HIL_PWM_PAIR_DT_HL_VALID;
    } else {
        pair->deadtime_low_to_high_ticks = deadtime_ticks;
        pair->deadtime_low_to_high_count += 1u;
        pair->flags |= HIL_PWM_PAIR_DT_LH_VALID;
    }

    if ((shared->min_deadtime_ticks != 0u) &&
        (deadtime_ticks < shared->min_deadtime_ticks)) {
        pair->violation_count += 1u;
        pair->flags |= HIL_PWM_PAIR_VIOLATION_LATCHED;
        shared->fault_flags |= HIL_PWM_FAULT_DEADTIME(pair_index);
    }
}

void hil_pwm_capture_init(
    volatile struct hil_pwm_shared *shared,
    uint32_t tick_hz,
    uint32_t min_deadtime_ticks)
{
    clear_words(
        (volatile uint32_t *)shared,
        (uint32_t)(sizeof(struct hil_pwm_shared) / sizeof(uint32_t)));

    shared->magic = HIL_PWM_SHARED_MAGIC;
    shared->version = HIL_PWM_SHARED_VERSION;
    shared->total_size = (uint32_t)sizeof(struct hil_pwm_shared);
    shared->tick_hz = tick_hz;
    shared->channel_count = HIL_PWM_CHANNEL_COUNT;
    shared->pair_count = HIL_PWM_PAIR_COUNT;
    shared->ring_capacity = HIL_PWM_RING_CAPACITY;
    shared->min_deadtime_ticks = min_deadtime_ticks;
}

void hil_pwm_capture_start(
    volatile struct hil_pwm_shared *shared,
    uint32_t timestamp_ticks,
    uint32_t logical_inputs)
{
    begin_update(shared);
    shared->running = 1u;
    shared->input_bits = logical_inputs & HIL_PWM_LOGICAL_MASK;
    shared->changed_bits = 0u;
    shared->last_timestamp_ticks = timestamp_ticks;
    end_update(shared);
}

void hil_pwm_capture_stop(volatile struct hil_pwm_shared *shared)
{
    begin_update(shared);
    shared->running = 0u;
    end_update(shared);
}

void hil_pwm_capture_clear(
    volatile struct hil_pwm_shared *shared,
    uint32_t logical_inputs)
{
    uint32_t tick_hz = shared->tick_hz;
    uint32_t min_deadtime_ticks = shared->min_deadtime_ticks;
    uint32_t running = shared->running;

    hil_pwm_capture_init(shared, tick_hz, min_deadtime_ticks);
    shared->input_bits = logical_inputs & HIL_PWM_LOGICAL_MASK;
    shared->running = running;
}

void hil_pwm_capture_set_min_deadtime(
    volatile struct hil_pwm_shared *shared,
    uint32_t min_deadtime_ticks)
{
    begin_update(shared);
    shared->min_deadtime_ticks = min_deadtime_ticks;
    end_update(shared);
}

void hil_pwm_capture_process(
    volatile struct hil_pwm_shared *shared,
    uint32_t timestamp_ticks,
    uint32_t logical_inputs)
{
    uint32_t previous_inputs;
    uint32_t changed_inputs;
    uint32_t rise_bits;
    uint32_t fall_bits;
    uint32_t channel_index;
    uint32_t pair_index;

    if (shared->running == 0u)
        return;

    logical_inputs &= HIL_PWM_LOGICAL_MASK;
    previous_inputs = shared->input_bits;
    changed_inputs = (logical_inputs ^ previous_inputs) & HIL_PWM_LOGICAL_MASK;
    if (changed_inputs == 0u)
        return;

    rise_bits = changed_inputs & logical_inputs;
    fall_bits = changed_inputs & previous_inputs;

    begin_update(shared);
    shared->input_bits = logical_inputs;
    shared->changed_bits = changed_inputs;
    shared->last_timestamp_ticks = timestamp_ticks;
    shared->event_seq += 1u;

    for (channel_index = 0u; channel_index < HIL_PWM_CHANNEL_COUNT; ++channel_index) {
        uint32_t bit = (1u << channel_index);
        volatile struct hil_pwm_channel_snapshot *channel = &shared->channel[channel_index];

        if ((rise_bits & bit) != 0u) {
            if ((channel->flags & HIL_PWM_CH_RISE_SEEN) != 0u) {
                channel->period_ticks = timestamp_ticks - channel->last_rise_ticks;
                channel->flags |= HIL_PWM_CH_PERIOD_VALID;
            }
            if ((channel->flags & HIL_PWM_CH_FALL_SEEN) != 0u) {
                channel->low_ticks = timestamp_ticks - channel->last_fall_ticks;
                channel->flags |= HIL_PWM_CH_LOW_VALID;
            }
            channel->last_rise_ticks = timestamp_ticks;
            channel->rise_count += 1u;
            channel->flags |= HIL_PWM_CH_RISE_SEEN;
        }

        if ((fall_bits & bit) != 0u) {
            if ((channel->flags & HIL_PWM_CH_RISE_SEEN) != 0u) {
                channel->high_ticks = timestamp_ticks - channel->last_rise_ticks;
                channel->flags |= HIL_PWM_CH_HIGH_VALID;
            }
            channel->last_fall_ticks = timestamp_ticks;
            channel->fall_count += 1u;
            channel->flags |= HIL_PWM_CH_FALL_SEEN;
        }
    }

    for (pair_index = 0u; pair_index < HIL_PWM_PAIR_COUNT; ++pair_index) {
        uint32_t high_index = pair_index * 2u;
        uint32_t low_index = high_index + 1u;
        uint32_t high_bit = (1u << high_index);
        uint32_t low_bit = (1u << low_index);
        uint32_t overlap_now =
            (((logical_inputs & high_bit) != 0u) &&
             ((logical_inputs & low_bit) != 0u)) ? 1u : 0u;
        volatile struct hil_pwm_pair_snapshot *pair = &shared->pair[pair_index];

        if ((rise_bits & low_bit) != 0u) {
            if ((fall_bits & high_bit) != 0u) {
                record_deadtime(shared, pair_index, 1u, 0u);
            } else if ((shared->channel[high_index].flags & HIL_PWM_CH_FALL_SEEN) != 0u) {
                record_deadtime(
                    shared,
                    pair_index,
                    1u,
                    timestamp_ticks - shared->channel[high_index].last_fall_ticks);
            }
        }

        if ((rise_bits & high_bit) != 0u) {
            if ((fall_bits & low_bit) != 0u) {
                record_deadtime(shared, pair_index, 0u, 0u);
            } else if ((shared->channel[low_index].flags & HIL_PWM_CH_FALL_SEEN) != 0u) {
                record_deadtime(
                    shared,
                    pair_index,
                    0u,
                    timestamp_ticks - shared->channel[low_index].last_fall_ticks);
            }
        }

        if (overlap_now != 0u) {
            if ((pair->flags & HIL_PWM_PAIR_OVERLAP_ACTIVE) == 0u)
                pair->overlap_count += 1u;
            pair->flags |=
                (HIL_PWM_PAIR_OVERLAP_ACTIVE | HIL_PWM_PAIR_OVERLAP_LATCHED);
            shared->fault_flags |= HIL_PWM_FAULT_OVERLAP(pair_index);
        } else {
            pair->flags &= ~HIL_PWM_PAIR_OVERLAP_ACTIVE;
        }
    }

    push_edge_record(shared, timestamp_ticks, logical_inputs, changed_inputs);
    end_update(shared);
}
