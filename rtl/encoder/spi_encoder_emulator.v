`default_nettype none

module spi_encoder_emulator #(
    parameter FRAME_BITS = 24
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  spi_sclk_async,
    input  wire                  spi_cs_n_async,
    input  wire                  spi_mosi_async,
    input  wire [FRAME_BITS-1:0] frame_data,
    input  wire [FRAME_BITS-1:0] fault_flip_mask,
    input  wire                  fault_enable,

    output reg                   spi_miso,
    output reg                   frame_active,
    output reg                   frame_done_pulse,
    output reg  [15:0]           received_bit_count,
    output reg  [FRAME_BITS-1:0] received_mosi_data
);

    wire [2:0] sync_bus;
    wire spi_cs_n;
    wire spi_sclk;
    wire spi_mosi;

    reg spi_cs_n_d;
    reg spi_sclk_d;
    reg [FRAME_BITS-1:0] shift_reg;
    reg [15:0] remaining_bits;

    wire cs_fall;
    wire cs_rise;
    wire sclk_fall;
    wire sclk_rise;
    wire [FRAME_BITS-1:0] effective_frame;

    sync_2ff #(
        .WIDTH(3)
    ) u_sync (
        .clk      (clk),
        .rst_n    (rst_n),
        .async_in ({spi_cs_n_async, spi_sclk_async, spi_mosi_async}),
        .sync_out (sync_bus)
    );

    assign spi_cs_n = sync_bus[2];
    assign spi_sclk = sync_bus[1];
    assign spi_mosi = sync_bus[0];

    assign cs_fall   = spi_cs_n_d & ~spi_cs_n;
    assign cs_rise   = ~spi_cs_n_d & spi_cs_n;
    assign sclk_fall = spi_sclk_d & ~spi_sclk;
    assign sclk_rise = ~spi_sclk_d & spi_sclk;

    assign effective_frame = fault_enable ?
                             (frame_data ^ fault_flip_mask) :
                             frame_data;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_cs_n_d <= 1'b1;
            spi_sclk_d <= 1'b0;
        end else begin
            spi_cs_n_d <= spi_cs_n;
            spi_sclk_d <= spi_sclk;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_miso           <= 1'b0;
            frame_active       <= 1'b0;
            frame_done_pulse   <= 1'b0;
            received_bit_count <= 16'd0;
            received_mosi_data <= {FRAME_BITS{1'b0}};
            remaining_bits     <= 16'd0;
            shift_reg          <= {FRAME_BITS{1'b0}};
        end else begin
            frame_done_pulse <= 1'b0;

            if (cs_fall) begin
                shift_reg          <= effective_frame;
                remaining_bits     <= FRAME_BITS;
                received_bit_count <= 16'd0;
                received_mosi_data <= {FRAME_BITS{1'b0}};
                frame_active       <= 1'b1;
                spi_miso           <= effective_frame[FRAME_BITS-1];
            end else if (frame_active && !spi_cs_n && sclk_fall) begin
                if (remaining_bits > 16'd1) begin
                    shift_reg <= {shift_reg[FRAME_BITS-2:0], 1'b0};
                    remaining_bits <= remaining_bits - 16'd1;
                    spi_miso <= shift_reg[FRAME_BITS-2];
                end else begin
                    remaining_bits <= 16'd0;
                    spi_miso <= 1'b0;
                end
            end

            if (frame_active && !spi_cs_n && sclk_rise) begin
                received_mosi_data <= {received_mosi_data[FRAME_BITS-2:0], spi_mosi};
                received_bit_count <= received_bit_count + 16'd1;
            end

            if (cs_rise && frame_active) begin
                frame_active <= 1'b0;
                frame_done_pulse <= 1'b1;
                spi_miso <= 1'b0;
            end
        end
    end

endmodule

`default_nettype wire
