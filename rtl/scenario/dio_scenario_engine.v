`default_nettype none

module dio_scenario_engine #(
    parameter WIDTH = 16,
    parameter ID_WIDTH = 16,
    parameter QUEUE_DEPTH = 8
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire [63:0]              timestamp,

    input  wire                     enqueue_event,
    input  wire [63:0]              event_timestamp,
    input  wire [WIDTH-1:0]         event_mask,
    input  wire [WIDTH-1:0]         event_value,
    input  wire [ID_WIDTH-1:0]      event_id,

    input  wire                     clear_queue,
    input  wire                     clear_status,
    input  wire [WIDTH-1:0]         safe_value,
    input  wire                     force_safe,

    output reg  [WIDTH-1:0]         dio_out,
    output wire [15:0]              queue_level,
    output wire                     queue_empty,
    output wire                     queue_full,
    output wire                     queue_overflow_latched,
    output wire                     queue_order_error_latched,

    output reg                      event_applied_pulse,
    output reg  [ID_WIDTH-1:0]      applied_event_id,
    output reg  [63:0]              requested_timestamp,
    output reg  [63:0]              actual_timestamp,
    output reg  [63:0]              late_ticks,
    output reg                      late_event_latched
);

    wire [63:0] head_timestamp;
    wire [WIDTH-1:0] head_mask;
    wire [WIDTH-1:0] head_value;
    wire [ID_WIDTH-1:0] head_event_id;
    wire event_due;
    wire queue_clear;

    assign queue_clear = clear_queue | force_safe;
    assign event_due = !queue_empty &&
                       !clear_queue &&
                       !force_safe &&
                       (timestamp >= head_timestamp);

    hil_event_queue #(
        .WIDTH(WIDTH),
        .ID_WIDTH(ID_WIDTH),
        .DEPTH(QUEUE_DEPTH)
    ) u_event_queue (
        .clk(clk),
        .rst_n(rst_n),
        .clear_queue(queue_clear),
        .clear_errors(clear_status),
        .push(enqueue_event),
        .push_timestamp(event_timestamp),
        .push_mask(event_mask),
        .push_value(event_value),
        .push_event_id(event_id),
        .pop(event_due),
        .head_timestamp(head_timestamp),
        .head_mask(head_mask),
        .head_value(head_value),
        .head_event_id(head_event_id),
        .empty(queue_empty),
        .full(queue_full),
        .level(queue_level),
        .overflow_latched(queue_overflow_latched),
        .order_error_latched(queue_order_error_latched)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dio_out <= {WIDTH{1'b0}};
            event_applied_pulse <= 1'b0;
            applied_event_id <= {ID_WIDTH{1'b0}};
            requested_timestamp <= 64'd0;
            actual_timestamp <= 64'd0;
            late_ticks <= 64'd0;
            late_event_latched <= 1'b0;
        end else begin
            event_applied_pulse <= 1'b0;

            if (clear_status)
                late_event_latched <= 1'b0;

            if (force_safe) begin
                dio_out <= safe_value;
            end else if (event_due) begin
                dio_out <= (dio_out & ~head_mask) |
                           (head_value & head_mask);
                event_applied_pulse <= 1'b1;
                applied_event_id <= head_event_id;
                requested_timestamp <= head_timestamp;
                actual_timestamp <= timestamp;
                late_ticks <= timestamp - head_timestamp;
                if (timestamp > head_timestamp)
                    late_event_latched <= 1'b1;
            end
        end
    end

endmodule

`default_nettype wire
