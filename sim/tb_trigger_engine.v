`timescale 1ns/1ps
`default_nettype none

module tb_trigger_engine;

    reg clk;
    reg rst_n;
    reg enable;
    reg trigger_async;
    reg trigger_on_rise;
    reg trigger_on_fall;
    reg clear_status;

    wire [63:0] timestamp;
    wire trigger_sync;
    wire trigger_pulse;
    wire [63:0] trigger_timestamp;
    wire [31:0] trigger_count;
    wire trigger_seen_latched;

    integer errors;

    hil_timebase u_time (
        .clk(clk),
        .rst_n(rst_n),
        .timestamp(timestamp)
    );

    trigger_engine u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .trigger_async(trigger_async),
        .trigger_on_rise(trigger_on_rise),
        .trigger_on_fall(trigger_on_fall),
        .clear_status(clear_status),
        .timestamp(timestamp),
        .trigger_sync(trigger_sync),
        .trigger_pulse(trigger_pulse),
        .trigger_timestamp(trigger_timestamp),
        .trigger_count(trigger_count),
        .trigger_seen_latched(trigger_seen_latched)
    );

    always #5 clk = ~clk;

    initial begin
        $dumpfile("build/tb_trigger_engine.vcd");
        $dumpvars(0, tb_trigger_engine);

        clk = 1'b0;
        rst_n = 1'b0;
        enable = 1'b1;
        trigger_async = 1'b0;
        trigger_on_rise = 1'b1;
        trigger_on_fall = 1'b0;
        clear_status = 1'b0;
        errors = 0;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (2) @(posedge clk);

        @(negedge clk);
        trigger_async = 1'b1;
        wait (trigger_pulse == 1'b1);
        if ((trigger_count != 32'd1) || !trigger_seen_latched ||
            (trigger_timestamp == 64'd0)) begin
            $display("ERROR: rising trigger evidence count=%0d seen=%0d ts=%0d",
                     trigger_count, trigger_seen_latched, trigger_timestamp);
            errors = errors + 1;
        end

        @(negedge clk);
        trigger_on_rise = 1'b0;
        trigger_on_fall = 1'b1;
        trigger_async = 1'b0;
        wait (trigger_pulse == 1'b1);
        if (trigger_count != 32'd2) begin
            $display("ERROR: falling trigger count=%0d", trigger_count);
            errors = errors + 1;
        end

        @(negedge clk);
        clear_status = 1'b1;
        @(negedge clk);
        clear_status = 1'b0;
        @(posedge clk);
        if ((trigger_count != 32'd0) || trigger_seen_latched) begin
            $display("ERROR: clear_status failed");
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_trigger_engine");
            $finish;
        end

        $display("FAIL: tb_trigger_engine errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
