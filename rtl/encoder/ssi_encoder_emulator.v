`default_nettype none

module ssi_encoder_emulator #(
    parameter DATA_BITS = 24
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     enable,
    input  wire                     ssi_clk_async,
    input  wire [DATA_BITS-1:0]     frame_data,
    input  wire [31:0]              frame_gap_ticks,
    input  wire [DATA_BITS-1:0]     fault_flip_mask,
    input  wire                     fault_enable,

    output reg                      ssi_data,
    output reg                      frame_active,
    output reg  [15:0]              bit_count,
    output reg                      frame_done_pulse
);

    wire ssi_clk_sync;
    reg  ssi_clk_d;
    reg  [31:0] gap_count;
    reg  [DATA_BITS-1:0] shift_data;

    wire clk_rise;
    wire clk_fall;
    wire gap_elapsed;
    wire [DATA_BITS-1:0] selected_frame;

    sync_2ff #(.WIDTH(1)) u_sync (
        .clk(clk),
        .rst_n(rst_n),
        .async_in(ssi_clk_async),
        .sync_out(ssi_clk_sync)
    );

    assign clk_rise = ssi_clk_sync & ~ssi_clk_d;
    assign clk_fall = ~ssi_clk_sync & ssi_clk_d;
    assign gap_elapsed = (frame_gap_ticks == 32'd0) ||
                         (gap_count >= frame_gap_ticks);
    assign selected_frame = fault_enable ?
                            (frame_data ^ fault_flip_mask) :
                            frame_data;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ssi_clk_d       <= 1'b1;
            gap_count       <= 32'hffffffff;
            shift_data      <= {DATA_BITS{1'b0}};
            ssi_data        <= 1'b1;
            frame_active    <= 1'b0;
            bit_count       <= 16'd0;
            frame_done_pulse <= 1'b0;
        end else begin
            ssi_clk_d <= ssi_clk_sync;
            frame_done_pulse <= 1'b0;

            if (!enable) begin
                gap_count    <= 32'hffffffff;
                shift_data   <= {DATA_BITS{1'b0}};
                ssi_data     <= 1'b1;
                frame_active <= 1'b0;
                bit_count    <= 16'd0;
            end else begin
                if (clk_rise || clk_fall)
                    gap_count <= 32'd0;
                else if (gap_count != 32'hffffffff)
                    gap_count <= gap_count + 32'd1;

                if (frame_active && gap_elapsed) begin
                    frame_active <= 1'b0;
                    bit_count    <= 16'd0;
                    ssi_data     <= 1'b1;
                end

                if (clk_fall) begin
                    if (!frame_active) begin
                        shift_data   <= selected_frame;
                        ssi_data     <= selected_frame[DATA_BITS-1];
                        frame_active <= 1'b1;
                        bit_count    <= 16'd1;
                    end else if (bit_count < DATA_BITS) begin
                        shift_data <= {shift_data[DATA_BITS-2:0], 1'b0};
                        ssi_data   <= shift_data[DATA_BITS-2];
                        bit_count  <= bit_count + 16'd1;
                    end
                end

                if (frame_active && clk_rise && (bit_count >= DATA_BITS)) begin
                    frame_done_pulse <= 1'b1;
                    frame_active <= 1'b0;
                    bit_count <= 16'd0;
                    ssi_data <= 1'b1;
                end
            end
        end
    end

endmodule

`default_nettype wire
