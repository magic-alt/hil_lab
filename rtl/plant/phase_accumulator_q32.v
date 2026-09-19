`default_nettype none

module phase_accumulator_q32 (
    input  wire                    clk,
    input  wire                    rst_n,
    input  wire                    clear,
    input  wire                    update_en,
    input  wire signed [31:0]      omega_rad_s_q16,
    input  wire signed [31:0]      k_rad_to_turn_q32,
    output reg  [31:0]             phase_turn_q32
);
    reg signed [63:0] product;
    reg signed [47:0] delta_phase_ext;

    always @* begin
        product = omega_rad_s_q16 * k_rad_to_turn_q32;
        delta_phase_ext = product >>> 16;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            phase_turn_q32 <= 32'd0;
        else if (clear)
            phase_turn_q32 <= 32'd0;
        else if (update_en)
            phase_turn_q32 <= phase_turn_q32 + delta_phase_ext[31:0];
    end
endmodule

`default_nettype wire
