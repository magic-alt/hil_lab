`default_nettype none

module park_alphabeta_q16 (
    input  wire signed [31:0] alpha_q16,
    input  wire signed [31:0] beta_q16,
    input  wire signed [31:0] sin_q16,
    input  wire signed [31:0] cos_q16,
    output wire signed [31:0] d_q16,
    output wire signed [31:0] q_q16
);
    function signed [31:0] qmul;
        input signed [31:0] x;
        input signed [31:0] y;
        reg signed [63:0] p;
        begin
            p = x * y;
            qmul = p >>> 16;
        end
    endfunction

    assign d_q16 = qmul(alpha_q16, cos_q16) + qmul(beta_q16, sin_q16);
    assign q_q16 = -qmul(alpha_q16, sin_q16) + qmul(beta_q16, cos_q16);
endmodule

`default_nettype wire
