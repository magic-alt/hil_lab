`default_nettype none

module hil_digital_core #(
    parameter ENCODER_COUNTS_PER_REV = 4096,
    parameter SPI_FRAME_BITS = 24,
    parameter DIO_WIDTH = 16
) (
    input  wire                         clk,
    input  wire                         rst_n,

    input  wire [2:0]                   pwm_high,
    input  wire [2:0]                   pwm_low,
    input  wire [31:0]                  min_deadtime_ticks,
    input  wire                         clear_pwm_faults,

    input  wire                         encoder_enable,
    input  wire                         encoder_direction_forward,
    input  wire [31:0]                  encoder_step_period_ticks,
    output wire                         enc_a,
    output wire                         enc_b,
    output wire                         enc_z,
    output wire [31:0]                  encoder_position_edges,

    input  wire                         spi_sclk,
    input  wire                         spi_cs_n,
    input  wire                         spi_mosi,
    input  wire [SPI_FRAME_BITS-1:0]    spi_frame_data,
    input  wire [SPI_FRAME_BITS-1:0]    spi_fault_flip_mask,
    input  wire                         spi_fault_enable,
    output wire                         spi_miso,
    output wire                         spi_frame_active,
    output wire                         spi_frame_done_pulse,

    input  wire                         dio_event_arm,
    input  wire [63:0]                  dio_event_timestamp,
    input  wire [DIO_WIDTH-1:0]         dio_event_mask,
    input  wire [DIO_WIDTH-1:0]         dio_event_value,
    input  wire [DIO_WIDTH-1:0]         dio_safe_value,
    input  wire                         dio_force_safe,
    output wire [DIO_WIDTH-1:0]         dio_out,
    output wire                         dio_event_armed,
    output wire                         dio_event_done_pulse,

    output wire [63:0]                  timestamp,
    output wire [95:0]                  pwm_period_ticks,
    output wire [95:0]                  pwm_high_ticks,
    output wire [95:0]                  pwm_low_ticks,
    output wire [2:0]                   pwm_measurement_valid,
    output wire [95:0]                  deadtime_high_to_low_ticks,
    output wire [95:0]                  deadtime_low_to_high_ticks,
    output wire [2:0]                   shoot_through_latched,
    output wire [2:0]                   deadtime_violation_latched
);

    genvar phase_index;

    hil_timebase #(
        .COUNTER_WIDTH(64)
    ) u_timebase (
        .clk       (clk),
        .rst_n     (rst_n),
        .timestamp (timestamp)
    );

    generate
        for (phase_index = 0; phase_index < 3; phase_index = phase_index + 1) begin : g_pwm
            wire [31:0] capture_period;
            wire [31:0] capture_high;
            wire [31:0] capture_low;
            wire [63:0] unused_rise_timestamp;
            wire [63:0] unused_fall_timestamp;
            wire        period_valid;
            wire        unused_high_valid;
            wire        unused_low_valid;
            wire        unused_pwm_sync;

            wire [31:0] dead_hl;
            wire [31:0] dead_lh;
            wire        unused_dead_hl_valid;
            wire        unused_dead_lh_valid;
            wire        shoot_fault;
            wire        dead_fault;

            pwm_capture u_capture (
                .clk                 (clk),
                .rst_n               (rst_n),
                .pwm_async           (pwm_high[phase_index]),
                .timestamp           (timestamp),
                .period_ticks        (capture_period),
                .high_ticks          (capture_high),
                .low_ticks           (capture_low),
                .last_rise_timestamp (unused_rise_timestamp),
                .last_fall_timestamp (unused_fall_timestamp),
                .period_valid        (period_valid),
                .high_valid          (unused_high_valid),
                .low_valid           (unused_low_valid),
                .pwm_sync            (unused_pwm_sync)
            );

            pwm_complementary_monitor u_complementary (
                .clk                         (clk),
                .rst_n                       (rst_n),
                .high_async                  (pwm_high[phase_index]),
                .low_async                   (pwm_low[phase_index]),
                .timestamp                   (timestamp),
                .min_deadtime_ticks          (min_deadtime_ticks),
                .clear_faults                (clear_pwm_faults),
                .deadtime_high_to_low_ticks  (dead_hl),
                .deadtime_low_to_high_ticks  (dead_lh),
                .deadtime_high_to_low_valid  (unused_dead_hl_valid),
                .deadtime_low_to_high_valid  (unused_dead_lh_valid),
                .shoot_through_latched       (shoot_fault),
                .deadtime_violation_latched  (dead_fault)
            );

            assign pwm_period_ticks[(phase_index+1)*32-1:phase_index*32] = capture_period;
            assign pwm_high_ticks[(phase_index+1)*32-1:phase_index*32] = capture_high;
            assign pwm_low_ticks[(phase_index+1)*32-1:phase_index*32] = capture_low;
            assign pwm_measurement_valid[phase_index] = period_valid;
            assign deadtime_high_to_low_ticks[(phase_index+1)*32-1:phase_index*32] = dead_hl;
            assign deadtime_low_to_high_ticks[(phase_index+1)*32-1:phase_index*32] = dead_lh;
            assign shoot_through_latched[phase_index] = shoot_fault;
            assign deadtime_violation_latched[phase_index] = dead_fault;
        end
    endgenerate

    abz_encoder_emulator #(
        .COUNTS_PER_REV(ENCODER_COUNTS_PER_REV)
    ) u_abz_encoder (
        .clk               (clk),
        .rst_n             (rst_n),
        .enable            (encoder_enable),
        .direction_forward (encoder_direction_forward),
        .step_period_ticks (encoder_step_period_ticks),
        .enc_a             (enc_a),
        .enc_b             (enc_b),
        .enc_z             (enc_z),
        .position_edges    (encoder_position_edges)
    );

    spi_encoder_emulator #(
        .FRAME_BITS(SPI_FRAME_BITS)
    ) u_spi_encoder (
        .clk                (clk),
        .rst_n              (rst_n),
        .spi_sclk_async     (spi_sclk),
        .spi_cs_n_async     (spi_cs_n),
        .spi_mosi_async     (spi_mosi),
        .frame_data         (spi_frame_data),
        .fault_flip_mask    (spi_fault_flip_mask),
        .fault_enable       (spi_fault_enable),
        .spi_miso           (spi_miso),
        .frame_active       (spi_frame_active),
        .frame_done_pulse   (spi_frame_done_pulse),
        .received_bit_count ()
    );

    dio_event_scheduler #(
        .WIDTH(DIO_WIDTH)
    ) u_dio_scheduler (
        .clk               (clk),
        .rst_n             (rst_n),
        .timestamp         (timestamp),
        .arm               (dio_event_arm),
        .target_timestamp  (dio_event_timestamp),
        .event_mask        (dio_event_mask),
        .event_value       (dio_event_value),
        .safe_value        (dio_safe_value),
        .force_safe        (dio_force_safe),
        .dio_out           (dio_out),
        .armed             (dio_event_armed),
        .event_done_pulse  (dio_event_done_pulse)
    );

endmodule

`default_nettype wire
