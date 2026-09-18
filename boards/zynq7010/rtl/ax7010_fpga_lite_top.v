`default_nettype none

module ax7010_fpga_lite_top #(
    parameter PWM_PERIOD_TICKS = 5000,
    parameter PWM_U_HIGH_TICKS = 2500,
    parameter PWM_V_HIGH_TICKS = 1667,
    parameter PWM_W_HIGH_TICKS = 3333,
    parameter PWM_DEADTIME_TICKS = 80,
    parameter ENCODER_COUNTS_PER_REV = 4096,
    parameter ENCODER_STEP_PERIOD_TICKS = 1000,
    parameter SSI_DATA_BITS = 24,
    parameter [SSI_DATA_BITS-1:0] SSI_FRAME_DATA = 24'hA55A3C
) (
    input  wire                     pl_clk_50m,
    input  wire                     ext_reset_n,
    input  wire                     hil_enable_in,
    input  wire                     force_safe_in,
    input  wire                     clear_faults_in,
    input  wire                     encoder_direction_in,
    input  wire                     ssi_master_start_in,

    input  wire [2:0]               dut_pwm_high_in,
    input  wire [2:0]               dut_pwm_low_in,
    input  wire                     dut_enc_a_in,
    input  wire                     dut_enc_b_in,
    input  wire                     dut_enc_z_in,
    input  wire                     dut_ssi_clk_in,
    input  wire                     dut_ssi_data_in,

    output wire [2:0]               stim_pwm_high_out,
    output wire [2:0]               stim_pwm_low_out,
    output wire                     stim_enc_a_out,
    output wire                     stim_enc_b_out,
    output wire                     stim_enc_z_out,
    output wire                     stim_ssi_clk_out,
    output wire                     stim_ssi_data_out,
    output wire                     fault_out,
    output wire [3:0]               status_out,
    output wire [3:0]               led_n
);

    wire hil_clk;
    wire clk_locked;
    reg  [3:0] reset_release;
    wire core_rst_n;

    wire [4:0] control_sync;
    wire hil_enable;
    wire force_safe;
    wire clear_faults;
    wire encoder_direction;
    wire ssi_master_start_sync;
    reg  ssi_master_start_d;
    wire ssi_master_start_pulse;
    wire outputs_enabled;

    wire [63:0] timestamp;

    wire [2:0] gen_pwm_high;
    wire [2:0] gen_pwm_low;

    wire [31:0] pwm_period_u;
    wire [31:0] pwm_period_v;
    wire [31:0] pwm_period_w;
    wire [31:0] pwm_high_u;
    wire [31:0] pwm_high_v;
    wire [31:0] pwm_high_w;
    wire [31:0] pwm_low_u;
    wire [31:0] pwm_low_v;
    wire [31:0] pwm_low_w;
    wire pwm_valid_u;
    wire pwm_valid_v;
    wire pwm_valid_w;

    wire [31:0] dead_hl_u;
    wire [31:0] dead_hl_v;
    wire [31:0] dead_hl_w;
    wire [31:0] dead_lh_u;
    wire [31:0] dead_lh_v;
    wire [31:0] dead_lh_w;
    wire dead_hl_valid_u;
    wire dead_hl_valid_v;
    wire dead_hl_valid_w;
    wire dead_lh_valid_u;
    wire dead_lh_valid_v;
    wire dead_lh_valid_w;
    wire shoot_u;
    wire shoot_v;
    wire shoot_w;
    wire dead_fault_u;
    wire dead_fault_v;
    wire dead_fault_w;

    wire core_enc_a;
    wire core_enc_b;
    wire core_enc_z;
    wire [31:0] gen_encoder_position;

    wire [31:0] captured_encoder_position;
    wire captured_encoder_direction;
    wire captured_encoder_step;
    wire captured_index_pulse;
    wire encoder_illegal_fault;
    wire [63:0] encoder_last_edge_timestamp;

    wire ssi_emulator_data;
    wire ssi_emulator_active;
    wire [15:0] ssi_emulator_bit_count;
    wire ssi_emulator_done;

    wire ssi_master_clk;
    wire [SSI_DATA_BITS-1:0] ssi_captured_data;
    wire ssi_master_busy;
    wire ssi_master_done;
    wire [15:0] ssi_master_bit_count;

    reg pwm_seen_latched;
    reg ssi_seen_latched;
    wire fault_summary;

    ax7010_clock_gen u_clock_gen (
        .pl_clk_50m(pl_clk_50m),
        .reset_n(ext_reset_n),
        .hil_clk(hil_clk),
        .locked(clk_locked)
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

    sync_2ff #(.WIDTH(5)) u_control_sync (
        .clk(hil_clk),
        .rst_n(core_rst_n),
        .async_in({
            ssi_master_start_in,
            encoder_direction_in,
            clear_faults_in,
            force_safe_in,
            hil_enable_in
        }),
        .sync_out(control_sync)
    );

    assign hil_enable           = control_sync[0];
    assign force_safe           = control_sync[1];
    assign clear_faults         = control_sync[2];
    assign encoder_direction    = control_sync[3];
    assign ssi_master_start_sync = control_sync[4];
    assign outputs_enabled      = hil_enable & ~force_safe;

    always @(posedge hil_clk or negedge core_rst_n) begin
        if (!core_rst_n)
            ssi_master_start_d <= 1'b0;
        else
            ssi_master_start_d <= ssi_master_start_sync;
    end

    assign ssi_master_start_pulse =
        ssi_master_start_sync & ~ssi_master_start_d;

    hil_timebase u_timebase (
        .clk(hil_clk),
        .rst_n(core_rst_n),
        .timestamp(timestamp)
    );

    pwm_complementary_generator u_pwm_gen_u (
        .clk(hil_clk), .rst_n(core_rst_n), .enable(outputs_enabled),
        .period_ticks(PWM_PERIOD_TICKS),
        .high_ticks(PWM_U_HIGH_TICKS),
        .deadtime_ticks(PWM_DEADTIME_TICKS),
        .pwm_high(gen_pwm_high[0]), .pwm_low(gen_pwm_low[0]),
        .cycle_pulse()
    );

    pwm_complementary_generator u_pwm_gen_v (
        .clk(hil_clk), .rst_n(core_rst_n), .enable(outputs_enabled),
        .period_ticks(PWM_PERIOD_TICKS),
        .high_ticks(PWM_V_HIGH_TICKS),
        .deadtime_ticks(PWM_DEADTIME_TICKS),
        .pwm_high(gen_pwm_high[1]), .pwm_low(gen_pwm_low[1]),
        .cycle_pulse()
    );

    pwm_complementary_generator u_pwm_gen_w (
        .clk(hil_clk), .rst_n(core_rst_n), .enable(outputs_enabled),
        .period_ticks(PWM_PERIOD_TICKS),
        .high_ticks(PWM_W_HIGH_TICKS),
        .deadtime_ticks(PWM_DEADTIME_TICKS),
        .pwm_high(gen_pwm_high[2]), .pwm_low(gen_pwm_low[2]),
        .cycle_pulse()
    );

    pwm_capture u_pwm_cap_u (
        .clk(hil_clk), .rst_n(core_rst_n),
        .pwm_async(dut_pwm_high_in[0]), .timestamp(timestamp),
        .period_ticks(pwm_period_u), .high_ticks(pwm_high_u),
        .low_ticks(pwm_low_u), .last_rise_timestamp(),
        .last_fall_timestamp(), .period_valid(pwm_valid_u),
        .high_valid(), .low_valid(), .pwm_sync()
    );

    pwm_capture u_pwm_cap_v (
        .clk(hil_clk), .rst_n(core_rst_n),
        .pwm_async(dut_pwm_high_in[1]), .timestamp(timestamp),
        .period_ticks(pwm_period_v), .high_ticks(pwm_high_v),
        .low_ticks(pwm_low_v), .last_rise_timestamp(),
        .last_fall_timestamp(), .period_valid(pwm_valid_v),
        .high_valid(), .low_valid(), .pwm_sync()
    );

    pwm_capture u_pwm_cap_w (
        .clk(hil_clk), .rst_n(core_rst_n),
        .pwm_async(dut_pwm_high_in[2]), .timestamp(timestamp),
        .period_ticks(pwm_period_w), .high_ticks(pwm_high_w),
        .low_ticks(pwm_low_w), .last_rise_timestamp(),
        .last_fall_timestamp(), .period_valid(pwm_valid_w),
        .high_valid(), .low_valid(), .pwm_sync()
    );

    pwm_complementary_monitor u_deadtime_u (
        .clk(hil_clk), .rst_n(core_rst_n),
        .high_async(dut_pwm_high_in[0]), .low_async(dut_pwm_low_in[0]),
        .timestamp(timestamp), .min_deadtime_ticks(PWM_DEADTIME_TICKS),
        .clear_faults(clear_faults),
        .deadtime_high_to_low_ticks(dead_hl_u),
        .deadtime_low_to_high_ticks(dead_lh_u),
        .deadtime_high_to_low_valid(dead_hl_valid_u),
        .deadtime_low_to_high_valid(dead_lh_valid_u),
        .shoot_through_latched(shoot_u),
        .deadtime_violation_latched(dead_fault_u)
    );

    pwm_complementary_monitor u_deadtime_v (
        .clk(hil_clk), .rst_n(core_rst_n),
        .high_async(dut_pwm_high_in[1]), .low_async(dut_pwm_low_in[1]),
        .timestamp(timestamp), .min_deadtime_ticks(PWM_DEADTIME_TICKS),
        .clear_faults(clear_faults),
        .deadtime_high_to_low_ticks(dead_hl_v),
        .deadtime_low_to_high_ticks(dead_lh_v),
        .deadtime_high_to_low_valid(dead_hl_valid_v),
        .deadtime_low_to_high_valid(dead_lh_valid_v),
        .shoot_through_latched(shoot_v),
        .deadtime_violation_latched(dead_fault_v)
    );

    pwm_complementary_monitor u_deadtime_w (
        .clk(hil_clk), .rst_n(core_rst_n),
        .high_async(dut_pwm_high_in[2]), .low_async(dut_pwm_low_in[2]),
        .timestamp(timestamp), .min_deadtime_ticks(PWM_DEADTIME_TICKS),
        .clear_faults(clear_faults),
        .deadtime_high_to_low_ticks(dead_hl_w),
        .deadtime_low_to_high_ticks(dead_lh_w),
        .deadtime_high_to_low_valid(dead_hl_valid_w),
        .deadtime_low_to_high_valid(dead_lh_valid_w),
        .shoot_through_latched(shoot_w),
        .deadtime_violation_latched(dead_fault_w)
    );

    abz_encoder_emulator #(
        .COUNTS_PER_REV(ENCODER_COUNTS_PER_REV)
    ) u_abz_generator (
        .clk(hil_clk),
        .rst_n(core_rst_n),
        .enable(outputs_enabled),
        .direction_forward(encoder_direction),
        .step_period_ticks(ENCODER_STEP_PERIOD_TICKS),
        .enc_a(core_enc_a),
        .enc_b(core_enc_b),
        .enc_z(core_enc_z),
        .position_edges(gen_encoder_position)
    );

    abz_encoder_capture u_abz_capture (
        .clk(hil_clk),
        .rst_n(core_rst_n),
        .enc_a_async(dut_enc_a_in),
        .enc_b_async(dut_enc_b_in),
        .enc_z_async(dut_enc_z_in),
        .timestamp(timestamp),
        .clear_faults(clear_faults),
        .position_edges(captured_encoder_position),
        .direction_forward(captured_encoder_direction),
        .step_pulse(captured_encoder_step),
        .index_pulse(captured_index_pulse),
        .illegal_transition_latched(encoder_illegal_fault),
        .last_edge_timestamp(encoder_last_edge_timestamp)
    );

    ssi_encoder_emulator #(
        .DATA_BITS(SSI_DATA_BITS)
    ) u_ssi_emulator (
        .clk(hil_clk),
        .rst_n(core_rst_n),
        .enable(outputs_enabled),
        .ssi_clk_async(dut_ssi_clk_in),
        .frame_data(SSI_FRAME_DATA),
        .frame_gap_ticks(32'd200),
        .fault_flip_mask({SSI_DATA_BITS{1'b0}}),
        .fault_enable(1'b0),
        .ssi_data(ssi_emulator_data),
        .frame_active(ssi_emulator_active),
        .bit_count(ssi_emulator_bit_count),
        .frame_done_pulse(ssi_emulator_done)
    );

    ssi_encoder_master_capture #(
        .DATA_BITS(SSI_DATA_BITS)
    ) u_ssi_master (
        .clk(hil_clk),
        .rst_n(core_rst_n),
        .start(ssi_master_start_pulse & outputs_enabled),
        .half_period_ticks(32'd50),
        .ssi_data_async(dut_ssi_data_in),
        .ssi_clk(ssi_master_clk),
        .captured_data(ssi_captured_data),
        .busy(ssi_master_busy),
        .done_pulse(ssi_master_done),
        .bit_count(ssi_master_bit_count)
    );

    always @(posedge hil_clk or negedge core_rst_n) begin
        if (!core_rst_n) begin
            pwm_seen_latched <= 1'b0;
            ssi_seen_latched <= 1'b0;
        end else begin
            if (clear_faults) begin
                pwm_seen_latched <= 1'b0;
                ssi_seen_latched <= 1'b0;
            end else begin
                if (pwm_valid_u || pwm_valid_v || pwm_valid_w)
                    pwm_seen_latched <= 1'b1;
                if (ssi_emulator_done || ssi_master_done)
                    ssi_seen_latched <= 1'b1;
            end
        end
    end

    assign fault_summary =
        shoot_u | shoot_v | shoot_w |
        dead_fault_u | dead_fault_v | dead_fault_w |
        encoder_illegal_fault;

    assign stim_pwm_high_out = outputs_enabled ? gen_pwm_high : 3'b000;
    assign stim_pwm_low_out  = outputs_enabled ? gen_pwm_low  : 3'b000;
    assign stim_enc_a_out    = outputs_enabled ? core_enc_a : 1'b0;
    assign stim_enc_b_out    = outputs_enabled ? core_enc_b : 1'b0;
    assign stim_enc_z_out    = outputs_enabled ? core_enc_z : 1'b0;
    assign stim_ssi_clk_out  = outputs_enabled ? ssi_master_clk : 1'b1;
    assign stim_ssi_data_out = outputs_enabled ? ssi_emulator_data : 1'b1;
    assign fault_out         = outputs_enabled ? fault_summary : 1'b0;

    assign status_out[0] = clk_locked;
    assign status_out[1] = pwm_seen_latched;
    assign status_out[2] = ssi_seen_latched;
    assign status_out[3] = fault_summary;

    assign led_n[0] = ~clk_locked;
    assign led_n[1] = ~pwm_seen_latched;
    assign led_n[2] = ~ssi_seen_latched;
    assign led_n[3] = ~fault_summary;

endmodule

`default_nettype wire
