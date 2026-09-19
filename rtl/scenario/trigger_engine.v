`default_nettype none

module trigger_engine (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    input  wire        trigger_async,
    input  wire        trigger_on_rise,
    input  wire        trigger_on_fall,
    input  wire        clear_status,
    input  wire [63:0] timestamp,

    output wire        trigger_sync,
    output reg         trigger_pulse,
    output reg  [63:0] trigger_timestamp,
    output reg  [31:0] trigger_count,
    output reg         trigger_seen_latched
);

    wire trigger_sync_int;
    reg trigger_d;
    wire rise_edge;
    wire fall_edge;
    wire selected_edge;

    sync_2ff #(
        .WIDTH(1)
    ) u_sync (
        .clk(clk),
        .rst_n(rst_n),
        .async_in(trigger_async),
        .sync_out(trigger_sync_int)
    );

    assign trigger_sync = trigger_sync_int;
    assign rise_edge = trigger_sync_int & ~trigger_d;
    assign fall_edge = ~trigger_sync_int & trigger_d;
    assign selected_edge = (trigger_on_rise && rise_edge) |
                           (trigger_on_fall && fall_edge);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            trigger_d <= 1'b0;
        else
            trigger_d <= trigger_sync_int;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            trigger_pulse <= 1'b0;
            trigger_timestamp <= 64'd0;
            trigger_count <= 32'd0;
            trigger_seen_latched <= 1'b0;
        end else begin
            trigger_pulse <= 1'b0;

            if (clear_status) begin
                trigger_count <= 32'd0;
                trigger_seen_latched <= 1'b0;
            end else if (enable && selected_edge) begin
                trigger_pulse <= 1'b1;
                trigger_timestamp <= timestamp;
                trigger_count <= trigger_count + 32'd1;
                trigger_seen_latched <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
