`default_nettype none

module pwm_complementary_generator (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    input  wire [31:0] period_ticks,
    input  wire [31:0] high_ticks,
    input  wire [31:0] deadtime_ticks,

    output reg         pwm_high,
    output reg         pwm_low,
    output reg         cycle_pulse
);

    reg [31:0] counter;
    wire period_valid;
    wire [32:0] low_start_ext;

    assign period_valid = (period_ticks >= 32'd4);
    assign low_start_ext = {1'b0, high_ticks} + {1'b0, deadtime_ticks};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter     <= 32'd0;
            pwm_high    <= 1'b0;
            pwm_low     <= 1'b0;
            cycle_pulse <= 1'b0;
        end else begin
            cycle_pulse <= 1'b0;

            if (!enable || !period_valid) begin
                counter  <= 32'd0;
                pwm_high <= 1'b0;
                pwm_low  <= 1'b0;
            end else begin
                if (counter >= (period_ticks - 32'd1)) begin
                    counter <= 32'd0;
                    cycle_pulse <= 1'b1;
                end else begin
                    counter <= counter + 32'd1;
                end

                if ((high_ticks > deadtime_ticks) &&
                    (counter >= deadtime_ticks) &&
                    (counter < high_ticks))
                    pwm_high <= 1'b1;
                else
                    pwm_high <= 1'b0;

                if ((low_start_ext[32] == 1'b0) &&
                    (low_start_ext[31:0] < period_ticks) &&
                    (counter >= low_start_ext[31:0]) &&
                    (counter < period_ticks))
                    pwm_low <= 1'b1;
                else
                    pwm_low <= 1'b0;
            end
        end
    end

endmodule

`default_nettype wire
