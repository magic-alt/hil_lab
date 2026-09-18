`default_nettype none

module ssi_encoder_master_capture #(
    parameter DATA_BITS = 24
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     start,
    input  wire [31:0]              half_period_ticks,
    input  wire                     ssi_data_async,

    output reg                      ssi_clk,
    output reg  [DATA_BITS-1:0]     captured_data,
    output reg                      busy,
    output reg                      done_pulse,
    output reg  [15:0]              bit_count
);

    wire data_sync;
    reg  [31:0] tick_count;
    reg         phase_low;

    wire half_period_due;

    sync_2ff #(.WIDTH(1)) u_sync (
        .clk(clk),
        .rst_n(rst_n),
        .async_in(ssi_data_async),
        .sync_out(data_sync)
    );

    assign half_period_due = (half_period_ticks <= 32'd1) ?
                             1'b1 :
                             (tick_count >= (half_period_ticks - 32'd1));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ssi_clk       <= 1'b1;
            captured_data <= {DATA_BITS{1'b0}};
            busy          <= 1'b0;
            done_pulse    <= 1'b0;
            bit_count     <= 16'd0;
            tick_count    <= 32'd0;
            phase_low     <= 1'b0;
        end else begin
            done_pulse <= 1'b0;

            if (!busy) begin
                ssi_clk    <= 1'b1;
                tick_count <= 32'd0;
                phase_low  <= 1'b0;

                if (start) begin
                    captured_data <= {DATA_BITS{1'b0}};
                    bit_count <= 16'd0;
                    busy <= 1'b1;
                end
            end else if (half_period_due) begin
                tick_count <= 32'd0;

                if (!phase_low) begin
                    ssi_clk   <= 1'b0;
                    phase_low <= 1'b1;
                end else begin
                    ssi_clk <= 1'b1;
                    phase_low <= 1'b0;
                    captured_data <= {captured_data[DATA_BITS-2:0], data_sync};

                    if (bit_count >= (DATA_BITS - 1)) begin
                        bit_count  <= DATA_BITS;
                        busy       <= 1'b0;
                        done_pulse <= 1'b1;
                    end else begin
                        bit_count <= bit_count + 16'd1;
                    end
                end
            end else begin
                tick_count <= tick_count + 32'd1;
            end
        end
    end

endmodule

`default_nettype wire
