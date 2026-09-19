`default_nettype none

module pmsm_closed_loop_hil_q16 (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    clear_faults,
    input  wire                    model_update,

    input  wire [95:0]             pwm_period_ticks,
    input  wire [95:0]             pwm_high_ticks,
    input  wire [2:0]              pwm_valid,
    input  wire signed [31:0]      vbus_q16,
    input  wire signed [31:0]      load_torque_q16,
    input  wire [15:0]             pole_pairs,

    input  wire signed [31:0]      k_vd_q16,
    input  wire signed [31:0]      k_vq_q16,
    input  wire signed [31:0]      k_r_d_q16,
    input  wire signed [31:0]      k_r_q_q16,
    input  wire signed [31:0]      k_cross_d_q16,
    input  wire signed [31:0]      k_cross_q_q16,
    input  wire signed [31:0]      k_flux_q16,
    input  wire signed [31:0]      k_torque_q16,
    input  wire signed [31:0]      k_accel_q16,
    input  wire signed [31:0]      k_damp_q16,
    input  wire signed [31:0]      k_theta_q16,
    input  wire signed [31:0]      k_rad_to_turn_q32,

    input  wire signed [31:0]      current_gain_q16,
    input  wire [15:0]             current_offset_code,
    input  wire signed [31:0]      vbus_gain_q16,
    input  wire [15:0]             vbus_offset_code,
    input  wire signed [31:0]      current_limit_q16,
    input  wire signed [31:0]      speed_limit_q16,

    output wire [95:0]             duty_q16,
    output wire signed [31:0]      vd_q16,
    output wire signed [31:0]      vq_q16,
    output wire signed [31:0]      id_q16,
    output wire signed [31:0]      iq_q16,
    output wire signed [31:0]      torque_q16,
    output wire signed [31:0]      omega_m_q16,
    output wire signed [31:0]      omega_e_q16,
    output wire signed [31:0]      ia_q16,
    output wire signed [31:0]      ib_q16,
    output wire signed [31:0]      ic_q16,
    output wire [31:0]             electrical_phase_q32,
    output wire [31:0]             mechanical_phase_q32,
    output wire [23:0]             encoder_word24,
    output wire [15:0]             dac_ia_code,
    output wire [15:0]             dac_ib_code,
    output wire [15:0]             dac_ic_code,
    output wire [15:0]             dac_vbus_code,
    output reg                     state_limit_latched
);

    wire [31:0] duty_u_q16;
    wire [31:0] duty_v_q16;
    wire [31:0] duty_w_q16;
    wire signed [31:0] vu_q16;
    wire signed [31:0] vv_q16;
    wire signed [31:0] vw_q16;
    wire signed [31:0] common_mode_q16;
    wire signed [31:0] v_alpha_q16;
    wire signed [31:0] v_beta_q16;
    wire signed [31:0] sin_e_q16;
    wire signed [31:0] cos_e_q16;
    wire signed [31:0] i_alpha_q16;
    wire signed [31:0] i_beta_q16;
    wire signed [31:0] theta_compat_q16;

    function signed [31:0] abs_q16;
        input signed [31:0] value;
        begin
            if (value[31])
                abs_q16 = -value;
            else
                abs_q16 = value;
        end
    endfunction

    pwm_ticks_to_duty_q16 u_duty_u (
        .period_ticks(pwm_period_ticks[31:0]),
        .high_ticks(pwm_high_ticks[31:0]),
        .valid(pwm_valid[0]), .duty_q16(duty_u_q16)
    );
    pwm_ticks_to_duty_q16 u_duty_v (
        .period_ticks(pwm_period_ticks[63:32]),
        .high_ticks(pwm_high_ticks[63:32]),
        .valid(pwm_valid[1]), .duty_q16(duty_v_q16)
    );
    pwm_ticks_to_duty_q16 u_duty_w (
        .period_ticks(pwm_period_ticks[95:64]),
        .high_ticks(pwm_high_ticks[95:64]),
        .valid(pwm_valid[2]), .duty_q16(duty_w_q16)
    );
    assign duty_q16 = {duty_w_q16, duty_v_q16, duty_u_q16};

    averaged_inverter_abc_q16 u_inverter (
        .duty_u_q16(duty_u_q16), .duty_v_q16(duty_v_q16),
        .duty_w_q16(duty_w_q16), .vbus_q16(vbus_q16),
        .phase_u_q16(vu_q16), .phase_v_q16(vv_q16),
        .phase_w_q16(vw_q16), .common_mode_q16(common_mode_q16)
    );

    phase_accumulator_q32 u_electrical_phase (
        .clk(clk), .rst_n(rst_n), .clear(clear_faults),
        .update_en(model_update), .omega_rad_s_q16(omega_e_q16),
        .k_rad_to_turn_q32(k_rad_to_turn_q32),
        .phase_turn_q32(electrical_phase_q32)
    );

    phase_accumulator_q32 u_mechanical_phase (
        .clk(clk), .rst_n(rst_n), .clear(clear_faults),
        .update_en(model_update), .omega_rad_s_q16(omega_m_q16),
        .k_rad_to_turn_q32(k_rad_to_turn_q32),
        .phase_turn_q32(mechanical_phase_q32)
    );

    sincos_lut_q16 u_sincos (
        .phase_turn_q32(electrical_phase_q32),
        .sin_q16(sin_e_q16), .cos_q16(cos_e_q16)
    );

    clarke_abc_q16 u_v_clarke (
        .a_q16(vu_q16), .b_q16(vv_q16), .c_q16(vw_q16),
        .alpha_q16(v_alpha_q16), .beta_q16(v_beta_q16)
    );

    park_alphabeta_q16 u_v_park (
        .alpha_q16(v_alpha_q16), .beta_q16(v_beta_q16),
        .sin_q16(sin_e_q16), .cos_q16(cos_e_q16),
        .d_q16(vd_q16), .q_q16(vq_q16)
    );

    pmsm_dq_plant_q16 u_plant (
        .clk(clk), .rst_n(rst_n), .update_en(model_update),
        .vd_q16(vd_q16), .vq_q16(vq_q16),
        .load_torque_q16(load_torque_q16), .pole_pairs(pole_pairs),
        .k_vd_q16(k_vd_q16), .k_vq_q16(k_vq_q16),
        .k_r_d_q16(k_r_d_q16), .k_r_q_q16(k_r_q_q16),
        .k_cross_d_q16(k_cross_d_q16), .k_cross_q_q16(k_cross_q_q16),
        .k_flux_q16(k_flux_q16), .k_torque_q16(k_torque_q16),
        .k_accel_q16(k_accel_q16), .k_damp_q16(k_damp_q16),
        .k_theta_q16(k_theta_q16),
        .id_q16(id_q16), .iq_q16(iq_q16), .torque_q16(torque_q16),
        .omega_m_q16(omega_m_q16), .theta_m_q16(theta_compat_q16),
        .omega_e_q16(omega_e_q16)
    );

    inverse_park_q16 u_i_invpark (
        .d_q16(id_q16), .q_q16(iq_q16),
        .sin_q16(sin_e_q16), .cos_q16(cos_e_q16),
        .alpha_q16(i_alpha_q16), .beta_q16(i_beta_q16)
    );

    inverse_clarke_q16 u_i_invclarke (
        .alpha_q16(i_alpha_q16), .beta_q16(i_beta_q16),
        .a_q16(ia_q16), .b_q16(ib_q16), .c_q16(ic_q16)
    );

    assign encoder_word24 = {mechanical_phase_q32[31:16], 8'd0};

    q16_to_dac_code u_dac_ia (
        .signal_q16(ia_q16), .gain_codes_per_unit_q16(current_gain_q16),
        .offset_code(current_offset_code), .dac_code(dac_ia_code)
    );
    q16_to_dac_code u_dac_ib (
        .signal_q16(ib_q16), .gain_codes_per_unit_q16(current_gain_q16),
        .offset_code(current_offset_code), .dac_code(dac_ib_code)
    );
    q16_to_dac_code u_dac_ic (
        .signal_q16(ic_q16), .gain_codes_per_unit_q16(current_gain_q16),
        .offset_code(current_offset_code), .dac_code(dac_ic_code)
    );
    q16_to_dac_code u_dac_vbus (
        .signal_q16(vbus_q16), .gain_codes_per_unit_q16(vbus_gain_q16),
        .offset_code(vbus_offset_code), .dac_code(dac_vbus_code)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state_limit_latched <= 1'b0;
        else if (clear_faults)
            state_limit_latched <= 1'b0;
        else if (model_update) begin
            if ((abs_q16(id_q16) > current_limit_q16) ||
                (abs_q16(iq_q16) > current_limit_q16) ||
                (abs_q16(omega_m_q16) > speed_limit_q16))
                state_limit_latched <= 1'b1;
        end
    end

endmodule

`default_nettype wire
