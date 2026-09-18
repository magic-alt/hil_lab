`timescale 1ns/1ps
`default_nettype none

module tb_ssi_encoder_loopback;

    localparam DATA_BITS = 24;
    localparam [DATA_BITS-1:0] TEST_WORD = 24'h5A3CC3;

    reg clk;
    reg rst_n;
    reg start;

    wire ssi_clk;
    wire ssi_data;
    wire [DATA_BITS-1:0] captured_data;
    wire master_busy;
    wire master_done;
    wire [15:0] master_bit_count;
    wire emulator_active;
    wire [15:0] emulator_bit_count;
    wire emulator_done;

    ssi_encoder_master_capture #(.DATA_BITS(DATA_BITS)) master (
        .clk(clk), .rst_n(rst_n), .start(start),
        .half_period_ticks(32'd8), .ssi_data_async(ssi_data),
        .ssi_clk(ssi_clk), .captured_data(captured_data),
        .busy(master_busy), .done_pulse(master_done),
        .bit_count(master_bit_count)
    );

    ssi_encoder_emulator #(.DATA_BITS(DATA_BITS)) emulator (
        .clk(clk), .rst_n(rst_n), .enable(1'b1),
        .ssi_clk_async(ssi_clk), .frame_data(TEST_WORD),
        .frame_gap_ticks(32'd16),
        .fault_flip_mask({DATA_BITS{1'b0}}), .fault_enable(1'b0),
        .ssi_data(ssi_data), .frame_active(emulator_active),
        .bit_count(emulator_bit_count),
        .frame_done_pulse(emulator_done)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        start = 1'b0;

        repeat (8) @(posedge clk);
        rst_n = 1'b1;
        repeat (24) @(posedge clk);

        start = 1'b1;
        @(posedge clk);
        start = 1'b0;

        wait(master_done == 1'b1);
        @(posedge clk);

        if (captured_data !== TEST_WORD) begin
            $display("FAIL: SSI loopback got %h expected %h", captured_data, TEST_WORD);
            $fatal;
        end

        $display("PASS: SSI emulator/master loopback");
        $finish;
    end

    initial begin
        repeat (2000) @(posedge clk);
        $display("FAIL: SSI loopback timeout");
        $fatal;
    end

endmodule

`default_nettype wire
