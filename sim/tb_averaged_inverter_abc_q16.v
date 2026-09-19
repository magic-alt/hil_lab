`timescale 1ns/1ps
`default_nettype none

module tb_averaged_inverter_abc_q16;

    localparam signed [31:0] Q16_24 = 32'sd1572864;
    localparam signed [31:0] Q16_NEG24 = -32'sd1572864;
    localparam signed [31:0] Q16_48 = 32'sd3145728;

    reg [31:0] duty_u_q16;
    reg [31:0] duty_v_q16;
    reg [31:0] duty_w_q16;
    reg signed [31:0] vbus_q16;

    wire signed [31:0] phase_u_q16;
    wire signed [31:0] phase_v_q16;
    wire signed [31:0] phase_w_q16;
    wire signed [31:0] common_mode_q16;

    integer errors;

    averaged_inverter_abc_q16 u_dut (
        .duty_u_q16(duty_u_q16),
        .duty_v_q16(duty_v_q16),
        .duty_w_q16(duty_w_q16),
        .vbus_q16(vbus_q16),
        .phase_u_q16(phase_u_q16),
        .phase_v_q16(phase_v_q16),
        .phase_w_q16(phase_w_q16),
        .common_mode_q16(common_mode_q16)
    );

    initial begin
        errors = 0;
        vbus_q16 = Q16_48;

        duty_u_q16 = 32'h00008000;
        duty_v_q16 = 32'h00008000;
        duty_w_q16 = 32'h00008000;
        #1;
        if ((phase_u_q16 != 32'sd0) ||
            (phase_v_q16 != 32'sd0) ||
            (phase_w_q16 != 32'sd0) ||
            (common_mode_q16 != 32'sd0)) begin
            $display("ERROR: 50%% duty neutral point is not zero");
            errors = errors + 1;
        end

        duty_u_q16 = 32'h00010000;
        duty_v_q16 = 32'h00008000;
        duty_w_q16 = 32'h00000000;
        #1;
        if ((phase_u_q16 != Q16_24) ||
            (phase_v_q16 != 32'sd0) ||
            (phase_w_q16 != Q16_NEG24) ||
            (common_mode_q16 != 32'sd0)) begin
            $display("ERROR: balanced abc reconstruction u=%0d v=%0d w=%0d cm=%0d",
                     phase_u_q16, phase_v_q16, phase_w_q16, common_mode_q16);
            errors = errors + 1;
        end

        duty_u_q16 = 32'h00020000;
        duty_v_q16 = 32'h00008000;
        duty_w_q16 = 32'h00000000;
        #1;
        if (phase_u_q16 != Q16_24) begin
            $display("ERROR: duty clamp failed u=%0d", phase_u_q16);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_averaged_inverter_abc_q16");
            $finish;
        end

        $display("FAIL: tb_averaged_inverter_abc_q16 errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
