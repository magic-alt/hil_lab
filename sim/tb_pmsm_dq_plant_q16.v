`timescale 1ns/1ps
`default_nettype none

module tb_pmsm_dq_plant_q16;

    reg clk;
    reg rst_n;
    reg update_en;

    wire signed [31:0] id_q16;
    wire signed [31:0] iq_q16;
    wire signed [31:0] torque_q16;
    wire signed [31:0] omega_m_q16;
    wire signed [31:0] theta_m_q16;
    wire signed [31:0] omega_e_q16;

    pmsm_dq_plant_q16 dut (
        .clk(clk), .rst_n(rst_n), .update_en(update_en),
        .vd_q16(32'sd0),
        .vq_q16(32'sd65536),
        .load_torque_q16(32'sd0),
        .pole_pairs(16'd4),
        .k_vd_q16(32'sd16384),
        .k_vq_q16(32'sd16384),
        .k_r_d_q16(32'sd4096),
        .k_r_q_q16(32'sd4096),
        .k_cross_d_q16(32'sd0),
        .k_cross_q_q16(32'sd0),
        .k_flux_q16(32'sd0),
        .k_torque_q16(32'sd32768),
        .k_accel_q16(32'sd8192),
        .k_damp_q16(32'sd512),
        .k_theta_q16(32'sd4096),
        .id_q16(id_q16), .iq_q16(iq_q16),
        .torque_q16(torque_q16),
        .omega_m_q16(omega_m_q16),
        .theta_m_q16(theta_m_q16),
        .omega_e_q16(omega_e_q16)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        update_en = 1'b0;

        repeat (5) @(posedge clk);
        rst_n = 1'b1;

        repeat (40) begin
            @(posedge clk);
            update_en = 1'b1;
            @(posedge clk);
            update_en = 1'b0;
        end

        if (iq_q16 <= 0) begin
            $display("FAIL: iq did not rise: %0d", iq_q16);
            $fatal;
        end

        if (omega_m_q16 <= 0) begin
            $display("FAIL: omega did not rise: %0d", omega_m_q16);
            $fatal;
        end

        if (theta_m_q16 <= 0) begin
            $display("FAIL: theta did not rise: %0d", theta_m_q16);
            $fatal;
        end

        $display("PASS: PMSM-lite Q16 plant");
        $finish;
    end

endmodule

`default_nettype wire
