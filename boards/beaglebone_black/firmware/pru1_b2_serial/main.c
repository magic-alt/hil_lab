#include <stdint.h>
#include <pru_cfg.h>
#include <pru_iep.h>
#include <pru_intc.h>
#include <pru_rpmsg.h>

#include "../common/hil_pru_protocol.h"
#include "../pru1_b2/resource_table_1.h"
#include "../pru1_b2/intc_map_1.h"

volatile register uint32_t __R30;
volatile register uint32_t __R31;

#define VIRTIO_CONFIG_S_DRIVER_OK  (4u)
#define CHAN_NAME                   "rpmsg-pru"
#define CHAN_DESC                   "hil-b2-serial-pru1"
#define CHAN_PORT                   (31u)

#define HOST_INT                    ((uint32_t)1u << 31)
#define TO_ARM_HOST                 (18u)
#define FROM_ARM_HOST               (19u)

#define IEP_TICK_HZ                 (200000000u)
#define IEP_COUNTER_BITS            (32u)

#define SERIAL_MODE_NONE            (0u)
#define SERIAL_MODE_SSI             (1u)
#define SERIAL_MODE_BISS            (2u)
#define SERIAL_MODE_SPI             (3u)

#define SERIAL_CLK_MASK             (1u << 0) /* P8_45 / PRU1 R31[0] */
#define SERIAL_DATA_MASK            (1u << 1) /* P8_46 / PRU1 R30[1] */
#define SERIAL_CS_MASK              (1u << 2) /* P8_43 / PRU1 R31[2] */
#define SERIAL_MOSI_MASK            (1u << 3) /* P8_44 / PRU1 R31[3] */

#define SERIAL_FLAG_FAULT_ENABLE    (1u << 0)
#define SERIAL_FLAG_BISS_ERROR_OK   (1u << 1)
#define SERIAL_FLAG_BISS_WARNING_OK (1u << 2)

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

static void set_data_output(uint32_t value)
{
    if (value != 0u)
        __R30 |= SERIAL_DATA_MASK;
    else
        __R30 &= ~SERIAL_DATA_MASK;
}

static void force_safe_output(void)
{
    set_data_output(0u);
}

static uint32_t crc6_biss(uint32_t position, uint32_t position_bits,
                          uint32_t error_ok, uint32_t warning_ok)
{
    uint32_t crc = 0u;
    int32_t bit_index;

    for (bit_index = (int32_t)position_bits - 1; bit_index >= 0; bit_index--) {
        uint32_t bit = (position >> (uint32_t)bit_index) & 1u;
        uint32_t feedback = ((crc >> 5) & 1u) ^ bit;
        crc = (crc << 1) & 0x3fu;
        if (feedback != 0u)
            crc ^= 0x03u;
    }

    {
        uint32_t status_bits = ((error_ok & 1u) << 1) | (warning_ok & 1u);
        for (bit_index = 1; bit_index >= 0; bit_index--) {
            uint32_t bit = (status_bits >> (uint32_t)bit_index) & 1u;
            uint32_t feedback = ((crc >> 5) & 1u) ^ bit;
            crc = (crc << 1) & 0x3fu;
            if (feedback != 0u)
                crc ^= 0x03u;
        }
    }

    return (~crc) & 0x3fu;
}

static uint64_t build_frame(
    uint32_t mode,
    uint32_t data_bits,
    uint32_t data_value,
    uint32_t fault_mask,
    uint32_t data_flags,
    uint32_t *total_bits)
{
    uint32_t effective = data_value;
    uint64_t frame;

    if ((data_flags & SERIAL_FLAG_FAULT_ENABLE) != 0u)
        effective ^= fault_mask;

    if (data_bits < 32u)
        effective &= ((1u << data_bits) - 1u);

    if (mode == SERIAL_MODE_BISS) {
        uint32_t error_ok =
            ((data_flags & SERIAL_FLAG_BISS_ERROR_OK) != 0u) ? 1u : 0u;
        uint32_t warning_ok =
            ((data_flags & SERIAL_FLAG_BISS_WARNING_OK) != 0u) ? 1u : 0u;
        uint32_t crc = crc6_biss(
            effective,
            data_bits,
            error_ok,
            warning_ok);

        /* ACK=0, START=1, CDS=0, position, ERR, WARN, inverted CRC6. */
        frame = 0u;
        frame = (frame << 1);             /* ACK */
        frame = (frame << 1) | 1u;        /* START */
        frame = (frame << 1);             /* CDS */
        frame = (frame << data_bits) | effective;
        frame = (frame << 1) | error_ok;
        frame = (frame << 1) | warning_ok;
        frame = (frame << 6) | crc;
        *total_bits = data_bits + 11u;
        return frame;
    }

    *total_bits = data_bits;
    return (uint64_t)effective;
}

static uint32_t frame_bit(uint64_t frame, uint32_t total_bits, uint32_t index)
{
    uint32_t shift = total_bits - 1u - index;
    return (uint32_t)((frame >> shift) & 1u);
}

static void update_min_half_period(
    uint32_t now,
    uint32_t *last_edge_ticks,
    uint32_t *min_half_period_ticks)
{
    if (*last_edge_ticks != 0u) {
        uint32_t delta = now - *last_edge_ticks;
        if ((*min_half_period_ticks == 0u) ||
            (delta < *min_half_period_ticks))
            *min_half_period_ticks = delta;
    }
    *last_edge_ticks = now;
}

static void handle_request(
    uint16_t len,
    uint32_t *mode,
    uint32_t *configured,
    uint32_t *enabled,
    uint32_t *start_pending,
    uint32_t *data_bits,
    uint32_t *frame_gap_ticks,
    uint32_t *config_flags,
    uint32_t *data_value,
    uint32_t *fault_mask,
    uint32_t *data_flags,
    uint32_t *frame_count,
    uint32_t *protocol_error_count,
    uint32_t *min_half_period_ticks,
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
        tx_msg.arg0 = HIL_PRU_B2_SERIAL_CAPABILITIES;
        tx_msg.arg1 = IEP_TICK_HZ;
        tx_msg.arg2 = IEP_COUNTER_BITS;
        tx_msg.arg3 = HIL_PRU_B2_SERIAL_FIRMWARE_VERSION;
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
        *enabled = 0u;
        *start_pending = 0u;
        force_safe_output();
        *last_apply_ticks = now;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *frame_count;
        break;

    case HIL_PRU_MSG_SERIAL_CONFIG:
        if (*enabled != 0u) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        if ((request->arg0 < SERIAL_MODE_SSI) ||
            (request->arg0 > SERIAL_MODE_SPI)) {
            tx_msg.flags = HIL_PRU_ERR_UNSUPPORTED_MODE;
            break;
        }
        if ((request->arg1 == 0u) || (request->arg1 > 32u)) {
            tx_msg.flags = HIL_PRU_ERR_INVALID_ARGUMENT;
            break;
        }

        *mode = request->arg0;
        *data_bits = request->arg1;
        *frame_gap_ticks = request->arg2;
        *config_flags = request->arg3;
        *configured = 1u;
        *frame_count = 0u;
        *protocol_error_count = 0u;
        *min_half_period_ticks = 0u;
        force_safe_output();

        tx_msg.arg0 = *mode;
        tx_msg.arg1 = *data_bits;
        tx_msg.arg2 = *frame_gap_ticks;
        tx_msg.arg3 = *config_flags;
        break;

    case HIL_PRU_MSG_SERIAL_DATA:
        if (*enabled != 0u) {
            tx_msg.flags = HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        *data_value = request->arg0;
        *fault_mask = request->arg1;
        *data_flags = request->arg2;
        tx_msg.arg0 = *data_value;
        tx_msg.arg1 = *fault_mask;
        tx_msg.arg2 = *data_flags;
        break;

    case HIL_PRU_MSG_SERIAL_START:
        if ((*configured == 0u) || (*enabled != 0u) ||
            (*start_pending != 0u)) {
            tx_msg.flags = (*configured == 0u) ?
                HIL_PRU_ERR_INVALID_ARGUMENT :
                HIL_PRU_ERR_CAPTURE_RUNNING;
            break;
        }
        *start_pending = 1u;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *mode;
        tx_msg.arg2 = *data_bits;
        break;

    case HIL_PRU_MSG_SERIAL_STOP:
        *enabled = 0u;
        *start_pending = 0u;
        force_safe_output();
        *last_apply_ticks = now;
        tx_msg.arg0 = now;
        tx_msg.arg1 = *frame_count;
        tx_msg.arg2 = *min_half_period_ticks;
        tx_msg.arg3 = *protocol_error_count;
        break;

    case HIL_PRU_MSG_SERIAL_STATUS:
        tx_msg.arg0 = (*enabled != 0u ? 1u : 0u) | ((*mode & 0xffu) << 8);
        tx_msg.arg1 = *frame_count;
        tx_msg.arg2 = *min_half_period_ticks;
        tx_msg.arg3 = *protocol_error_count;
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

    uint32_t mode = SERIAL_MODE_NONE;
    uint32_t configured = 0u;
    uint32_t enabled = 0u;
    uint32_t start_pending = 0u;
    uint32_t data_bits = 24u;
    uint32_t frame_gap_ticks = 200u;
    uint32_t config_flags = 0u;
    uint32_t data_value = 0u;
    uint32_t fault_mask = 0u;
    uint32_t data_flags =
        SERIAL_FLAG_BISS_ERROR_OK | SERIAL_FLAG_BISS_WARNING_OK;

    uint32_t frame_count = 0u;
    uint32_t protocol_error_count = 0u;
    uint32_t min_half_period_ticks = 0u;
    uint32_t last_apply_ticks = 0u;

    uint32_t last_clk = 1u;
    uint32_t last_cs = 1u;
    uint32_t last_edge_ticks = 0u;
    uint32_t frame_active = 0u;
    uint32_t bit_index = 0u;
    uint32_t total_bits = 0u;
    uint64_t current_frame = 0u;
    uint32_t received_mosi = 0u;
    uint32_t received_bits = 0u;

    CT_CFG.SYSCFG_bit.STANDBY_INIT = 0u;
    CT_CFG.GPCFG1 = 0u;
    init_timebase_if_needed();
    force_safe_output();

    CT_INTC.SICR_bit.STS_CLR_IDX = FROM_ARM_HOST;

    driver_status = &resourceTable.rpmsg_vdev.status;
    while (((*driver_status) & VIRTIO_CONFIG_S_DRIVER_OK) == 0u) {
        force_safe_output();
    }

    if (pru_rpmsg_init(&transport,
                       &resourceTable.rpmsg_vring0,
                       &resourceTable.rpmsg_vring1,
                       TO_ARM_HOST,
                       FROM_ARM_HOST) != PRU_RPMSG_SUCCESS) {
        force_safe_output();
        while (1) {
        }
    }

    while (pru_rpmsg_channel(RPMSG_NS_CREATE,
                             &transport,
                             CHAN_NAME,
                             CHAN_DESC,
                             CHAN_PORT) != PRU_RPMSG_SUCCESS) {
        force_safe_output();
    }

    while (1) {
        uint32_t raw = __R31;
        uint32_t now = tick_now();
        uint32_t clk = (raw & SERIAL_CLK_MASK) ? 1u : 0u;
        uint32_t cs = (raw & SERIAL_CS_MASK) ? 1u : 0u;
        uint32_t mosi = (raw & SERIAL_MOSI_MASK) ? 1u : 0u;
        uint32_t clk_rise = (clk != 0u && last_clk == 0u) ? 1u : 0u;
        uint32_t clk_fall = (clk == 0u && last_clk != 0u) ? 1u : 0u;
        uint32_t cs_fall = (cs == 0u && last_cs != 0u) ? 1u : 0u;
        uint32_t cs_rise = (cs != 0u && last_cs == 0u) ? 1u : 0u;

        if (enabled != 0u) {
            if ((mode == SERIAL_MODE_SSI) || (mode == SERIAL_MODE_BISS)) {
                if (clk_rise || clk_fall)
                    update_min_half_period(
                        now,
                        &last_edge_ticks,
                        &min_half_period_ticks);

                if (clk_fall) {
                    uint32_t gap_elapsed =
                        (last_edge_ticks == now) ? 0u :
                        ((now - last_edge_ticks) >= frame_gap_ticks ? 1u : 0u);

                    /*
                     * A long clock-idle gap re-arms the next master-driven
                     * frame. On the first falling edge load bit 0; subsequent
                     * falling edges update DATA for sampling on rising edges.
                     */
                    if ((frame_active == 0u) ||
                        (gap_elapsed != 0u)) {
                        current_frame = build_frame(
                            mode,
                            data_bits,
                            data_value,
                            fault_mask,
                            data_flags,
                            &total_bits);
                        bit_index = 0u;
                        frame_active = 1u;
                        set_data_output(
                            frame_bit(current_frame, total_bits, bit_index));
                    } else if ((bit_index + 1u) < total_bits) {
                        bit_index += 1u;
                        set_data_output(
                            frame_bit(current_frame, total_bits, bit_index));
                    }
                }

                if (clk_rise && frame_active &&
                    ((bit_index + 1u) >= total_bits)) {
                    frame_count += 1u;
                    frame_active = 0u;
                    set_data_output(1u);
                }

                if (frame_active && (frame_gap_ticks != 0u) &&
                    ((now - last_edge_ticks) >= frame_gap_ticks)) {
                    frame_active = 0u;
                    set_data_output(1u);
                }
            } else if (mode == SERIAL_MODE_SPI) {
                if (cs_fall) {
                    current_frame = build_frame(
                        mode,
                        data_bits,
                        data_value,
                        fault_mask,
                        data_flags,
                        &total_bits);
                    bit_index = 0u;
                    received_mosi = 0u;
                    received_bits = 0u;
                    frame_active = 1u;
                    last_edge_ticks = now;
                    set_data_output(
                        frame_bit(current_frame, total_bits, bit_index));
                }

                if ((cs == 0u) && frame_active) {
                    if (clk_rise) {
                        update_min_half_period(
                            now,
                            &last_edge_ticks,
                            &min_half_period_ticks);
                        received_mosi =
                            (received_mosi << 1) | (mosi & 1u);
                        if (received_bits < 32u)
                            received_bits += 1u;
                    }
                    if (clk_fall) {
                        update_min_half_period(
                            now,
                            &last_edge_ticks,
                            &min_half_period_ticks);
                        if ((bit_index + 1u) < total_bits) {
                            bit_index += 1u;
                            set_data_output(frame_bit(
                                current_frame,
                                total_bits,
                                bit_index));
                        } else {
                            set_data_output(0u);
                        }
                    }
                }

                if (cs_rise && frame_active) {
                    if (received_bits != total_bits)
                        protocol_error_count += 1u;
                    frame_count += 1u;
                    frame_active = 0u;
                    set_data_output(0u);
                }
            }
        }

        last_clk = clk;
        last_cs = cs;

        if ((__R31 & HOST_INT) != 0u) {
            CT_INTC.SICR_bit.STS_CLR_IDX = FROM_ARM_HOST;

            while (pru_rpmsg_receive(&transport,
                                     &src,
                                     &dst,
                                     rx_buffer.bytes,
                                     &len) == PRU_RPMSG_SUCCESS) {
                handle_request(
                    len,
                    &mode,
                    &configured,
                    &enabled,
                    &start_pending,
                    &data_bits,
                    &frame_gap_ticks,
                    &config_flags,
                    &data_value,
                    &fault_mask,
                    &data_flags,
                    &frame_count,
                    &protocol_error_count,
                    &min_half_period_ticks,
                    &last_apply_ticks);

                pru_rpmsg_send(
                    &transport,
                    dst,
                    src,
                    (uint8_t *)&tx_msg,
                    (uint16_t)sizeof(tx_msg));

                if (start_pending != 0u) {
                    uint32_t baseline = __R31;
                    last_clk =
                        (baseline & SERIAL_CLK_MASK) ? 1u : 0u;
                    last_cs =
                        (baseline & SERIAL_CS_MASK) ? 1u : 0u;
                    last_edge_ticks = tick_now();
                    frame_active = 0u;
                    bit_index = 0u;
                    received_bits = 0u;
                    min_half_period_ticks = 0u;
                    protocol_error_count = 0u;
                    if ((mode == SERIAL_MODE_SSI) ||
                        (mode == SERIAL_MODE_BISS))
                        set_data_output(1u);
                    else
                        set_data_output(0u);
                    last_apply_ticks = last_edge_ticks;
                    enabled = 1u;
                    start_pending = 0u;
                }
            }
        }
    }
}
