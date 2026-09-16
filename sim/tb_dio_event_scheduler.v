`timescale 1ns/1ps
`default_nettype none

module tb_dio_event_scheduler;

    reg clk;
    reg rst_n;
    reg arm;
    reg [63:0] target;
    reg [7:0] mask;
    reg [7:0] value;
    reg [7:0] safe_value;
    reg force_safe;

    wire [63:0] timestamp;
    wire [7:0] dio_out;
    wire armed;
    wire done;

    integer errors;

    hil_timebase u_time (
        .clk(clk),
        .rst_n(rst_n),
        .timestamp(timestamp)
    );

    dio_event_scheduler #(
        .WIDTH(8)
    ) u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .timestamp(timestamp),
        .arm(arm),
        .target_timestamp(target),
        .event_mask(mask),
        .event_value(value),
        .safe_value(safe_value),
        .force_safe(force_safe),
        .dio_out(dio_out),
        .armed(armed),
        .event_done_pulse(done)
    );

    always #5 clk = ~clk;

    initial begin
        $dumpfile("build/tb_dio_event_scheduler.vcd");
        $dumpvars(0, tb_dio_event_scheduler);

        clk = 1'b0;
        rst_n = 1'b0;
        arm = 1'b0;
        target = 64'd0;
        mask = 8'h00;
        value = 8'h00;
        safe_value = 8'hA5;
        force_safe = 1'b0;
        errors = 0;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (3) @(posedge clk);

        target = timestamp + 64'd12;
        mask = 8'h0F;
        value = 8'h05;
        @(negedge clk);
        arm = 1'b1;
        @(negedge clk);
        arm = 1'b0;

        wait (done == 1'b1);
        @(posedge clk);
        if (dio_out != 8'h05) begin
            $display("ERROR: scheduled dio=%02x expected=05", dio_out);
            errors = errors + 1;
        end

        @(negedge clk);
        force_safe = 1'b1;
        @(negedge clk);
        force_safe = 1'b0;
        @(posedge clk);
        if (dio_out != 8'hA5) begin
            $display("ERROR: safe dio=%02x expected=A5", dio_out);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_dio_event_scheduler");
            $finish;
        end

        $display("FAIL: tb_dio_event_scheduler errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
