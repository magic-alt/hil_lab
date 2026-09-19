`default_nettype none

module pwm_ticks_to_duty_q16 (
    input  wire [31:0] period_ticks,
    input  wire [31:0] high_ticks,
    input  wire        valid,
    output reg  [31:0] duty_q16
);
    reg [63:0] numerator;

    always @* begin
        numerator = 64'd0;
        if (!valid || (period_ticks == 32'd0)) begin
            duty_q16 = 32'd0;
        end else if (high_ticks >= period_ticks) begin
            duty_q16 = 32'h00010000;
        end else begin
            numerator = {32'd0, high_ticks} << 16;
            duty_q16 = numerator / period_ticks;
        end
    end
endmodule

`default_nettype wire
