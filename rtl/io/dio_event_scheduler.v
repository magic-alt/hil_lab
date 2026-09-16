`default_nettype none

module dio_event_scheduler #(
    parameter WIDTH = 16
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [63:0]          timestamp,
    input  wire                 arm,
    input  wire [63:0]          target_timestamp,
    input  wire [WIDTH-1:0]     event_mask,
    input  wire [WIDTH-1:0]     event_value,
    input  wire [WIDTH-1:0]     safe_value,
    input  wire                 force_safe,

    output reg  [WIDTH-1:0]     dio_out,
    output reg                  armed,
    output reg                  event_done_pulse
);

    reg [63:0]      pending_timestamp;
    reg [WIDTH-1:0] pending_mask;
    reg [WIDTH-1:0] pending_value;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dio_out          <= {WIDTH{1'b0}};
            armed            <= 1'b0;
            event_done_pulse <= 1'b0;
            pending_timestamp <= 64'd0;
            pending_mask      <= {WIDTH{1'b0}};
            pending_value     <= {WIDTH{1'b0}};
        end else begin
            event_done_pulse <= 1'b0;

            if (force_safe) begin
                dio_out <= safe_value;
                armed <= 1'b0;
            end else begin
                if (arm) begin
                    pending_timestamp <= target_timestamp;
                    pending_mask      <= event_mask;
                    pending_value     <= event_value;
                    armed             <= 1'b1;
                end

                if (armed && (timestamp >= pending_timestamp)) begin
                    dio_out <= (dio_out & ~pending_mask) |
                               (pending_value & pending_mask);
                    armed <= 1'b0;
                    event_done_pulse <= 1'b1;
                end
            end
        end
    end

endmodule

`default_nettype wire
