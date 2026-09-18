#include <stdint.h>
#include <pru_cfg.h>
#include <pru_iep.h>
#include <pru_intc.h>
#include <pru_rpmsg.h>

#include "../common/hil_pru_protocol.h"
#include "../common/pwm_capture_core.h"
#include "resource_table_0.h"
#include "intc_map_0.h"

volatile register uint32_t __R31;

#define VIRTIO_CONFIG_S_DRIVER_OK  (4u)
#define CHAN_NAME                   "rpmsg-pru"
#define CHAN_DESC                   "hil-b1-pru0"
#define CHAN_PORT                   (30u)

#define HOST_INT                    ((uint32_t)1u << 30)
#define TO_ARM_HOST                 (16u)
#define FROM_ARM_HOST               (17u)

#define IEP_TICK_HZ                 (200000000u)
#define IEP_COUNTER_BITS            (32u)

/*
 * B1 fixed direct-input map on BeagleBone Black:
 * logical 0 UH -> P9_29 -> R31[1]
 * logical 1 UL -> P9_30 -> R31[2]
 * logical 2 VH -> P9_28 -> R31[3]
 * logical 3 VL -> P9_27 -> R31[5]
 * logical 4 WH -> P8_16 -> R31[14]
 * logical 5 WL -> P8_15 -> R31[15]
 */
#define R31_UH_MASK                 (1u << 1)
#define R31_UL_MASK                 (1u << 2)
#define R31_VH_MASK                 (1u << 3)
#define R31_VL_MASK                 (1u << 5)
#define R31_WH_MASK                 (1u << 14)
#define R31_WL_MASK                 (1u << 15)
#define R31_PWM_INPUT_MASK     (R31_UH_MASK | R31_UL_MASK | R31_VH_MASK |      R31_VL_MASK | R31_WH_MASK | R31_WL_MASK)

union hil_rx_buffer {
    struct hil_pru_msg msg;
    uint8_t bytes[RPMSG_BUF_SIZE];
};

#pragma DATA_SECTION(g_pwm_shared, ".shared_pwm")
#pragma RETAIN(g_pwm_shared)
volatile __far struct hil_pwm_shared g_pwm_shared;

static struct pru_rpmsg_transport transport;
static union hil_rx_buffer rx_buffer;
static struct hil_pru_msg tx_msg;

static uint32_t tick_now(void)
{
    return CT_IEP.TMR_CNT;
}

static void init_timebase(void)
{
    CT_IEP.TMR_GLB_CFG_bit.CNT_EN = 0u;
    CT_IEP.TMR_CNT = 0u;
    CT_IEP.TMR_GLB_STS_bit.CNT_OVF = 1u;
    CT_IEP.TMR_GLB_CFG_bit.DEFAULT_INC = 1u;
    CT_IEP.TMR_GLB_CFG_bit.CNT_EN = 1u;
}

static uint32_t pack_pwm_inputs(uint32_t raw_r31)
{
    uint32_t logical = 0u;

    if ((raw_r31 & R31_UH_MASK) != 0u)
        logical |= 1u << HIL_PWM_CH_UH;
    if ((raw_r31 & R31_UL_MASK) != 0u)
        logical |= 1u << HIL_PWM_CH_UL;
    if ((raw_r31 & R31_VH_MASK) != 0u)
        logical |= 1u << HIL_PWM_CH_VH;
    if ((raw_r31 & R31_VL_MASK) != 0u)
        logical |= 1u << HIL_PWM_CH_VL;
    if ((raw_r31 & R31_WH_MASK) != 0u)
        logical |= 1u << HIL_PWM_CH_WH;
    if ((raw_r31 & R31_WL_MASK) != 0u)
        logical |= 1u << HIL_PWM_CH_WL;

    return logical;
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

static void handle_request(
    uint16_t len,
    uint32_t raw_r31,
    uint32_t *capture_running,
    uint32_t *last_inputs)
{
    struct hil_pru_msg *request = &rx_buffer.msg;
    uint32_t now;
    uint32_t logical_inputs;

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

    now = tick_now();
    logical_inputs = pack_pwm_inputs(raw_r31);

    switch (request->type) {
    case HIL_PRU_MSG_HELLO:
        tx_msg.arg0 = HIL_PRU_B1_CAPABILITIES;
        tx_msg.arg1 = IEP_TICK_HZ;
        tx_msg.arg2 = IEP_COUNTER_BITS;
        tx_msg.arg3 = HIL_PRU_B1_FIRMWARE_VERSION;
        break;

    case HIL_PRU_MSG_TIME:
        tx_msg.arg0 = now;
        tx_msg.arg1 = IEP_TICK_HZ;
        tx_msg.arg2 = IEP_COUNTER_BITS;
        break;

    case HIL_PRU_MSG_PING:
        tx_msg.arg0 = now;
        break;

    case HIL_PRU_MSG_FORCE_SAFE:
        hil_pwm_capture_stop(&g_pwm_shared);
        *capture_running = 0u;
        tx_msg.arg0 = now;
        break;

    case HIL_PRU_MSG_CAPTURE_CONFIG:
        hil_pwm_capture_set_min_deadtime(&g_pwm_shared, request->arg0);
        tx_msg.arg0 = g_pwm_shared.min_deadtime_ticks;
        break;

    case HIL_PRU_MSG_CAPTURE_START:
        *last_inputs = logical_inputs;
        hil_pwm_capture_start(&g_pwm_shared, now, logical_inputs);
        *capture_running = 1u;
        tx_msg.arg0 = now;
        tx_msg.arg1 = logical_inputs;
        break;

    case HIL_PRU_MSG_CAPTURE_STOP:
        hil_pwm_capture_stop(&g_pwm_shared);
        *capture_running = 0u;
        tx_msg.arg0 = now;
        break;

    case HIL_PRU_MSG_CAPTURE_CLEAR:
        *last_inputs = logical_inputs;
        hil_pwm_capture_clear(&g_pwm_shared, logical_inputs);
        tx_msg.arg0 = g_pwm_shared.event_seq;
        break;

    case HIL_PRU_MSG_CAPTURE_STATUS:
        tx_msg.arg0 = g_pwm_shared.running;
        tx_msg.arg1 = g_pwm_shared.min_deadtime_ticks;
        tx_msg.arg2 = g_pwm_shared.fault_flags;
        tx_msg.arg3 = g_pwm_shared.event_seq;
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
    uint32_t capture_running = 0u;
    uint32_t last_inputs;

    CT_CFG.SYSCFG_bit.STANDBY_INIT = 0u;
    init_timebase();

    last_inputs = pack_pwm_inputs(__R31);
    hil_pwm_capture_init(&g_pwm_shared, IEP_TICK_HZ, 0u);
    g_pwm_shared.input_bits = last_inputs;

    CT_INTC.SICR_bit.STS_CLR_IDX = FROM_ARM_HOST;

    driver_status = &resourceTable.rpmsg_vdev.status;
    while (((*driver_status) & VIRTIO_CONFIG_S_DRIVER_OK) == 0u) {
        /* Input-only B1 firmware has no active stimulus while waiting. */
    }

    if (pru_rpmsg_init(&transport,
                       &resourceTable.rpmsg_vring0,
                       &resourceTable.rpmsg_vring1,
                       TO_ARM_HOST,
                       FROM_ARM_HOST) != PRU_RPMSG_SUCCESS) {
        while (1) {
            /* Invalid RPMsg event configuration is non-recoverable. */
        }
    }

    while (pru_rpmsg_channel(RPMSG_NS_CREATE,
                             &transport,
                             CHAN_NAME,
                             CHAN_DESC,
                             CHAN_PORT) != PRU_RPMSG_SUCCESS) {
        /* Wait for Linux RPMsg channel creation. */
    }

    while (1) {
        uint32_t raw_r31 = __R31;

        /*
         * Real-time data plane:
         * one R31 sample per loop, then only timestamp/process if any of the
         * six direct-input PWM bits changed. Linux is not in this path.
         */
        if (capture_running != 0u) {
            uint32_t logical_inputs = pack_pwm_inputs(raw_r31);
            if (logical_inputs != last_inputs) {
                uint32_t timestamp_ticks = tick_now();
                hil_pwm_capture_process(&g_pwm_shared, timestamp_ticks, logical_inputs);
                last_inputs = logical_inputs;
            }
        }

        /*
         * Control plane: RPMsg is checked after the capture sample. Commands
         * configure/start/stop/snapshot metadata but never carry individual
         * PWM edges.
         */
        if ((raw_r31 & HOST_INT) != 0u) {
            CT_INTC.SICR_bit.STS_CLR_IDX = FROM_ARM_HOST;

            while (pru_rpmsg_receive(&transport,
                                     &src,
                                     &dst,
                                     rx_buffer.bytes,
                                     &len) == PRU_RPMSG_SUCCESS) {
                handle_request(
                    len,
                    raw_r31,
                    &capture_running,
                    &last_inputs);
                pru_rpmsg_send(&transport,
                               dst,
                               src,
                               (uint8_t *)&tx_msg,
                               (uint16_t)sizeof(tx_msg));
            }
        }
    }
}
