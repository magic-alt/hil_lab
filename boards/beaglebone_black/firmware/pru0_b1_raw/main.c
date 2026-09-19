#include <stdint.h>
#include <pru_cfg.h>
#include <pru_iep.h>
#include <pru_intc.h>
#include <pru_rpmsg.h>

#include "../common/hil_pru_protocol.h"
#include "../common/raw_edge_capture.h"
#include "resource_table_0.h"
#include "intc_map_0.h"

volatile register uint32_t __R31;

#define VIRTIO_CONFIG_S_DRIVER_OK  (4u)
#define CHAN_NAME                   "rpmsg-pru"
#define CHAN_DESC                   "hil-b1-raw-pru0"
#define CHAN_PORT                   (30u)

#define HOST_INT                    ((uint32_t)1u << 30)
#define TO_ARM_HOST                 (16u)
#define FROM_ARM_HOST               (17u)

#define IEP_TICK_HZ                 (200000000u)
#define IEP_COUNTER_BITS            (32u)

/*
 * B1 fixed direct-input map on BeagleBone Black.
 * Keep the hot path in native R31 bit space; Linux performs logical remapping.
 *
 * UH -> P9_29 -> R31[1]
 * UL -> P9_30 -> R31[2]
 * VH -> P9_28 -> R31[3]
 * VL -> P9_27 -> R31[5]
 * WH -> P8_16 -> R31[14]
 * WL -> P8_15 -> R31[15]
 */
#define R31_UH_MASK                 (1u << 1)
#define R31_UL_MASK                 (1u << 2)
#define R31_VH_MASK                 (1u << 3)
#define R31_VL_MASK                 (1u << 5)
#define R31_WH_MASK                 (1u << 14)
#define R31_WL_MASK                 (1u << 15)
#define R31_PWM_INPUT_MASK          (R31_UH_MASK | R31_UL_MASK | R31_VH_MASK | \
                                     R31_VL_MASK | R31_WH_MASK | R31_WL_MASK)

union hil_rx_buffer {
    struct hil_pru_msg msg;
    uint8_t bytes[RPMSG_BUF_SIZE];
};

#pragma DATA_SECTION(g_raw_shared, ".shared_raw")
#pragma RETAIN(g_raw_shared)
volatile __far struct hil_raw_capture_shared g_raw_shared;

static struct pru_rpmsg_transport transport;
static union hil_rx_buffer rx_buffer;
static struct hil_pru_msg tx_msg;

static uint32_t tick_now(void)
{
    return CT_IEP.TMR_CNT;
}

static void init_timebase_if_needed(void)
{
    /*
     * PRU0 normally owns the BBB IEP timebase. Do not reset an already-running
     * IEP so a future PRU1 stimulus engine can share the same counter.
     */
    if (CT_IEP.TMR_GLB_CFG_bit.CNT_EN == 0u) {
        CT_IEP.TMR_CNT = 0u;
        CT_IEP.TMR_GLB_STS_bit.CNT_OVF = 1u;
        CT_IEP.TMR_GLB_CFG_bit.DEFAULT_INC = 1u;
        CT_IEP.TMR_GLB_CFG_bit.CNT_EN = 1u;
    }
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

static void raw_shared_init(void)
{
    uint32_t generation =
        ((g_raw_shared.magic == HIL_RAW_CAPTURE_MAGIC) &&
         (g_raw_shared.version == HIL_RAW_CAPTURE_VERSION))
            ? (g_raw_shared.generation + 1u)
            : 1u;

    g_raw_shared.magic = HIL_RAW_CAPTURE_MAGIC;
    g_raw_shared.version = HIL_RAW_CAPTURE_VERSION;
    g_raw_shared.total_size = (uint32_t)sizeof(struct hil_raw_capture_shared);
    g_raw_shared.tick_hz = IEP_TICK_HZ;
    g_raw_shared.capacity = HIL_RAW_CAPTURE_CAPACITY;
    g_raw_shared.running = 0u;
    g_raw_shared.configured_event_limit = HIL_RAW_CAPTURE_CAPACITY;
    g_raw_shared.event_count = 0u;
    g_raw_shared.initial_raw_inputs = 0u;
    g_raw_shared.final_raw_inputs = 0u;
    g_raw_shared.start_ticks = 0u;
    g_raw_shared.stop_ticks = 0u;
    g_raw_shared.stop_reason = HIL_RAW_STOP_NONE;
    g_raw_shared.input_mask = R31_PWM_INPUT_MASK;
    g_raw_shared.generation = generation;
    g_raw_shared.overflow_count = 0u;
}

static void publish_stop(
    uint32_t stop_reason,
    uint32_t stop_ticks,
    uint32_t raw_inputs,
    uint32_t event_count)
{
    g_raw_shared.final_raw_inputs = raw_inputs;
    g_raw_shared.event_count = event_count;
    g_raw_shared.stop_ticks = stop_ticks;
    g_raw_shared.stop_reason = stop_reason;

    /*
     * Publish running=0 last. Linux treats running==0 as the release point for
     * the frozen ring/header contents.
     */
    g_raw_shared.running = 0u;
}

static uint32_t run_capture_window(
    uint32_t event_limit,
    uint32_t initial_inputs)
{
    uint32_t event_count = 0u;
    uint32_t last_inputs = initial_inputs;
    uint32_t last_timestamp = g_raw_shared.start_ticks;

    /*
     * PRECISION CAPTURE KERNEL V2
     *
     * The no-change path is intentionally limited to:
     *   R31 sample -> PWM mask -> state compare -> branch back.
     *
     * There are no RPMsg/HOST_INT, start_pending or capture_running checks in
     * this window. Control returns to the ordinary main loop only after the
     * bounded event_limit is reached. This firmware is input-only, so host
     * silence during the short bounded window cannot create an unsafe output.
     */
    while (1) {
        uint32_t raw_inputs = __R31 & R31_PWM_INPUT_MASK;

        if (raw_inputs == last_inputs) {
            continue;
        }

        {
            uint32_t timestamp_ticks = tick_now();
            volatile __far struct hil_raw_edge_record *record =
                &g_raw_shared.ring[event_count];

            record->timestamp_ticks = timestamp_ticks;
            record->raw_inputs = raw_inputs;

            last_inputs = raw_inputs;
            last_timestamp = timestamp_ticks;
            event_count += 1u;
        }

        if (event_count >= event_limit) {
            break;
        }
    }

    publish_stop(
        HIL_RAW_STOP_EVENT_LIMIT,
        last_timestamp,
        last_inputs,
        event_count);

    return event_count;
}

static void handle_request(
    uint16_t len,
    uint32_t raw_inputs,
    uint32_t *capture_running,
    uint32_t *start_pending,
    uint32_t *last_inputs,
    uint32_t *event_count,
    uint32_t *event_limit)
{
    struct hil_pru_msg *request = &rx_buffer.msg;
    uint32_t now = tick_now();

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

    switch (request->type) {
    case HIL_PRU_MSG_HELLO:
        tx_msg.arg0 = HIL_PRU_B1_RAW_CAPABILITIES;
        tx_msg.arg1 = IEP_TICK_HZ;
        tx_msg.arg2 = IEP_COUNTER_BITS;
        tx_msg.arg3 = HIL_PRU_B1_RAW_FIRMWARE_VERSION;
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
        *start_pending = 0u;
        if (*capture_running != 0u) {
            publish_stop(
                HIL_RAW_STOP_FORCE_SAFE,
                now,
                raw_inputs,
                *event_count);
            *capture_running = 0u;
        }
        tx_msg.arg0 = now;
        tx_msg.arg1 = *event_count;
        break;

    case HIL_PRU_MSG_RAW_CONFIG:
        if ((*capture_running != 0u) || (*start_pending != 0u)) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        if ((request->arg0 == 0u) ||
            (request->arg0 > HIL_RAW_CAPTURE_CAPACITY)) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }
        *event_limit = request->arg0;
        g_raw_shared.configured_event_limit = request->arg0;
        tx_msg.arg0 = request->arg0;
        tx_msg.arg1 = HIL_RAW_CAPTURE_CAPACITY;
        break;

    case HIL_PRU_MSG_RAW_CLEAR:
        if ((*capture_running != 0u) || (*start_pending != 0u)) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        raw_shared_init();
        g_raw_shared.configured_event_limit = *event_limit;
        *event_count = 0u;
        *last_inputs = raw_inputs;
        tx_msg.arg0 = g_raw_shared.generation;
        break;

    case HIL_PRU_MSG_RAW_START:
        if ((*capture_running != 0u) || (*start_pending != 0u)) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }

        /*
         * Do not enter the precise window inside RPMsg handling.
         *
         * raw_inputs was sampled before receiving/decoding/sending this
         * command and can already be stale by several PWM transitions. The
         * main loop arms capture only after the RAW_START response has been
         * sent, then takes a fresh R31 + IEP baseline.
         */
        *event_count = 0u;
        *start_pending = 1u;

        g_raw_shared.event_count = 0u;
        g_raw_shared.stop_ticks = 0u;
        g_raw_shared.stop_reason = HIL_RAW_STOP_NONE;
        g_raw_shared.overflow_count = 0u;
        g_raw_shared.running = 0u;

        tx_msg.arg0 = now;        /* arm-request timestamp, not capture start */
        tx_msg.arg1 = raw_inputs; /* diagnostic pre-arm sample only */
        tx_msg.arg2 = *event_limit;
        break;

    case HIL_PRU_MSG_RAW_STOP:
        if (*start_pending != 0u) {
            *start_pending = 0u;
            g_raw_shared.stop_ticks = now;
            g_raw_shared.stop_reason = HIL_RAW_STOP_HOST_REQUEST;
            g_raw_shared.running = 0u;
        }
        if (*capture_running != 0u) {
            publish_stop(
                HIL_RAW_STOP_HOST_REQUEST,
                now,
                raw_inputs,
                *event_count);
            *capture_running = 0u;
        }
        tx_msg.arg0 = now;
        tx_msg.arg1 = *event_count;
        tx_msg.arg2 = g_raw_shared.stop_reason;
        break;

    case HIL_PRU_MSG_RAW_STATUS:
        /*
         * A status request during capture necessarily perturbs the acquisition
         * loop. Publish the current count for diagnostics, but precise tests
         * should use a bounded event_limit and query only after auto-stop.
         */
        g_raw_shared.event_count = *event_count;
        g_raw_shared.final_raw_inputs = raw_inputs;
        tx_msg.arg0 = ((*capture_running != 0u) || (*start_pending != 0u)) ? 1u : 0u;
        tx_msg.arg1 = *event_count;
        tx_msg.arg2 = *event_limit;
        tx_msg.arg3 = g_raw_shared.stop_reason;
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
    uint32_t start_pending = 0u;
    uint32_t event_count = 0u;
    uint32_t event_limit = HIL_RAW_CAPTURE_CAPACITY;
    uint32_t last_inputs;

    CT_CFG.SYSCFG_bit.STANDBY_INIT = 0u;
    init_timebase_if_needed();

    last_inputs = __R31 & R31_PWM_INPUT_MASK;
    raw_shared_init();
    g_raw_shared.initial_raw_inputs = last_inputs;
    g_raw_shared.final_raw_inputs = last_inputs;

    CT_INTC.SICR_bit.STS_CLR_IDX = FROM_ARM_HOST;

    driver_status = &resourceTable.rpmsg_vdev.status;
    while (((*driver_status) & VIRTIO_CONFIG_S_DRIVER_OK) == 0u) {
        /* Input-only firmware; no real-time output exists while waiting. */
    }

    if (pru_rpmsg_init(&transport,
                       &resourceTable.rpmsg_vring0,
                       &resourceTable.rpmsg_vring1,
                       TO_ARM_HOST,
                       FROM_ARM_HOST) != PRU_RPMSG_SUCCESS) {
        while (1) {
        }
    }

    while (pru_rpmsg_channel(RPMSG_NS_CREATE,
                             &transport,
                             CHAN_NAME,
                             CHAN_DESC,
                             CHAN_PORT) != PRU_RPMSG_SUCCESS) {
    }

    while (1) {
        uint32_t raw_r31;
        uint32_t raw_inputs;

        /*
         * RAW_START is acknowledged first. Only after the response has left
         * PRU0 do we take a fresh R31/IEP baseline and publish running=1.
         * This prevents the first raw record from comparing against a stale
         * control-plane sample and creating a synthetic zero-dead-time edge.
         */
        if (start_pending != 0u) {
            uint32_t baseline_raw = __R31 & R31_PWM_INPUT_MASK;
            uint32_t baseline_ticks = tick_now();

            event_count = 0u;
            last_inputs = baseline_raw;

            g_raw_shared.event_count = 0u;
            g_raw_shared.initial_raw_inputs = baseline_raw;
            g_raw_shared.final_raw_inputs = baseline_raw;
            g_raw_shared.start_ticks = baseline_ticks;
            g_raw_shared.stop_ticks = 0u;
            g_raw_shared.stop_reason = HIL_RAW_STOP_NONE;
            g_raw_shared.overflow_count = 0u;

            capture_running = 1u;
            start_pending = 0u;

            /* Publish running=1 last, after the fresh baseline is complete. */
            g_raw_shared.running = 1u;

            /*
             * Enter the dedicated precision kernel. No control-plane checks
             * occur until the bounded event limit freezes the capture.
             */
            event_count = run_capture_window(event_limit, baseline_raw);
            capture_running = 0u;
            continue;
        }

        raw_r31 = __R31;
        raw_inputs = raw_r31 & R31_PWM_INPUT_MASK;

        if ((raw_r31 & HOST_INT) != 0u) {
            CT_INTC.SICR_bit.STS_CLR_IDX = FROM_ARM_HOST;

            while (pru_rpmsg_receive(&transport,
                                     &src,
                                     &dst,
                                     rx_buffer.bytes,
                                     &len) == PRU_RPMSG_SUCCESS) {
                handle_request(
                    len,
                    raw_inputs,
                    &capture_running,
                    &start_pending,
                    &last_inputs,
                    &event_count,
                    &event_limit);

                pru_rpmsg_send(&transport,
                               dst,
                               src,
                               (uint8_t *)&tx_msg,
                               (uint16_t)sizeof(tx_msg));
            }
        }
    }
}
