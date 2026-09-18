#ifndef HIL_RAW_EDGE_CAPTURE_H_
#define HIL_RAW_EDGE_CAPTURE_H_

#include <stdint.h>

#define HIL_RAW_CAPTURE_MAGIC        (0x31574152u) /* "RAW1" little-endian */
#define HIL_RAW_CAPTURE_VERSION      (1u)
#define HIL_RAW_CAPTURE_CAPACITY     (1024u)

#define HIL_RAW_STOP_NONE            (0u)
#define HIL_RAW_STOP_EVENT_LIMIT     (1u)
#define HIL_RAW_STOP_HOST_REQUEST    (2u)
#define HIL_RAW_STOP_FORCE_SAFE      (3u)

struct hil_raw_edge_record {
    uint32_t timestamp_ticks;
    uint32_t raw_inputs;
};

struct hil_raw_capture_shared {
    uint32_t magic;
    uint32_t version;
    uint32_t total_size;
    uint32_t tick_hz;

    uint32_t capacity;
    uint32_t running;
    uint32_t configured_event_limit;
    uint32_t event_count;

    uint32_t initial_raw_inputs;
    uint32_t final_raw_inputs;
    uint32_t start_ticks;
    uint32_t stop_ticks;

    uint32_t stop_reason;
    uint32_t input_mask;
    uint32_t generation;
    uint32_t overflow_count;

    struct hil_raw_edge_record ring[HIL_RAW_CAPTURE_CAPACITY];
};

typedef char hil_raw_edge_record_must_be_8_bytes[
    (sizeof(struct hil_raw_edge_record) == 8u) ? 1 : -1
];

typedef char hil_raw_capture_must_fit_shared_ram[
    (sizeof(struct hil_raw_capture_shared) <= 0x3000u) ? 1 : -1
];

#endif
