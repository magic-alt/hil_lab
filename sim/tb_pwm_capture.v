`timescale 1ns/1ps
`default_nettype none

module tb_pwm_capture;

    reg clk;
    reg rst_n;
    reg pwm_in;

    wire [63:0] timestamp;
    wire [31:0] period_ticks;
    wire [31:0] high_ticks;
    wire [31:0] low_ticks;
    wire [63:0] rise_ts;
    wire [63:0] fall_ts;
    wire period_valid;
    wire high_valid;
    wire low_valid;
    wire pwm_sync;

    integer valid_count;
    integer errors;
    reg [31:0] last_period;
    reg [31:0] last_high;
    reg [31:0] last_low;

    hil_timebase u_time (
        .clk(clk),
        .rst_n(rst_n),
        .timestamp(timestamp)
    );

    pwm_capture u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .pwm_async(pwm_in),
        .timestamp(timestamp),
        .period_ticks(period_ticks),
        .high_ticks(high_ticks),
        .low_ticks(low_ticks),
        .last_rise_timestamp(rise_ts),
        .last_fall_timestamp(fall_ts),
        .period_valid(period_valid),
        .high_valid(high_valid),
        .low_valid(low_valid),
        .pwm_sync(pwm_sync)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (period_valid) begin
            valid_count = valid_count + 1;
            last_period = period_ticks;
        end
        if (high_valid)
            last_high = high_ticks;
        if (low_valid)
            last_low = low_ticks;
    end

    task drive_pwm_cycle;
        begin
            @(negedge clk);
            pwm_in = 1'b1;
            repeat (30) @(posedge clk);
            @(negedge clk);
            pwm_in = 1'b0;
            repeat (70) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("build/tb_pwm_capture.vcd");
        $dumpvars(0, tb_pwm_capture);

        clk = 1'b0;
        rst_n = 1'b0;
        pwm_in = 1'b0;
        valid_count = 0;
        errors = 0;
        last_period = 0;
        last_high = 0;
        last_low = 0;

        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (4) @(posedge clk);

        drive_pwm_cycle();
        drive_pwm_cycle();
        drive_pwm_cycle();
        drive_pwm_cycle();
        repeat (8) @(posedge clk);

        if (valid_count < 2) begin
            $display("ERROR: expected repeated period measurements");
            errors = errors + 1;
        end
        if (last_period != 32'd100) begin
            $display("ERROR: period=%0d expected=100", last_period);
            errors = errors + 1;
        end
        if (last_high != 32'd30) begin
            $display("ERROR: high=%0d expected=30", last_high);
            errors = errors + 1;
        end
        if (last_low != 32'd70) begin
            $display("ERROR: low=%0d expected=70", last_low);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_pwm_capture");
            $finish;
        end

        $display("FAIL: tb_pwm_capture errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
