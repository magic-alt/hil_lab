`default_nettype none

// Averaged two-level three-phase inverter model.
//
// Inputs use Q16.16:
//   duty_*_q16: 0.0 .. 1.0 (values above 1.0 are clamped)
//   vbus_q16:   DC-bus voltage
//
// The model first computes each leg voltage around half-bus, then removes the
// instantaneous common-mode component so phase_u/v/w are line-neutral values.
// Switching ripple, dead-time distortion and device drops are intentionally
// outside this primitive.
module averaged_inverter_abc_q16 (
    input  wire        [31:0] duty_u_q16,
    input  wire        [31:0] duty_v_q16,
    input  wire        [31:0] duty_w_q16,
    input  wire signed [31:0] vbus_q16,

    output wire signed [31:0] phase_u_q16,
    output wire signed [31:0] phase_v_q16,
    output wire signed [31:0] phase_w_q16,
    output wire signed [31:0] common_mode_q16
);

    function signed [31:0] qmul;
        input signed [31:0] a;
        input signed [31:0] b;
        reg signed [63:0] product;
        begin
            product = a * b;
            qmul = product >>> 16;
        end
    endfunction

    function signed [31:0] centered_duty;
        input [31:0] duty;
        reg [31:0] clamped;
        begin
            if (duty > 32'h00010000)
                clamped = 32'h00010000;
            else
                clamped = duty;

            centered_duty = clamped - 32'h00008000;
        end
    endfunction

    wire signed [31:0] centered_u_q16;
    wire signed [31:0] centered_v_q16;
    wire signed [31:0] centered_w_q16;

    wire signed [31:0] leg_u_q16;
    wire signed [31:0] leg_v_q16;
    wire signed [31:0] leg_w_q16;
    wire signed [33:0] leg_sum_q16;
    wire signed [33:0] common_ext_q16;

    assign centered_u_q16 = centered_duty(duty_u_q16);
    assign centered_v_q16 = centered_duty(duty_v_q16);
    assign centered_w_q16 = centered_duty(duty_w_q16);

    assign leg_u_q16 = qmul(vbus_q16, centered_u_q16);
    assign leg_v_q16 = qmul(vbus_q16, centered_v_q16);
    assign leg_w_q16 = qmul(vbus_q16, centered_w_q16);

    assign leg_sum_q16 =
        {{2{leg_u_q16[31]}}, leg_u_q16} +
        {{2{leg_v_q16[31]}}, leg_v_q16} +
        {{2{leg_w_q16[31]}}, leg_w_q16};

    assign common_ext_q16 = leg_sum_q16 / 34'sd3;
    assign common_mode_q16 = common_ext_q16[31:0];

    assign phase_u_q16 = leg_u_q16 - common_mode_q16;
    assign phase_v_q16 = leg_v_q16 - common_mode_q16;
    assign phase_w_q16 = leg_w_q16 - common_mode_q16;

endmodule

`default_nettype wire
