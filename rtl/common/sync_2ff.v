`default_nettype none

module sync_2ff #(
    parameter WIDTH = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [WIDTH-1:0]     async_in,
    output wire [WIDTH-1:0]     sync_out
);

    (* ASYNC_REG = "TRUE", SHREG_EXTRACT = "NO" *)
    reg [WIDTH-1:0] meta;

    (* ASYNC_REG = "TRUE", SHREG_EXTRACT = "NO" *)
    reg [WIDTH-1:0] sync_reg;

    assign sync_out = sync_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            meta     <= {WIDTH{1'b0}};
            sync_reg <= {WIDTH{1'b0}};
        end else begin
            meta     <= async_in;
            sync_reg <= meta;
        end
    end

endmodule

`default_nettype wire
