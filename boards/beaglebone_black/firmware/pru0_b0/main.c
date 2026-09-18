#include <stdint.h>
#include <pru_cfg.h>
#include <pru_iep.h>
#include <sys_mailbox.h>
#include <pru_rpmsg.h>
#include <pru_virtqueue.h>

#include "../common/hil_pru_protocol.h"
#include "resource_table_0.h"

volatile register uint32_t __R30;
volatile register uint32_t __R31;

#define VIRTIO_CONFIG_S_DRIVER_OK  (4u)
#define CHAN_NAME                   "rpmsg-pru"
#define CHAN_DESC                   "hil-b0-pru0"
#define CHAN_PORT                   (30u)

/* AM335x PRU0 RPMsg mailbox assignment from the Linux PRUSS DT binding. */
#define MB_FROM_ARM_HOST             (2u)
#define MB_TO_ARM_HOST               (3u)

/* B0 temporary loopback fixture only: P9_31 -> P9_25 jumper. */
#define LOOPBACK_OUT_R30_BIT        (0u)  /* P9_31 pru0_r30[0] */
#define LOOPBACK_IN_R31_BIT         (7u)  /* P9_25 pru0_r31[7] */
#define LOOPBACK_OUT_MASK           (1u << LOOPBACK_OUT_R30_BIT)
#define LOOPBACK_IN_MASK            (1u << LOOPBACK_IN_R31_BIT)

#define IEP_TICK_HZ                 (200000000u)
#define IEP_COUNTER_BITS            (32u)
#define WATCHDOG_TICKS              (200000000u) /* 1 s */
#define MAX_LOOPBACK_DELAY_TICKS    (2000000u)   /* 10 ms */
#define MAX_LOOPBACK_WIDTH_TICKS    (2000000u)   /* 10 ms */
#define MAX_LOOPBACK_TIMEOUT_TICKS  (4000000u)   /* 20 ms */
#define TICK_NOT_SEEN               (0xffffffffu)

union hil_rx_buffer {
    struct hil_pru_msg msg;
    uint8_t bytes[RPMSG_BUF_SIZE];
};

static struct pru_rpmsg_transport transport;
static union hil_rx_buffer rx_buffer;
static struct hil_pru_msg tx_msg;
static uint32_t last_host_tick;

static uint32_t tick_now(void)
{
    return CT_IEP.TMR_CNT;
}

static uint32_t tick_elapsed(uint32_t now, uint32_t then)
{
    return now - then;
}

static uint8_t tick_reached(uint32_t now, uint32_t target)
{
    return ((int32_t)(now - target) >= 0) ? 1u : 0u;
}

static void force_safe(void)
{
    __R30 &= ~LOOPBACK_OUT_MASK;
}

static void init_timebase(void)
{
    CT_IEP.TMR_GLB_CFG_bit.CNT_EN = 0u;
    CT_IEP.TMR_CNT = 0u;
    CT_IEP.TMR_GLB_STS_bit.CNT_OVF = 1u;
    CT_IEP.TMR_GLB_CFG_bit.DEFAULT_INC = 1u;
    CT_IEP.TMR_GLB_CFG_bit.CNT_EN = 1u;
}

static void clear_response(uint16_t request_type, uint32_t seq)
{
    tx_msg.magic = HIL_PRU_MAGIC;
    tx_msg.version = HIL_PRU_PROTOCOL_VERSION;
    tx_msg.type = (uint16_t)(request_type | HIL_PRU_MSG_RESPONSE_BIT);
    tx_msg.seq = seq;
    tx_msg.flags = HIL_PRU_STATUS_OK;
    tx_msg.arg0 = 0u;
    tx_msg.arg1 = 0u;
    tx_msg.arg2 = 0u;
    tx_msg.arg3 = 0u;
}

static uint32_t run_gpio_loopback(uint32_t delay_ticks,
                                  uint32_t width_ticks,
                                  uint32_t timeout_ticks,
                                  uint32_t *requested_start,
                                  uint32_t *observed_rise,
                                  uint32_t *observed_fall)
{
    uint32_t status = HIL_PRU_STATUS_OK;
    uint32_t now;
    uint32_t fall_target;
    uint32_t fall_wait_start;

    *observed_rise = TICK_NOT_SEEN;
    *observed_fall = TICK_NOT_SEEN;

    if ((delay_ticks > MAX_LOOPBACK_DELAY_TICKS) ||
        (width_ticks == 0u) ||
        (width_ticks > MAX_LOOPBACK_WIDTH_TICKS) ||
        (timeout_ticks == 0u) ||
        (timeout_ticks > MAX_LOOPBACK_TIMEOUT_TICKS)) {
        force_safe();
        return HIL_PRU_ERR_INVALID_ARGUMENT;
    }

    force_safe();
    *requested_start = tick_now() + delay_ticks;

    do {
        now = tick_now();
    } while (!tick_reached(now, *requested_start));

    __R30 |= LOOPBACK_OUT_MASK;
    fall_target = *requested_start + width_ticks;

    do {
        now = tick_now();
        if ((*observed_rise == TICK_NOT_SEEN) && ((__R31 & LOOPBACK_IN_MASK) != 0u)) {
            *observed_rise = now;
        }
    } while (!tick_reached(now, fall_target));

    force_safe();
    fall_wait_start = tick_now();

    do {
        now = tick_now();
        if ((__R31 & LOOPBACK_IN_MASK) == 0u) {
            *observed_fall = now;
            break;
        }
    } while (tick_elapsed(now, fall_wait_start) <= timeout_ticks);

    if (*observed_rise == TICK_NOT_SEEN) {
        status |= HIL_PRU_ERR_LOOPBACK_NO_RISE;
    }
    if (*observed_fall == TICK_NOT_SEEN) {
        status |= HIL_PRU_ERR_LOOPBACK_NO_FALL;
    }

    force_safe();
    return status;
}

static void handle_request(uint16_t len)
{
    struct hil_pru_msg *request = &rx_buffer.msg;
    uint32_t requested_start = 0u;
    uint32_t observed_rise = TICK_NOT_SEEN;
    uint32_t observed_fall = TICK_NOT_SEEN;

    if (len != sizeof(struct hil_pru_msg)) {
        clear_response(0u, 0u);
        tx_msg.flags = HIL_PRU_ERR_BAD_LENGTH;
        return;
    }

    clear_response(request->type, request->seq);

    if (request->magic != HIL_PRU_MAGIC) {
        tx_msg.flags = HIL_PRU_ERR_BAD_MAGIC;
        return;
    }
    if (request->version != HIL_PRU_PROTOCOL_VERSION) {
        tx_msg.flags = HIL_PRU_ERR_BAD_VERSION;
        return;
    }

    last_host_tick = tick_now();

    switch (request->type) {
    case HIL_PRU_MSG_HELLO:
        tx_msg.arg0 = HIL_PRU_CAPABILITIES;
        tx_msg.arg1 = IEP_TICK_HZ;
        tx_msg.arg2 = IEP_COUNTER_BITS;
        tx_msg.arg3 = HIL_PRU_FIRMWARE_VERSION;
        break;

    case HIL_PRU_MSG_TIME:
        tx_msg.arg0 = tick_now();
        tx_msg.arg1 = IEP_TICK_HZ;
        tx_msg.arg2 = IEP_COUNTER_BITS;
        break;

    case HIL_PRU_MSG_GPIO_LOOPBACK:
        tx_msg.flags = run_gpio_loopback(
            request->arg0,
            request->arg1,
            request->arg2,
            &requested_start,
            &observed_rise,
            &observed_fall);
        tx_msg.arg0 = requested_start;
        tx_msg.arg1 = observed_rise;
        tx_msg.arg2 = observed_fall;
        tx_msg.arg3 = tick_now();
        break;

    case HIL_PRU_MSG_FORCE_SAFE:
        force_safe();
        tx_msg.arg0 = tick_now();
        break;

    case HIL_PRU_MSG_PING:
        tx_msg.arg0 = tick_now();
        break;

    default:
        tx_msg.flags = HIL_PRU_ERR_BAD_COMMAND;
        break;
    }
}

void main(void)
{
    uint16_t src = 0u;
    uint16_t dst = 0u;
    uint16_t len = 0u;
    volatile uint8_t *driver_status;

    force_safe();
    CT_CFG.SYSCFG_bit.STANDBY_INIT = 0u;
    init_timebase();

    driver_status = &resourceTable.rpmsg_vdev.status;
    while (((*driver_status) & VIRTIO_CONFIG_S_DRIVER_OK) == 0u) {
        force_safe();
    }

    pru_virtqueue_init(&transport.virtqueue0,
                       &resourceTable.rpmsg_vring0,
                       &CT_MBX.MESSAGE[MB_TO_ARM_HOST],
                       &CT_MBX.MESSAGE[MB_FROM_ARM_HOST]);
    pru_virtqueue_init(&transport.virtqueue1,
                       &resourceTable.rpmsg_vring1,
                       &CT_MBX.MESSAGE[MB_TO_ARM_HOST],
                       &CT_MBX.MESSAGE[MB_FROM_ARM_HOST]);

    while (pru_rpmsg_channel(RPMSG_NS_CREATE,
                             &transport,
                             CHAN_NAME,
                             CHAN_DESC,
                             CHAN_PORT) != PRU_RPMSG_SUCCESS) {
        force_safe();
    }

    last_host_tick = tick_now();

    while (1) {
        uint32_t now = tick_now();

        if (tick_elapsed(now, last_host_tick) > WATCHDOG_TICKS) {
            force_safe();
        }

        if (CT_MBX.MESSAGE[MB_FROM_ARM_HOST] == 1u) {
            if (pru_rpmsg_receive(&transport,
                                  &src,
                                  &dst,
                                  rx_buffer.bytes,
                                  &len) == PRU_RPMSG_SUCCESS) {
                handle_request(len);
                pru_rpmsg_send(&transport,
                               dst,
                               src,
                               (uint8_t *)&tx_msg,
                               (uint16_t)sizeof(tx_msg));
            }
        }
    }
}
