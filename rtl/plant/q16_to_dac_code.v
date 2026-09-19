`default_nettype none

module q16_to_dac_code (
    input  wire signed [31:0] signal_q16,
    input  wire signed [31:0] gain_codes_per_unit_q16,
    input  wire [15:0]        offset_code,
    output reg  [15:0]        dac_code
);
    reg signed [63:0] product;
    reg signed [63:0] code_ext;

    always @* begin
        product = signal_q16 * gain_codes_per_unit_q16;
        code_ext = $signed({1'b0, offset_code}) + (product >>> 32);
        if (code_ext < 0)
            dac_code = 16'h0000;
        else if (code_ext > 65535)
            dac_code = 16'hffff;
        else
            dac_code = code_ext[15:0];
    end
endmodule

`default_nettype wire
