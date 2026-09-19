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

#define STIM_MODE_NONE              (0u)
#define STIM_MODE_ABZ               (1u)
#define STIM_MODE_HALL              (2u)

#define STIM_STATE_IDLE             (0u)
#define STIM_STATE_RUNNING          (1u)
#define STIM_STATE_ARMED            (2u)

#define ABZ_A_MASK                  (1u << 0)
#define ABZ_B_MASK                  (1u << 1)
#define ABZ_Z_MASK                  (1u << 2)
#define STIM_OUTPUT_MASK            (ABZ_A_MASK | ABZ_B_MASK | ABZ_Z_MASK)

#define ABZ_MIN_TRANSITION_TICKS    (100u)
#define ABZ_DEFAULT_TRANSITION_TICKS (200000u)
#define HALL_MIN_TRANSITION_TICKS   (100u)
#define HALL_DEFAULT_TRANSITION_TICKS (200000u)

#define ABZ_SCHED_TRANSITION_VALID  (1u << 0)
#define ABZ_SCHED_DIRECTION_VALID   (1u << 1)

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

static uint32_t time_due(uint32_t now, uint32_t deadline)
{
    return ((int32_t)(now - deadline) >= 0) ? 1u : 0u;
}

static uint32_t time_is_future(uint32_t now, uint32_t deadline)
{
    int32_t delta = (int32_t)(deadline - now);
    return (delta > 0) ? 1u : 0u;
}

static void init_timebase_if_needed(void)
{
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

static uint32_t hall_step_to_bits(uint32_t step)
{
    /*
     * Forward six-step Hall sequence on U/V/W = R30[0:2]:
     *   001 -> 101 -> 100 -> 110 -> 010 -> 011 -> 001
     * Reverse walks the same table in the opposite direction.
     */
    switch (step % 6u) {
    case 0u:
        return 0x1u;
    case 1u:
        return 0x5u;
    case 2u:
        return 0x4u;
    case 3u:
        return 0x6u;
    case 4u:
        return 0x2u;
    default:
        return 0x3u;
    }
}

static void apply_outputs(uint32_t bits)
{
    uint32_t outputs = __R30;
    outputs &= ~STIM_OUTPUT_MASK;
    outputs |= (bits & STIM_OUTPUT_MASK);
    __R30 = outputs;
}

static void apply_abz(uint32_t phase, uint32_t index_active)
{
    uint32_t bits = phase_to_ab(phase);
    if (index_active != 0u)
        bits |= ABZ_Z_MASK;
    apply_outputs(bits);
}

static void force_safe_outputs(void)
{
    __R30 &= ~STIM_OUTPUT_MASK;
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
    uint32_t *active_mode,
    uint32_t *running,
    uint32_t *start_pending_mode,
    uint32_t *armed_mode,
    uint32_t *armed_apply_ticks,
    uint32_t *last_apply_ticks,
    uint32_t *schedule_late_count,
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
    uint32_t *update_pending,
    uint32_t *update_apply_ticks,
    uint32_t *update_transition_ticks,
    uint32_t *update_direction,
    uint32_t *update_flags,
    uint32_t *hall_transition_ticks,
    uint32_t *hall_initial_step,
    uint32_t *hall_step,
    uint32_t *hall_direction,
    uint32_t *hall_transition_count,
    uint32_t *hall_next_transition_ticks,
    uint32_t *hall_late_transition_count)
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
        *active_mode = STIM_MODE_NONE;
        *start_pending_mode = STIM_MODE_NONE;
        *armed_mode = STIM_MODE_NONE;
        *update_pending = 0u;
        force_safe_outputs();
        *last_apply_ticks = now;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *transition_count;
        tx_msg.arg2 = *hall_transition_count;
        break;

    case HIL_PRU_MSG_ABZ_CONFIG: {
        uint32_t requested_direction = request->arg3 & 1u;
        uint32_t requested_phase = (request->arg3 >> 8) & 3u;

        if ((*running != 0u) || (*armed_mode != STIM_MODE_NONE) ||
            (*start_pending_mode != STIM_MODE_NONE)) {
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
        *schedule_late_count = 0u;
        *update_pending = 0u;
        force_safe_outputs();

        tx_msg.arg0 = *transition_ticks;
        tx_msg.arg1 = *index_period_transitions;
        tx_msg.arg2 = *index_width_transitions;
        tx_msg.arg3 = (*direction & 1u) | ((*initial_phase & 3u) << 8);
        break;
    }

    case HIL_PRU_MSG_ABZ_START:
        if ((*running != 0u) || (*armed_mode != STIM_MODE_NONE) ||
            (*start_pending_mode != STIM_MODE_NONE)) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        *start_pending_mode = STIM_MODE_ABZ;
        tx_msg.arg0 = now; /* arm-request timestamp; apply occurs after ACK */
        tx_msg.arg1 = phase_to_ab(*initial_phase) |
            (index_is_active(
                *index_period_transitions,
                *index_width_transitions,
                0u) ? ABZ_Z_MASK : 0u);
        tx_msg.arg2 = *transition_ticks;
        tx_msg.arg3 = *direction;
        break;

    case HIL_PRU_MSG_ABZ_ARM:
        if ((*running != 0u) || (*armed_mode != STIM_MODE_NONE) ||
            (*start_pending_mode != STIM_MODE_NONE)) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        if ((request->arg0 == 0u) || !time_is_future(now, request->arg0)) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }
        *armed_mode = STIM_MODE_ABZ;
        *armed_apply_ticks = request->arg0;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *armed_apply_ticks;
        tx_msg.arg2 = *transition_ticks;
        tx_msg.arg3 = *direction;
        break;

    case HIL_PRU_MSG_ABZ_SCHEDULE:
        if (*running != 0u) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        if (*armed_mode != STIM_MODE_ABZ) {
            tx_msg.flags = HIL_PRU_ERR_NOT_ARMED;
            break;
        }
        if (*update_pending != 0u) {
            tx_msg.flags = HIL_PRU_ERR_SCHEDULE_BUSY;
            break;
        }
        if ((request->arg0 == 0u) || !time_is_future(now, request->arg0) ||
            !time_is_future(*armed_apply_ticks, request->arg0)) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }
        if ((request->arg3 & ABZ_SCHED_TRANSITION_VALID) != 0u) {
            if ((request->arg1 < ABZ_MIN_TRANSITION_TICKS) ||
                (request->arg1 >= 0x80000000u)) {
                tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
                break;
            }
        }
        if (((request->arg3 & ABZ_SCHED_DIRECTION_VALID) != 0u) &&
            (request->arg2 > 1u)) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }

        *update_apply_ticks = request->arg0;
        *update_transition_ticks = request->arg1;
        *update_direction = request->arg2;
        *update_flags = request->arg3 &
            (ABZ_SCHED_TRANSITION_VALID | ABZ_SCHED_DIRECTION_VALID);
        *update_pending = 1u;

        tx_msg.arg0 = now;
        tx_msg.arg1 = *update_apply_ticks;
        tx_msg.arg2 = *update_transition_ticks;
        tx_msg.arg3 = *update_flags | ((*update_direction & 1u) << 8);
        break;

    case HIL_PRU_MSG_ABZ_STOP:
        *running = 0u;
        *active_mode = STIM_MODE_NONE;
        *armed_mode = STIM_MODE_NONE;
        *start_pending_mode = STIM_MODE_NONE;
        *update_pending = 0u;
        force_safe_outputs();
        *last_apply_ticks = now;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *transition_count;
        tx_msg.arg2 = *late_transition_count;
        tx_msg.arg3 = *schedule_late_count;
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
        tx_msg.arg0 = (*running != 0u && *active_mode == STIM_MODE_ABZ) ? 1u :
            ((*armed_mode == STIM_MODE_ABZ) ? 2u : 0u);
        tx_msg.arg1 = *transition_ticks;
        tx_msg.arg2 = *transition_count;
        tx_msg.arg3 = *late_transition_count;
        break;

    case HIL_PRU_MSG_HALL_CONFIG:
        if ((*running != 0u) || (*armed_mode != STIM_MODE_NONE) ||
            (*start_pending_mode != STIM_MODE_NONE)) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        if ((request->arg0 < HALL_MIN_TRANSITION_TICKS) ||
            (request->arg0 >= 0x80000000u) ||
            (request->arg1 > 1u) ||
            (request->arg2 >= 6u)) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }
        *hall_transition_ticks = request->arg0;
        *hall_direction = request->arg1;
        *hall_initial_step = request->arg2;
        *hall_step = request->arg2;
        *hall_transition_count = 0u;
        *hall_late_transition_count = 0u;
        force_safe_outputs();
        tx_msg.arg0 = *hall_transition_ticks;
        tx_msg.arg1 = *hall_direction;
        tx_msg.arg2 = *hall_initial_step;
        tx_msg.arg3 = hall_step_to_bits(*hall_initial_step);
        break;

    case HIL_PRU_MSG_HALL_START:
        if ((*running != 0u) || (*armed_mode != STIM_MODE_NONE) ||
            (*start_pending_mode != STIM_MODE_NONE)) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        *start_pending_mode = STIM_MODE_HALL;
        tx_msg.arg0 = now;
        tx_msg.arg1 = hall_step_to_bits(*hall_initial_step);
        tx_msg.arg2 = *hall_transition_ticks;
        tx_msg.arg3 = *hall_direction;
        break;

    case HIL_PRU_MSG_HALL_STOP:
        *running = 0u;
        *active_mode = STIM_MODE_NONE;
        *start_pending_mode = STIM_MODE_NONE;
        force_safe_outputs();
        *last_apply_ticks = now;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *hall_transition_count;
        tx_msg.arg2 = *hall_late_transition_count;
        break;

    case HIL_PRU_MSG_HALL_STATUS:
        tx_msg.arg0 = (*running != 0u && *active_mode == STIM_MODE_HALL) ? 1u : 0u;
        tx_msg.arg1 = *hall_transition_ticks;
        tx_msg.arg2 = *hall_transition_count;
        tx_msg.arg3 = *hall_late_transition_count;
        break;

    case HIL_PRU_MSG_STIM_STATUS:
        tx_msg.arg0 = (*running != 0u) ? STIM_STATE_RUNNING :
            ((*armed_mode != STIM_MODE_NONE) ? STIM_STATE_ARMED : STIM_STATE_IDLE);
        tx_msg.arg1 = (*running != 0u) ? *active_mode : *armed_mode;
        tx_msg.arg2 = *last_apply_ticks;
        tx_msg.arg3 = *schedule_late_count;
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

    uint32_t active_mode = STIM_MODE_NONE;
    uint32_t running = 0u;
    uint32_t start_pending_mode = STIM_MODE_NONE;
    uint32_t armed_mode = STIM_MODE_NONE;
    uint32_t armed_apply_ticks = 0u;
    uint32_t last_apply_ticks = 0u;
    uint32_t schedule_late_count = 0u;

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

    uint32_t update_pending = 0u;
    uint32_t update_apply_ticks = 0u;
    uint32_t update_transition_ticks = 0u;
    uint32_t update_direction = 0u;
    uint32_t update_flags = 0u;

    uint32_t hall_transition_ticks = HALL_DEFAULT_TRANSITION_TICKS;
    uint32_t hall_initial_step = 0u;
    uint32_t hall_step = 0u;
    uint32_t hall_direction = 0u;
    uint32_t hall_transition_count = 0u;
    uint32_t hall_next_transition_ticks = 0u;
    uint32_t hall_late_transition_count = 0u;

    CT_CFG.SYSCFG_bit.STANDBY_INIT = 0u;
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

        if ((armed_mode == STIM_MODE_ABZ) && time_due(now, armed_apply_ticks)) {
            uint32_t z_active;
            uint32_t lateness = now - armed_apply_ticks;

            phase = initial_phase;
            transition_count = 0u;
            index_phase = 0u;
            late_transition_count = 0u;
            z_active = index_is_active(
                index_period_transitions,
                index_width_transitions,
                index_phase);
            apply_abz(phase, z_active);

            if (lateness >= transition_ticks)
                schedule_late_count += 1u;

            last_apply_ticks = now;
            next_transition_ticks = now + transition_ticks;
            active_mode = STIM_MODE_ABZ;
            running = 1u;
            armed_mode = STIM_MODE_NONE;
            continue;
        }

        if ((running != 0u) && (active_mode == STIM_MODE_ABZ)) {
            if ((update_pending != 0u) &&
                time_due(now, update_apply_ticks)) {
                uint32_t lateness = now - update_apply_ticks;

                if ((update_flags & ABZ_SCHED_TRANSITION_VALID) != 0u)
                    transition_ticks = update_transition_ticks;
                if ((update_flags & ABZ_SCHED_DIRECTION_VALID) != 0u)
                    direction = update_direction;

                if (lateness >= transition_ticks)
                    schedule_late_count += 1u;

                last_apply_ticks = now;
                next_transition_ticks = now + transition_ticks;
                update_pending = 0u;
                continue;
            }

            if (time_due(now, next_transition_ticks)) {
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

                if (lateness >= transition_ticks)
                    next_transition_ticks = now + transition_ticks;
                else
                    next_transition_ticks += transition_ticks;
                continue;
            }
        }

        if ((running != 0u) && (active_mode == STIM_MODE_HALL)) {
            if (time_due(now, hall_next_transition_ticks)) {
                uint32_t lateness = now - hall_next_transition_ticks;

                if (lateness >= hall_transition_ticks)
                    hall_late_transition_count += 1u;

                if (hall_direction == 0u)
                    hall_step = (hall_step + 1u) % 6u;
                else
                    hall_step = (hall_step + 5u) % 6u;

                hall_transition_count += 1u;
                apply_outputs(hall_step_to_bits(hall_step));
                last_apply_ticks = now;

                if (lateness >= hall_transition_ticks)
                    hall_next_transition_ticks = now + hall_transition_ticks;
                else
                    hall_next_transition_ticks += hall_transition_ticks;
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
                    &active_mode,
                    &running,
                    &start_pending_mode,
                    &armed_mode,
                    &armed_apply_ticks,
                    &last_apply_ticks,
                    &schedule_late_count,
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
                    &update_pending,
                    &update_apply_ticks,
                    &update_transition_ticks,
                    &update_direction,
                    &update_flags,
                    &hall_transition_ticks,
                    &hall_initial_step,
                    &hall_step,
                    &hall_direction,
                    &hall_transition_count,
                    &hall_next_transition_ticks,
                    &hall_late_transition_count);

                pru_rpmsg_send(&transport,
                               dst,
                               src,
                               (uint8_t *)&tx_msg,
                               (uint16_t)sizeof(tx_msg));

                /*
                 * ACK-before-run boundary: only after the START response has
                 * been sent do we take a fresh IEP timestamp and establish
                 * the first real-time deadline.
                 */
                if (start_pending_mode == STIM_MODE_ABZ) {
                    uint32_t start_now = tick_now();
                    uint32_t z_active;

                    phase = initial_phase;
                    transition_count = 0u;
                    index_phase = 0u;
                    late_transition_count = 0u;
                    schedule_late_count = 0u;
                    z_active = index_is_active(
                        index_period_transitions,
                        index_width_transitions,
                        index_phase);
                    apply_abz(phase, z_active);
                    last_apply_ticks = start_now;
                    next_transition_ticks = start_now + transition_ticks;
                    active_mode = STIM_MODE_ABZ;
                    running = 1u;
                    start_pending_mode = STIM_MODE_NONE;
                } else if (start_pending_mode == STIM_MODE_HALL) {
                    uint32_t start_now = tick_now();

                    hall_step = hall_initial_step;
                    hall_transition_count = 0u;
                    hall_late_transition_count = 0u;
                    apply_outputs(hall_step_to_bits(hall_step));
                    last_apply_ticks = start_now;
                    hall_next_transition_ticks =
                        start_now + hall_transition_ticks;
                    active_mode = STIM_MODE_HALL;
                    running = 1u;
                    start_pending_mode = STIM_MODE_NONE;
                }
            }
        }
    }
}
