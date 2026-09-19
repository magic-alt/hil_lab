`default_nettype none

module inverse_clarke_q16 (
    input  wire signed [31:0] alpha_q16,
    input  wire signed [31:0] beta_q16,
    output wire signed [31:0] a_q16,
    output wire signed [31:0] b_q16,
    output wire signed [31:0] c_q16
);
    localparam signed [31:0] HALF_Q16 = 32'sd32768;
    localparam signed [31:0] SQRT3_HALF_Q16 = 32'sd56756;

    function signed [31:0] qmul;
        input signed [31:0] x;
        input signed [31:0] y;
        reg signed [63:0] p;
        begin
            p = x * y;
            qmul = p >>> 16;
        end
    endfunction

    wire signed [31:0] half_alpha;
    wire signed [31:0] beta_term;

    assign half_alpha = qmul(alpha_q16, HALF_Q16);
    assign beta_term = qmul(beta_q16, SQRT3_HALF_Q16);
    assign a_q16 = alpha_q16;
    assign b_q16 = -half_alpha + beta_term;
    assign c_q16 = -half_alpha - beta_term;
endmodule

`default_nettype wire
