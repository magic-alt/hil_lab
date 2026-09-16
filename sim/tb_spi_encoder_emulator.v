`timescale 1ns/1ps
`default_nettype none

module tb_spi_encoder_emulator;

    reg clk;
    reg rst_n;
    reg sclk;
    reg cs_n;
    reg mosi;
    reg [7:0] frame_data;
    reg [7:0] fault_mask;
    reg fault_enable;

    wire miso;
    wire frame_active;
    wire frame_done;
    wire [15:0] received_bit_count;

    reg [7:0] rx_word;
    integer bit_index;
    integer errors;

    spi_encoder_emulator #(
        .FRAME_BITS(8)
    ) u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .spi_sclk_async(sclk),
        .spi_cs_n_async(cs_n),
        .spi_mosi_async(mosi),
        .frame_data(frame_data),
        .fault_flip_mask(fault_mask),
        .fault_enable(fault_enable),
        .spi_miso(miso),
        .frame_active(frame_active),
        .frame_done_pulse(frame_done),
        .received_bit_count(received_bit_count)
    );

    always #5 clk = ~clk;

    task transfer_byte;
        output [7:0] data;
        begin
            data = 8'h00;
            sclk = 1'b0;
            cs_n = 1'b0;
            repeat (6) @(posedge clk);

            for (bit_index = 7; bit_index >= 0; bit_index = bit_index - 1) begin
                #40;
                sclk = 1'b1;
                #30;
                data[bit_index] = miso;
                #30;
                sclk = 1'b0;
                #40;
            end

            cs_n = 1'b1;
            repeat (6) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("build/tb_spi_encoder_emulator.vcd");
        $dumpvars(0, tb_spi_encoder_emulator);

        clk = 1'b0;
        rst_n = 1'b0;
        sclk = 1'b0;
        cs_n = 1'b1;
        mosi = 1'b0;
        frame_data = 8'hA6;
        fault_mask = 8'h00;
        fault_enable = 1'b0;
        rx_word = 8'h00;
        errors = 0;

        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk);

        transfer_byte(rx_word);
        if (rx_word != 8'hA6) begin
            $display("ERROR: SPI rx=%02x expected=A6", rx_word);
            errors = errors + 1;
        end

        fault_enable = 1'b1;
        fault_mask = 8'h01;
        transfer_byte(rx_word);
        if (rx_word != 8'hA7) begin
            $display("ERROR: SPI fault rx=%02x expected=A7", rx_word);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_spi_encoder_emulator");
            $finish;
        end

        $display("FAIL: tb_spi_encoder_emulator errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
