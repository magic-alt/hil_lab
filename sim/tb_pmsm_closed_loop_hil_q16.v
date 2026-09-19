`timescale 1ns/1ps
`default_nettype none

module tb_pmsm_closed_loop_hil_q16;
    reg clk;
    reg rst_n;
    reg clear_faults;
    reg update;
    wire signed [31:0] iq;
    wire signed [31:0] torque;
    wire signed [31:0] omega;
    wire signed [31:0] ia;
    wire [23:0] encoder;
    wire [15:0] dac_ia;
    wire limit_fault;

    pmsm_closed_loop_hil_q16 dut (
        .clk(clk),.rst_n(rst_n),.clear_faults(clear_faults),.model_update(update),
        .pwm_period_ticks({32'd5000,32'd5000,32'd5000}),
        .pwm_high_ticks({32'd1250,32'd3750,32'd2500}),
        .pwm_valid(3'b111),
        .vbus_q16(32'sd3145728),.load_torque_q16(32'sd0),.pole_pairs(16'd10),
        .k_vd_q16(32'sd655),.k_vq_q16(32'sd655),
        .k_r_d_q16(32'sd65),.k_r_q_q16(32'sd65),
        .k_cross_d_q16(32'sd0),.k_cross_q_q16(32'sd0),
        .k_flux_q16(32'sd0),.k_torque_q16(32'sd6160),
        .k_accel_q16(32'sd3277),.k_damp_q16(32'sd7),
        .k_theta_q16(32'sd1),.k_rad_to_turn_q32(32'sd34178),
        .current_gain_q16(32'sd6553600),.current_offset_code(16'd32768),
        .vbus_gain_q16(32'sd65536),.vbus_offset_code(16'd0),
        .current_limit_q16(32'sd1310720),.speed_limit_q16(32'sd13107200),
        .duty_q16(),.vd_q16(),.vq_q16(),.id_q16(),.iq_q16(iq),
        .torque_q16(torque),.omega_m_q16(omega),.omega_e_q16(),
        .ia_q16(ia),.ib_q16(),.ic_q16(),.electrical_phase_q32(),
        .mechanical_phase_q32(),.encoder_word24(encoder),
        .dac_ia_code(dac_ia),.dac_ib_code(),.dac_ic_code(),.dac_vbus_code(),
        .state_limit_latched(limit_fault)
    );

    always #5 clk=~clk;

    initial begin
        clk=0; rst_n=0; clear_faults=0; update=0;
        repeat(5) @(posedge clk); rst_n=1;
        repeat(80) begin
            @(negedge clk); update=1;
            @(negedge clk); update=0;
        end
        if(iq<=0 || torque<=0 || omega<=0) begin
            $display("FAIL: closed-loop plant did not accelerate iq=%0d tq=%0d w=%0d",iq,torque,omega);
            $fatal(1);
        end
        if(dac_ia==16'd32768) begin
            $display("FAIL: current DAC feedback did not move");
            $fatal(1);
        end
        if(encoder==24'd0) begin
            $display("FAIL: encoder feedback did not move");
            $fatal(1);
        end
        if(limit_fault) begin
            $display("FAIL: unexpected state-limit latch");
            $fatal(1);
        end
        $display("PASS: tb_pmsm_closed_loop_hil_q16");
        $finish;
    end
endmodule

`default_nettype wire
