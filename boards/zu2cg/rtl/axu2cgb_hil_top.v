`default_nettype none

module axu2cgb_hil_top #(
    parameter ENCODER_COUNTS_PER_REV = 4096,
    parameter ENCODER_STEP_PERIOD_TICKS = 5000,
    parameter SPI_FRAME_BITS = 24,
    parameter [SPI_FRAME_BITS-1:0] SPI_FRAME_DATA = 24'hA55A3C,
    parameter MIN_DEADTIME_TICKS = 50,
    parameter DAC_STARTUP_DELAY_CYCLES = 1000000
) (
    input  wire                      pl_ref_clk,
    input  wire [2:0]                pwm_high_in,
    input  wire [2:0]                pwm_low_in,
    input  wire                      spi_sclk_in,
    input  wire                      spi_cs_n_in,
    input  wire                      spi_mosi_in,
    input  wire                      ext_reset_n,
    input  wire                      hil_enable_in,
    input  wire                      encoder_direction_in,
    input  wire                      clear_faults_in,
    input  wire                      force_safe_in,
    input  wire                      test_pattern_enable_in,
    input  wire [1:0]                dac_pattern_select_in,
    output wire                      enc_a_out,
    output wire                      enc_b_out,
    output wire                      enc_z_out,
    output wire                      spi_miso_out,
    output wire [15:0]               dio_out,
    output wire [3:0]                status_out,
    output wire                      dac_sclk_out,
    output wire                      dac_cs_n_out,
    output wire                      dac_mosi_a_out,
    output wire                      dac_mosi_b_out,
    output wire                      dac_reset_n_out,
    output wire                      dac_ldac_n_out,
    output wire                      dac_output_enable_out,
    output wire                      dac_initialized_out,
    output wire                      dac_stream_active_out,
    output wire [3:0]                led_n
);

    wire hil_clk;
    wire clk_locked;
    reg  [3:0] reset_release;
    wire core_rst_n;
    wire [6:0] control_sync;
    wire hil_enable;
    wire encoder_direction;
    wire clear_faults;
    wire force_safe;
    wire test_pattern_enable;
    wire [1:0] dac_pattern_select;
    wire outputs_enabled;
    wire core_enc_a;
    wire core_enc_b;
    wire core_enc_z;
    wire core_spi_miso;
    wire [15:0] core_dio_out;

    /* verilator lint_off UNUSEDSIGNAL */
    wire [63:0] timestamp;
    wire [95:0] pwm_period_ticks;
    wire [95:0] pwm_high_ticks;
    wire [95:0] pwm_low_ticks;
    wire [2:0]  pwm_measurement_valid;
    wire [95:0] deadtime_high_to_low_ticks;
    wire [95:0] deadtime_low_to_high_ticks;
    wire [2:0]  shoot_through_latched;
    wire [2:0]  deadtime_violation_latched;
    wire [31:0] encoder_position_edges;
    wire        spi_frame_active;
    wire        spi_frame_done_pulse;
    wire [15:0] spi_received_bit_count;
    wire [SPI_FRAME_BITS-1:0] spi_received_mosi_data;
    wire        dio_event_armed;
    wire        dio_event_done_pulse;
    wire        dac_sample_accepted_pulse;
    wire        dac_sample_update_pulse;
    /* verilator lint_on UNUSEDSIGNAL */

    wire [15:0] dac_ch0_code;
    wire [15:0] dac_ch1_code;
    wire [15:0] dac_ch2_code;
    wire [15:0] dac_ch3_code;
    wire        dac_sample_ready;
    wire        dac_sample_valid;
    wire        dac_initialized;
    wire        dac_stream_active;
    reg         dac_submit_pending;
    reg  [1:0]  dac_pattern_seen;
    reg         outputs_enabled_d;
    reg         pwm_seen_latched;
    wire        fault_summary;

    axu2cgb_clock_gen u_clock_gen (
        .pl_ref_clk(pl_ref_clk), .reset_n(ext_reset_n),
        .hil_clk(hil_clk), .locked(clk_locked)
    );

    always @(posedge hil_clk or negedge ext_reset_n) begin
        if (!ext_reset_n)
            reset_release <= 4'b0000;
        else if (!clk_locked)
            reset_release <= 4'b0000;
        else
            reset_release <= {reset_release[2:0], 1'b1};
    end
    assign core_rst_n = reset_release[3];

    sync_2ff #(.WIDTH(7)) u_control_sync (
        .clk(hil_clk), .rst_n(core_rst_n),
        .async_in({dac_pattern_select_in, test_pattern_enable_in,
                   force_safe_in, clear_faults_in,
                   encoder_direction_in, hil_enable_in}),
        .sync_out(control_sync)
    );

    assign hil_enable          = control_sync[0];
    assign encoder_direction   = control_sync[1];
    assign clear_faults        = control_sync[2];
    assign force_safe          = control_sync[3];
    assign test_pattern_enable = control_sync[4];
    assign dac_pattern_select  = control_sync[6:5];
    assign outputs_enabled     = hil_enable & ~force_safe;

    hil_digital_core #(
        .ENCODER_COUNTS_PER_REV(ENCODER_COUNTS_PER_REV),
        .SPI_FRAME_BITS(SPI_FRAME_BITS), .DIO_WIDTH(16)
    ) u_hil_core (
        .clk(hil_clk), .rst_n(core_rst_n),
        .pwm_high(pwm_high_in), .pwm_low(pwm_low_in),
        .min_deadtime_ticks(MIN_DEADTIME_TICKS),
        .clear_pwm_faults(clear_faults),
        .encoder_enable(outputs_enabled),
        .encoder_direction_forward(encoder_direction),
        .encoder_step_period_ticks(ENCODER_STEP_PERIOD_TICKS),
        .enc_a(core_enc_a), .enc_b(core_enc_b), .enc_z(core_enc_z),
        .encoder_position_edges(encoder_position_edges),
        .spi_sclk(spi_sclk_in), .spi_cs_n(spi_cs_n_in), .spi_mosi(spi_mosi_in),
        .spi_frame_data(SPI_FRAME_DATA),
        .spi_fault_flip_mask({SPI_FRAME_BITS{1'b0}}), .spi_fault_enable(1'b0),
        .spi_miso(core_spi_miso), .spi_frame_active(spi_frame_active),
        .spi_frame_done_pulse(spi_frame_done_pulse),
        .spi_received_bit_count(spi_received_bit_count),
        .spi_received_mosi_data(spi_received_mosi_data),
        .dio_event_arm(1'b0), .dio_event_timestamp(64'd0),
        .dio_event_mask(16'd0), .dio_event_value(16'd0),
        .dio_safe_value(16'd0), .dio_force_safe(~outputs_enabled),
        .dio_out(core_dio_out), .dio_event_armed(dio_event_armed),
        .dio_event_done_pulse(dio_event_done_pulse),
        .timestamp(timestamp), .pwm_period_ticks(pwm_period_ticks),
        .pwm_high_ticks(pwm_high_ticks), .pwm_low_ticks(pwm_low_ticks),
        .pwm_measurement_valid(pwm_measurement_valid),
        .deadtime_high_to_low_ticks(deadtime_high_to_low_ticks),
        .deadtime_low_to_high_ticks(deadtime_low_to_high_ticks),
        .shoot_through_latched(shoot_through_latched),
        .deadtime_violation_latched(deadtime_violation_latched)
    );

    dac_eval_pattern_generator u_dac_pattern (
        .pattern_select(dac_pattern_select),
        .ch0_code(dac_ch0_code), .ch1_code(dac_ch1_code),
        .ch2_code(dac_ch2_code), .ch3_code(dac_ch3_code)
    );

    assign dac_sample_valid = dac_submit_pending & outputs_enabled;

    always @(posedge hil_clk or negedge core_rst_n) begin
        if (!core_rst_n) begin
            dac_submit_pending <= 1'b1;
            dac_pattern_seen   <= 2'b00;
            outputs_enabled_d  <= 1'b0;
        end else begin
            outputs_enabled_d <= outputs_enabled;
            if (!outputs_enabled)
                dac_submit_pending <= 1'b1;
            if (dac_pattern_select != dac_pattern_seen) begin
                dac_pattern_seen <= dac_pattern_select;
                dac_submit_pending <= 1'b1;
            end
            if (outputs_enabled && !outputs_enabled_d)
                dac_submit_pending <= 1'b1;
            if (dac_sample_valid && dac_sample_ready)
                dac_submit_pending <= 1'b0;
        end
    end

    ad3542r_quad_stream #(
        .STARTUP_DELAY_CYCLES(DAC_STARTUP_DELAY_CYCLES),
        .OUTPUT_RANGE_CONFIG(8'h11), .SAFE_CODE(16'h0000)
    ) u_dac_stream (
        .clk(hil_clk), .rst_n(core_rst_n), .enable(hil_enable),
        .force_safe(force_safe),
        .ch0_code(dac_ch0_code), .ch1_code(dac_ch1_code),
        .ch2_code(dac_ch2_code), .ch3_code(dac_ch3_code),
        .sample_valid(dac_sample_valid), .sample_ready(dac_sample_ready),
        .sample_accepted_pulse(dac_sample_accepted_pulse),
        .sample_update_pulse(dac_sample_update_pulse),
        .dac_sclk(dac_sclk_out), .dac_cs_n(dac_cs_n_out),
        .dac_sdio0_a(dac_mosi_a_out), .dac_sdio0_b(dac_mosi_b_out),
        .dac_reset_n(dac_reset_n_out), .dac_ldac_n(dac_ldac_n_out),
        .dac_output_enable(dac_output_enable_out),
        .initialized(dac_initialized), .stream_active(dac_stream_active)
    );

    assign dac_initialized_out   = dac_initialized;
    assign dac_stream_active_out = dac_stream_active;

    always @(posedge hil_clk or negedge core_rst_n) begin
        if (!core_rst_n)
            pwm_seen_latched <= 1'b0;
        else if (clear_faults)
            pwm_seen_latched <= 1'b0;
        else if (|pwm_measurement_valid)
            pwm_seen_latched <= 1'b1;
    end

    assign fault_summary = (|shoot_through_latched) |
                           (|deadtime_violation_latched);
    assign enc_a_out    = outputs_enabled ? core_enc_a : 1'b0;
    assign enc_b_out    = outputs_enabled ? core_enc_b : 1'b0;
    assign enc_z_out    = outputs_enabled ? core_enc_z : 1'b0;
    assign spi_miso_out = outputs_enabled ? core_spi_miso : 1'b0;
    assign dio_out = (outputs_enabled && test_pattern_enable) ?
                     16'hA55A : core_dio_out;
    assign status_out[0] = clk_locked;
    assign status_out[1] = core_rst_n;
    assign status_out[2] = pwm_seen_latched;
    assign status_out[3] = fault_summary;
    assign led_n[0] = ~clk_locked;
    assign led_n[1] = ~pwm_seen_latched;
    assign led_n[2] = ~(|shoot_through_latched);
    assign led_n[3] = ~(|deadtime_violation_latched);

endmodule

`default_nettype wire
