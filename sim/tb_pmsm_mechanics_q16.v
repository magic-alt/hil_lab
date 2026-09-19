`timescale 1ns/1ps
`default_nettype none

module tb_pmsm_mechanics_q16;

    localparam signed [31:0] Q16_ONE = 32'sd65536;
    localparam signed [31:0] Q16_TWO = 32'sd131072;

    reg clk;
    reg rst_n;
    reg update_en;
    reg signed [31:0] motor_torque_q16;
    reg signed [31:0] load_torque_q16;
    reg signed [31:0] k_accel_q16;
    reg signed [31:0] k_damp_q16;
    reg signed [31:0] k_theta_q16;

    wire signed [31:0] omega_m_q16;
    wire signed [31:0] theta_m_q16;
    wire signed [31:0] delta_omega_q16;

    integer errors;

    pmsm_mechanics_q16 u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .update_en(update_en),
        .motor_torque_q16(motor_torque_q16),
        .load_torque_q16(load_torque_q16),
        .k_accel_q16(k_accel_q16),
        .k_damp_q16(k_damp_q16),
        .k_theta_q16(k_theta_q16),
        .omega_m_q16(omega_m_q16),
        .theta_m_q16(theta_m_q16),
        .delta_omega_q16(delta_omega_q16)
    );

    always #5 clk = ~clk;

    task step_once;
        begin
            @(negedge clk);
            update_en = 1'b1;
            @(posedge clk);
            #1;
            @(negedge clk);
            update_en = 1'b0;
        end
    endtask

    initial begin
        $dumpfile("build/tb_pmsm_mechanics_q16.vcd");
        $dumpvars(0, tb_pmsm_mechanics_q16);

        clk = 1'b0;
        rst_n = 1'b0;
        update_en = 1'b0;
        motor_torque_q16 = 32'sd0;
        load_torque_q16 = 32'sd0;
        k_accel_q16 = Q16_ONE;
        k_damp_q16 = 32'sd0;
        k_theta_q16 = Q16_ONE;
        errors = 0;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;

        motor_torque_q16 = Q16_ONE;
        step_once();
        if ((omega_m_q16 != Q16_ONE) || (theta_m_q16 != 32'sd0)) begin
            $display("ERROR: first mechanics step omega=%0d theta=%0d",
                     omega_m_q16, theta_m_q16);
            errors = errors + 1;
        end

        motor_torque_q16 = 32'sd0;
        step_once();
        if ((omega_m_q16 != Q16_ONE) || (theta_m_q16 != Q16_ONE)) begin
            $display("ERROR: coast step omega=%0d theta=%0d",
                     omega_m_q16, theta_m_q16);
            errors = errors + 1;
        end

        load_torque_q16 = Q16_ONE;
        step_once();
        if ((omega_m_q16 != 32'sd0) || (theta_m_q16 != Q16_TWO)) begin
            $display("ERROR: load step omega=%0d theta=%0d",
                     omega_m_q16, theta_m_q16);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_pmsm_mechanics_q16");
            $finish;
        end

        $display("FAIL: tb_pmsm_mechanics_q16 errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
