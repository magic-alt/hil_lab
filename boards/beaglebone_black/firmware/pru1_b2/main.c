#include <stdint.h>
#include <pru_cfg.h>
#include <pru_iep.h>
#include <pru_intc.h>
#include <pru_rpmsg.h>

#include "../common/hil_pru_protocol.h"
#include "resource_table_1.h"
#include "intc_map_1.h"

volatile register uint32_t __R30;
volatile register uint32_t __R31;

#define VIRTIO_CONFIG_S_DRIVER_OK  (4u)
#define CHAN_NAME                   "rpmsg-pru"
#define CHAN_DESC                   "hil-b2-pru1"
#define CHAN_PORT                   (31u)

#define HOST_INT                    ((uint32_t)1u << 31)
#define TO_ARM_HOST                 (18u)
#define FROM_ARM_HOST               (19u)

#define IEP_TICK_HZ                 (200000000u)
#define IEP_COUNTER_BITS            (32u)

/*
 * First B2.1 ABZ pin map:
 *   A -> P8_45 -> PRU1 R30[0]
 *   B -> P8_46 -> PRU1 R30[1]
 *   Z -> P8_43 -> PRU1 R30[2]
 */
#define ABZ_A_MASK                  (1u << 0)
#define ABZ_B_MASK                  (1u << 1)
#define ABZ_Z_MASK                  (1u << 2)
#define ABZ_OUTPUT_MASK             (ABZ_A_MASK | ABZ_B_MASK | ABZ_Z_MASK)

#define ABZ_MIN_TRANSITION_TICKS    (100u)
#define ABZ_DEFAULT_TRANSITION_TICKS (200000u)

union hil_rx_buffer {
    struct hil_pru_msg msg;
    uint8_t bytes[RPMSG_BUF_SIZE];
};

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
     * B2 shares the PRU-ICSS IEP timebase with B1. PRU1 must not reset an
     * already-running counter because that would corrupt PRU0 capture time.
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

static uint32_t phase_to_ab(uint32_t phase)
{
    /*
     * Forward Gray-code sequence, A leads B:
     *   phase 0: 00
     *   phase 1: 10
     *   phase 2: 11
     *   phase 3: 01
     */
    switch (phase & 3u) {
    case 1u:
        return ABZ_A_MASK;
    case 2u:
        return ABZ_A_MASK | ABZ_B_MASK;
    case 3u:
        return ABZ_B_MASK;
    default:
        return 0u;
    }
}

static void apply_abz(uint32_t phase, uint32_t index_active)
{
    uint32_t outputs = __R30;
    uint32_t abz = phase_to_ab(phase);

    if (index_active != 0u)
        abz |= ABZ_Z_MASK;

    outputs &= ~ABZ_OUTPUT_MASK;
    outputs |= abz;
    __R30 = outputs;
}

static void force_safe_outputs(void)
{
    __R30 &= ~ABZ_OUTPUT_MASK;
}

static uint32_t index_is_active(
    uint32_t index_period_transitions,
    uint32_t index_width_transitions,
    uint32_t index_phase)
{
    return ((index_period_transitions != 0u) &&
            (index_width_transitions != 0u) &&
            (index_phase < index_width_transitions)) ? 1u : 0u;
}

static void handle_request(
    uint16_t len,
    uint32_t *running,
    uint32_t *transition_ticks,
    uint32_t *index_period_transitions,
    uint32_t *index_width_transitions,
    uint32_t *initial_phase,
    uint32_t *phase,
    uint32_t *direction,
    uint32_t *transition_count,
    uint32_t *index_phase,
    uint32_t *next_transition_ticks,
    uint32_t *late_transition_count,
    uint32_t *last_apply_ticks)
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
        tx_msg.arg0 = HIL_PRU_B2_CAPABILITIES;
        tx_msg.arg1 = IEP_TICK_HZ;
        tx_msg.arg2 = IEP_COUNTER_BITS;
        tx_msg.arg3 = HIL_PRU_B2_FIRMWARE_VERSION;
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
        *running = 0u;
        force_safe_outputs();
        *last_apply_ticks = now;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *transition_count;
        break;

    case HIL_PRU_MSG_ABZ_CONFIG: {
        uint32_t requested_direction = request->arg3 & 1u;
        uint32_t requested_phase = (request->arg3 >> 8) & 3u;

        if (*running != 0u) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        if ((request->arg0 < ABZ_MIN_TRANSITION_TICKS) ||
            (request->arg0 >= 0x80000000u)) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }
        if ((request->arg1 == 0u && request->arg2 != 0u) ||
            (request->arg1 != 0u && request->arg2 > request->arg1)) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }

        *transition_ticks = request->arg0;
        *index_period_transitions = request->arg1;
        *index_width_transitions = request->arg2;
        *direction = requested_direction;
        *initial_phase = requested_phase;
        *phase = requested_phase;
        *transition_count = 0u;
        *index_phase = 0u;
        *late_transition_count = 0u;
        force_safe_outputs();

        tx_msg.arg0 = *transition_ticks;
        tx_msg.arg1 = *index_period_transitions;
        tx_msg.arg2 = *index_width_transitions;
        tx_msg.arg3 = (*direction & 1u) | ((*initial_phase & 3u) << 8);
        break;
    }

    case HIL_PRU_MSG_ABZ_START: {
        uint32_t z_active;

        if (*running != 0u) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }

        *phase = *initial_phase;
        *transition_count = 0u;
        *index_phase = 0u;
        *late_transition_count = 0u;

        z_active = index_is_active(
            *index_period_transitions,
            *index_width_transitions,
            *index_phase);

        apply_abz(*phase, z_active);

        *last_apply_ticks = now;
        *next_transition_ticks = now + *transition_ticks;
        *running = 1u;

        tx_msg.arg0 = now;
        tx_msg.arg1 = phase_to_ab(*phase) |
                      (z_active ? ABZ_Z_MASK : 0u);
        tx_msg.arg2 = *next_transition_ticks;
        tx_msg.arg3 = *direction;
        break;
    }

    case HIL_PRU_MSG_ABZ_STOP:
        *running = 0u;
        force_safe_outputs();
        *last_apply_ticks = now;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *transition_count;
        tx_msg.arg2 = *late_transition_count;
        break;

    case HIL_PRU_MSG_ABZ_DIRECTION:
        if (request->arg0 > 1u) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }
        *direction = request->arg0;
        *last_apply_ticks = now;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *direction;
        tx_msg.arg2 = *transition_count;
        break;

    case HIL_PRU_MSG_ABZ_STATUS:
        tx_msg.arg0 = *running;
        tx_msg.arg1 = *transition_ticks;
        tx_msg.arg2 = *transition_count;
        tx_msg.arg3 = *late_transition_count;
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

    uint32_t running = 0u;
    uint32_t transition_ticks = ABZ_DEFAULT_TRANSITION_TICKS;
    uint32_t index_period_transitions = 0u;
    uint32_t index_width_transitions = 0u;
    uint32_t initial_phase = 0u;
    uint32_t phase = 0u;
    uint32_t direction = 0u;
    uint32_t transition_count = 0u;
    uint32_t index_phase = 0u;
    uint32_t next_transition_ticks = 0u;
    uint32_t late_transition_count = 0u;
    uint32_t last_apply_ticks = 0u;

    CT_CFG.SYSCFG_bit.STANDBY_INIT = 0u;

    /* PRU1 GPI/GPO Mode 0: direct R30/R31. */
    CT_CFG.GPCFG1 = 0u;

    init_timebase_if_needed();
    force_safe_outputs();

    CT_INTC.SICR_bit.STS_CLR_IDX = FROM_ARM_HOST;

    driver_status = &resourceTable.rpmsg_vdev.status;
    while (((*driver_status) & VIRTIO_CONFIG_S_DRIVER_OK) == 0u) {
        force_safe_outputs();
    }

    if (pru_rpmsg_init(&transport,
                       &resourceTable.rpmsg_vring0,
                       &resourceTable.rpmsg_vring1,
                       TO_ARM_HOST,
                       FROM_ARM_HOST) != PRU_RPMSG_SUCCESS) {
        force_safe_outputs();
        while (1) {
        }
    }

    while (pru_rpmsg_channel(RPMSG_NS_CREATE,
                             &transport,
                             CHAN_NAME,
                             CHAN_DESC,
                             CHAN_PORT) != PRU_RPMSG_SUCCESS) {
        force_safe_outputs();
    }

    while (1) {
        uint32_t now = tick_now();

        if (running != 0u) {
            if ((int32_t)(now - next_transition_ticks) >= 0) {
                uint32_t lateness = now - next_transition_ticks;
                uint32_t z_active;

                if (lateness >= transition_ticks)
                    late_transition_count += 1u;

                if (direction == 0u)
                    phase = (phase + 1u) & 3u;
                else
                    phase = (phase + 3u) & 3u;

                transition_count += 1u;

                if (index_period_transitions != 0u) {
                    index_phase += 1u;
                    if (index_phase >= index_period_transitions)
                        index_phase = 0u;
                } else {
                    index_phase = 0u;
                }

                z_active = index_is_active(
                    index_period_transitions,
                    index_width_transitions,
                    index_phase);

                apply_abz(phase, z_active);
                last_apply_ticks = now;

                /*
                 * Phase-locked schedule: do not derive the next deadline from
                 * the delayed actual apply time. late_transition_count exposes
                 * missed-rate operation for characterization.
                 */
                next_transition_ticks += transition_ticks;
                continue;
            }
        }

        if ((__R31 & HOST_INT) != 0u) {
            CT_INTC.SICR_bit.STS_CLR_IDX = FROM_ARM_HOST;

            while (pru_rpmsg_receive(&transport,
                                     &src,
                                     &dst,
                                     rx_buffer.bytes,
                                     &len) == PRU_RPMSG_SUCCESS) {
                handle_request(
                    len,
                    &running,
                    &transition_ticks,
                    &index_period_transitions,
                    &index_width_transitions,
                    &initial_phase,
                    &phase,
                    &direction,
                    &transition_count,
                    &index_phase,
                    &next_transition_ticks,
                    &late_transition_count,
                    &last_apply_ticks);

                pru_rpmsg_send(&transport,
                               dst,
                               src,
                               (uint8_t *)&tx_msg,
                               (uint16_t)sizeof(tx_msg));
            }
        }
    }
}
