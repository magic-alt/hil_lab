`default_nettype none

module pwm_capture (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        pwm_async,
    input  wire [63:0] timestamp,

    output reg  [31:0] period_ticks,
    output reg  [31:0] high_ticks,
    output reg  [31:0] low_ticks,
    output reg  [63:0] last_rise_timestamp,
    output reg  [63:0] last_fall_timestamp,
    output reg         period_valid,
    output reg         high_valid,
    output reg         low_valid,
    output wire        pwm_sync
);

    wire pwm_sync_int;
    reg  pwm_sync_d;
    reg  have_rise;
    reg  have_fall;

    wire rise_edge;
    wire fall_edge;
    wire [63:0] period_delta;
    wire [63:0] high_delta;
    wire [63:0] low_delta;

    sync_2ff #(
        .WIDTH(1)
    ) u_sync (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in (pwm_async),
        .sync_out (pwm_sync_int)
    );

    assign pwm_sync = pwm_sync_int;
    assign rise_edge = pwm_sync_int & ~pwm_sync_d;
    assign fall_edge = ~pwm_sync_int & pwm_sync_d;
    assign period_delta = timestamp - last_rise_timestamp;
    assign high_delta = timestamp - last_rise_timestamp;
    assign low_delta = timestamp - last_fall_timestamp;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            pwm_sync_d <= 1'b0;
        else
            pwm_sync_d <= pwm_sync_int;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            period_ticks        <= 32'd0;
            high_ticks          <= 32'd0;
            low_ticks           <= 32'd0;
            last_rise_timestamp <= 64'd0;
            last_fall_timestamp <= 64'd0;
            period_valid        <= 1'b0;
            high_valid          <= 1'b0;
            low_valid           <= 1'b0;
            have_rise           <= 1'b0;
            have_fall           <= 1'b0;
        end else begin
            period_valid <= 1'b0;
            high_valid   <= 1'b0;
            low_valid    <= 1'b0;

            if (rise_edge) begin
                if (have_rise) begin
                    period_ticks <= period_delta[31:0];
                    period_valid <= 1'b1;
                end

                if (have_fall) begin
                    low_ticks <= low_delta[31:0];
                    low_valid <= 1'b1;
                end

                last_rise_timestamp <= timestamp;
                have_rise <= 1'b1;
            end

            if (fall_edge) begin
                if (have_rise) begin
                    high_ticks <= high_delta[31:0];
                    high_valid <= 1'b1;
                end

                last_fall_timestamp <= timestamp;
                have_fall <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
