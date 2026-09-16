`default_nettype none

module hil_timebase #(
    parameter COUNTER_WIDTH = 64
) (
    input  wire                     clk,
    input  wire                     rst_n,
    output reg  [COUNTER_WIDTH-1:0] timestamp
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            timestamp <= {COUNTER_WIDTH{1'b0}};
        else
            timestamp <= timestamp + {{(COUNTER_WIDTH-1){1'b0}}, 1'b1};
    end

endmodule

`default_nettype wire
