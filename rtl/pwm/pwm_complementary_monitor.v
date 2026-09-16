`default_nettype none

module pwm_complementary_monitor (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        high_async,
    input  wire        low_async,
    input  wire [63:0] timestamp,
    input  wire [31:0] min_deadtime_ticks,
    input  wire        clear_faults,

    output reg  [31:0] deadtime_high_to_low_ticks,
    output reg  [31:0] deadtime_low_to_high_ticks,
    output reg         deadtime_high_to_low_valid,
    output reg         deadtime_low_to_high_valid,
    output reg         shoot_through_latched,
    output reg         deadtime_violation_latched
);

    wire [1:0] sync_bus;
    wire high_sync;
    wire low_sync;

    reg high_d;
    reg low_d;

    reg [63:0] high_fall_timestamp;
    reg [63:0] low_fall_timestamp;
    reg        high_fall_seen;
    reg        low_fall_seen;

    wire high_rise;
    wire high_fall;
    wire low_rise;
    wire low_fall;
    wire [63:0] high_to_low_delta;
    wire [63:0] low_to_high_delta;
    wire [63:0] min_deadtime_extended;

    sync_2ff #(
        .WIDTH(2)
    ) u_sync (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in ({high_async, low_async}),
        .sync_out (sync_bus)
    );

    assign high_sync = sync_bus[1];
    assign low_sync  = sync_bus[0];

    assign high_rise = high_sync & ~high_d;
    assign high_fall = ~high_sync & high_d;
    assign low_rise  = low_sync & ~low_d;
    assign low_fall  = ~low_sync & low_d;
    assign high_to_low_delta = timestamp - high_fall_timestamp;
    assign low_to_high_delta = timestamp - low_fall_timestamp;
    assign min_deadtime_extended = {32'd0, min_deadtime_ticks};

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            high_d <= 1'b0;
            low_d  <= 1'b0;
        end else begin
            high_d <= high_sync;
            low_d  <= low_sync;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            deadtime_high_to_low_ticks <= 32'd0;
            deadtime_low_to_high_ticks <= 32'd0;
            deadtime_high_to_low_valid <= 1'b0;
            deadtime_low_to_high_valid <= 1'b0;
            shoot_through_latched      <= 1'b0;
            deadtime_violation_latched <= 1'b0;
            high_fall_timestamp        <= 64'd0;
            low_fall_timestamp         <= 64'd0;
            high_fall_seen             <= 1'b0;
            low_fall_seen              <= 1'b0;
        end else begin
            deadtime_high_to_low_valid <= 1'b0;
            deadtime_low_to_high_valid <= 1'b0;

            if (clear_faults) begin
                shoot_through_latched      <= 1'b0;
                deadtime_violation_latched <= 1'b0;
            end

            if (high_sync && low_sync)
                shoot_through_latched <= 1'b1;

            if (high_fall) begin
                high_fall_timestamp <= timestamp;
                high_fall_seen <= 1'b1;
            end

            if (low_fall) begin
                low_fall_timestamp <= timestamp;
                low_fall_seen <= 1'b1;
            end

            if (low_rise) begin
                if (high_fall) begin
                    deadtime_high_to_low_ticks <= 32'd0;
                    deadtime_high_to_low_valid <= 1'b1;
                    if (min_deadtime_ticks != 32'd0)
                        deadtime_violation_latched <= 1'b1;
                end else if (high_fall_seen) begin
                    deadtime_high_to_low_ticks <= high_to_low_delta[31:0];
                    deadtime_high_to_low_valid <= 1'b1;
                    if (high_to_low_delta < min_deadtime_extended)
                        deadtime_violation_latched <= 1'b1;
                end
            end

            if (high_rise) begin
                if (low_fall) begin
                    deadtime_low_to_high_ticks <= 32'd0;
                    deadtime_low_to_high_valid <= 1'b1;
                    if (min_deadtime_ticks != 32'd0)
                        deadtime_violation_latched <= 1'b1;
                end else if (low_fall_seen) begin
                    deadtime_low_to_high_ticks <= low_to_high_delta[31:0];
                    deadtime_low_to_high_valid <= 1'b1;
                    if (low_to_high_delta < min_deadtime_extended)
                        deadtime_violation_latched <= 1'b1;
                end
            end
        end
    end

endmodule

`default_nettype wire
