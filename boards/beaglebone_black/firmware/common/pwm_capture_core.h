#ifndef HIL_PWM_CAPTURE_CORE_H_
#define HIL_PWM_CAPTURE_CORE_H_

#include <stdint.h>

#define HIL_PWM_SHARED_MAGIC       (0x314D5750u) /* "PWM1" little-endian */
#define HIL_PWM_SHARED_VERSION     (1u)
#define HIL_PWM_CHANNEL_COUNT      (6u)
#define HIL_PWM_PAIR_COUNT         (3u)
#define HIL_PWM_RING_CAPACITY      (128u)
#define HIL_PWM_LOGICAL_MASK       (0x3fu)

#define HIL_PWM_CH_UH              (0u)
#define HIL_PWM_CH_UL              (1u)
#define HIL_PWM_CH_VH              (2u)
#define HIL_PWM_CH_VL              (3u)
#define HIL_PWM_CH_WH              (4u)
#define HIL_PWM_CH_WL              (5u)

#define HIL_PWM_CH_RISE_SEEN       (1u << 0)
#define HIL_PWM_CH_FALL_SEEN       (1u << 1)
#define HIL_PWM_CH_PERIOD_VALID    (1u << 2)
#define HIL_PWM_CH_HIGH_VALID      (1u << 3)
#define HIL_PWM_CH_LOW_VALID       (1u << 4)

#define HIL_PWM_PAIR_DT_HL_VALID       (1u << 0)
#define HIL_PWM_PAIR_DT_LH_VALID       (1u << 1)
#define HIL_PWM_PAIR_OVERLAP_ACTIVE    (1u << 2)
#define HIL_PWM_PAIR_OVERLAP_LATCHED   (1u << 3)
#define HIL_PWM_PAIR_VIOLATION_LATCHED (1u << 4)

#define HIL_PWM_FAULT_OVERLAP(pair_index)  (1u << (pair_index))
#define HIL_PWM_FAULT_DEADTIME(pair_index) (1u << (8u + (pair_index)))

struct hil_pwm_channel_snapshot {
    uint32_t period_ticks;
    uint32_t high_ticks;
    uint32_t low_ticks;
    uint32_t last_rise_ticks;
    uint32_t last_fall_ticks;
    uint32_t rise_count;
    uint32_t fall_count;
    uint32_t flags;
};

struct hil_pwm_pair_snapshot {
    uint32_t deadtime_high_to_low_ticks;
    uint32_t deadtime_low_to_high_ticks;
    uint32_t deadtime_high_to_low_count;
    uint32_t deadtime_low_to_high_count;
    uint32_t overlap_count;
    uint32_t violation_count;
    uint32_t flags;
    uint32_t reserved;
};

struct hil_pwm_edge_record {
    uint32_t timestamp_ticks;
    uint32_t logical_inputs;
    uint32_t changed_inputs;
    uint32_t fault_flags;
};

struct hil_pwm_shared {
    uint32_t magic;
    uint32_t version;
    uint32_t total_size;
    uint32_t seq_lock;
    uint32_t tick_hz;
    uint32_t channel_count;
    uint32_t pair_count;
    uint32_t ring_capacity;
    uint32_t running;
    uint32_t min_deadtime_ticks;
    uint32_t input_bits;
    uint32_t changed_bits;
    uint32_t last_timestamp_ticks;
    uint32_t event_seq;
    uint32_t ring_head;
    uint32_t ring_count;
    uint32_t fault_flags;
    uint32_t reserved0;
    uint32_t reserved1;
    uint32_t reserved2;
    struct hil_pwm_channel_snapshot channel[HIL_PWM_CHANNEL_COUNT];
    struct hil_pwm_pair_snapshot pair[HIL_PWM_PAIR_COUNT];
    struct hil_pwm_edge_record ring[HIL_PWM_RING_CAPACITY];
};

void hil_pwm_capture_init(
    volatile struct hil_pwm_shared *shared,
    uint32_t tick_hz,
    uint32_t min_deadtime_ticks);

void hil_pwm_capture_start(
    volatile struct hil_pwm_shared *shared,
    uint32_t timestamp_ticks,
    uint32_t logical_inputs);

void hil_pwm_capture_stop(volatile struct hil_pwm_shared *shared);

void hil_pwm_capture_clear(
    volatile struct hil_pwm_shared *shared,
    uint32_t logical_inputs);

void hil_pwm_capture_set_min_deadtime(
    volatile struct hil_pwm_shared *shared,
    uint32_t min_deadtime_ticks);

void hil_pwm_capture_process(
    volatile struct hil_pwm_shared *shared,
    uint32_t timestamp_ticks,
    uint32_t logical_inputs);

#endif
