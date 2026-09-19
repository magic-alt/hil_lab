`timescale 1ns/1ps
`default_nettype none

module tb_plant_transforms_q16;
    reg [31:0] period;
    reg [31:0] high;
    reg valid;
    wire [31:0] duty;

    reg signed [31:0] alpha;
    reg signed [31:0] beta;
    reg signed [31:0] sinv;
    reg signed [31:0] cosv;
    wire signed [31:0] d;
    wire signed [31:0] q;
    wire signed [31:0] alpha_back;
    wire signed [31:0] beta_back;

    reg [31:0] phase;
    wire signed [31:0] sin_lut;
    wire signed [31:0] cos_lut;
    integer errors;

    pwm_ticks_to_duty_q16 u_duty(
        .period_ticks(period),.high_ticks(high),.valid(valid),.duty_q16(duty)
    );
    park_alphabeta_q16 u_park(
        .alpha_q16(alpha),.beta_q16(beta),.sin_q16(sinv),.cos_q16(cosv),
        .d_q16(d),.q_q16(q)
    );
    inverse_park_q16 u_inv(
        .d_q16(d),.q_q16(q),.sin_q16(sinv),.cos_q16(cosv),
        .alpha_q16(alpha_back),.beta_q16(beta_back)
    );
    sincos_lut_q16 u_lut(.phase_turn_q32(phase),.sin_q16(sin_lut),.cos_q16(cos_lut));

    initial begin
        errors=0; period=5000; high=2500; valid=1;
        alpha=32'sd65536; beta=32'sd32768; sinv=0; cosv=32'sd65536;
        phase=0; #1;
        if(duty!==32'h00008000) errors=errors+1;
        if(d!==alpha || q!==beta || alpha_back!==alpha || beta_back!==beta)
            errors=errors+1;
        if(sin_lut!==0 || cos_lut<32'sd65000) errors=errors+1;

        phase=32'h40000000; #1;
        if(sin_lut<32'sd65000 || (cos_lut>32'sd2000) || (cos_lut< -32'sd2000))
            errors=errors+1;

        if(errors==0) begin
            $display("PASS: tb_plant_transforms_q16");
            $finish;
        end
        $display("FAIL: tb_plant_transforms_q16 errors=%0d",errors);
        $fatal(1);
    end
endmodule

`default_nettype wire
