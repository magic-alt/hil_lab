`default_nettype none

// Four deterministic calibration vectors for G1 DAC bring-up. Across the four
// selectors every channel sees each required qualification level once, while
// each vector keeps all four channels distinct for routing checks.
module dac_eval_pattern_generator (
    input  wire [1:0]  pattern_select,
    output reg  [15:0] ch0_code,
    output reg  [15:0] ch1_code,
    output reg  [15:0] ch2_code,
    output reg  [15:0] ch3_code
);

    // AD3542R configured for the 0 V to 5 V range.
    // Rounded ideal codes for 0.25 V, 1.65 V, 3.00 V and 3.30 V.
    localparam [15:0] CODE_0V25 = 16'h0CCD;
    localparam [15:0] CODE_1V65 = 16'h547B;
    localparam [15:0] CODE_3V00 = 16'h9999;
    localparam [15:0] CODE_3V30 = 16'hA8F5;

    always @* begin
        case (pattern_select)
            2'b00: begin
                ch0_code = CODE_0V25;
                ch1_code = CODE_1V65;
                ch2_code = CODE_3V00;
                ch3_code = CODE_3V30;
            end
            2'b01: begin
                ch0_code = CODE_1V65;
                ch1_code = CODE_3V00;
                ch2_code = CODE_3V30;
                ch3_code = CODE_0V25;
            end
            2'b10: begin
                ch0_code = CODE_3V00;
                ch1_code = CODE_3V30;
                ch2_code = CODE_0V25;
                ch3_code = CODE_1V65;
            end
            default: begin
                ch0_code = CODE_3V30;
                ch1_code = CODE_0V25;
                ch2_code = CODE_1V65;
                ch3_code = CODE_3V00;
            end
        endcase
    end

endmodule

`default_nettype wire
