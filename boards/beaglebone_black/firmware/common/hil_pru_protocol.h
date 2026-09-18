#ifndef HIL_PRU_PROTOCOL_H_
#define HIL_PRU_PROTOCOL_H_

#include <stdint.h>

#define HIL_PRU_MAGIC              (0x304C4948u) /* "HIL0" little-endian */
#define HIL_PRU_PROTOCOL_VERSION   (1u)
#define HIL_PRU_FIRMWARE_VERSION   (0x00010000u)
#define HIL_PRU_B1_FIRMWARE_VERSION (0x00020000u)

#define HIL_PRU_CAP_TIMEBASE                  (1u << 0)
#define HIL_PRU_CAP_RPMSG                     (1u << 1)
#define HIL_PRU_CAP_GPIO_LOOPBACK             (1u << 2)
#define HIL_PRU_CAP_FORCE_SAFE                (1u << 3)
#define HIL_PRU_CAP_WATCHDOG                  (1u << 4)
#define HIL_PRU_CAP_PWM_CAPTURE               (1u << 5)
#define HIL_PRU_CAP_PWM_COMPLEMENTARY_MONITOR (1u << 6)
#define HIL_PRU_CAP_SHARED_SNAPSHOT           (1u << 7)

#define HIL_PRU_B0_CAPABILITIES     (HIL_PRU_CAP_TIMEBASE | HIL_PRU_CAP_RPMSG |      HIL_PRU_CAP_GPIO_LOOPBACK | HIL_PRU_CAP_FORCE_SAFE |      HIL_PRU_CAP_WATCHDOG)

#define HIL_PRU_B1_CAPABILITIES     (HIL_PRU_CAP_TIMEBASE | HIL_PRU_CAP_RPMSG |      HIL_PRU_CAP_FORCE_SAFE | HIL_PRU_CAP_PWM_CAPTURE |      HIL_PRU_CAP_PWM_COMPLEMENTARY_MONITOR |      HIL_PRU_CAP_SHARED_SNAPSHOT)

/* Backward-compatible alias used by the B0 firmware. */
#define HIL_PRU_CAPABILITIES HIL_PRU_B0_CAPABILITIES

#define HIL_PRU_MSG_HELLO          (1u)
#define HIL_PRU_MSG_TIME           (2u)
#define HIL_PRU_MSG_GPIO_LOOPBACK  (3u)
#define HIL_PRU_MSG_FORCE_SAFE     (4u)
#define HIL_PRU_MSG_PING           (5u)
#define HIL_PRU_MSG_CAPTURE_CONFIG (6u)
#define HIL_PRU_MSG_CAPTURE_START  (7u)
#define HIL_PRU_MSG_CAPTURE_STOP   (8u)
#define HIL_PRU_MSG_CAPTURE_CLEAR  (9u)
#define HIL_PRU_MSG_CAPTURE_STATUS (10u)
#define HIL_PRU_MSG_RESPONSE_BIT   (0x8000u)

#define HIL_PRU_STATUS_OK              (0u)
#define HIL_PRU_ERR_BAD_LENGTH         (1u << 0)
#define HIL_PRU_ERR_BAD_MAGIC          (1u << 1)
#define HIL_PRU_ERR_BAD_VERSION        (1u << 2)
#define HIL_PRU_ERR_BAD_COMMAND        (1u << 3)
#define HIL_PRU_ERR_INVALID_ARGUMENT   (1u << 4)
#define HIL_PRU_ERR_LOOPBACK_NO_RISE   (1u << 5)
#define HIL_PRU_ERR_LOOPBACK_NO_FALL   (1u << 6)
#define HIL_PRU_ERR_CAPTURE_RUNNING    (1u << 7)

/*
 * Fixed-size binary RPMsg frame. Natural 32-bit alignment makes this 32 bytes
 * without compiler-specific packing pragmas.
 */
struct hil_pru_msg {
    uint32_t magic;
    uint16_t version;
    uint16_t type;
    uint32_t seq;
    uint32_t flags;
    uint32_t arg0;
    uint32_t arg1;
    uint32_t arg2;
    uint32_t arg3;
};

typedef char hil_pru_msg_must_be_32_bytes[
    (sizeof(struct hil_pru_msg) == 32u) ? 1 : -1
];

#endif
