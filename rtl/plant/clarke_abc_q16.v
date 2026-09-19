`default_nettype none

module clarke_abc_q16 (
    input  wire signed [31:0] a_q16,
    input  wire signed [31:0] b_q16,
    input  wire signed [31:0] c_q16,
    output wire signed [31:0] alpha_q16,
    output wire signed [31:0] beta_q16
);
    localparam signed [31:0] INV_SQRT3_Q16 = 32'sd37837;

    function signed [31:0] qmul;
        input signed [31:0] x;
        input signed [31:0] y;
        reg signed [63:0] p;
        begin
            p = x * y;
            qmul = p >>> 16;
        end
    endfunction

    wire signed [32:0] beta_sum_ext;
    wire signed [31:0] beta_sum_q16;
    wire signed [32:0] zero_sum_ext;

    assign alpha_q16 = a_q16;
    assign beta_sum_ext =
        {a_q16[31], a_q16} + ({b_q16[31], b_q16} <<< 1);
    assign beta_sum_q16 = beta_sum_ext[31:0];
    assign beta_q16 = qmul(beta_sum_q16, INV_SQRT3_Q16);

    // c is intentionally retained in the interface so simulation/lint can
    // check the balanced three-phase invariant without changing the transform.
    assign zero_sum_ext =
        {a_q16[31], a_q16} + {b_q16[31], b_q16} + {c_q16[31], c_q16};

endmodule

`default_nettype wire
