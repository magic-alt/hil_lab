`timescale 1ns/1ps
`default_nettype none

module tb_pwm_complementary_generator;

    reg clk;
    reg rst_n;
    reg enable;
    reg [31:0] period_ticks;
    reg [31:0] high_ticks;
    reg [31:0] deadtime_ticks;

    wire pwm_high;
    wire pwm_low;
    wire cycle_pulse;

    reg [63:0] timestamp;
    wire [31:0] measured_period;
    wire [31:0] measured_high;
    wire [31:0] measured_low;
    wire period_valid;
    wire high_valid;
    wire low_valid;
    wire pwm_sync;

    integer cycles_seen;
    integer period_seen;

    pwm_complementary_generator dut_gen (
        .clk(clk), .rst_n(rst_n), .enable(enable),
        .period_ticks(period_ticks), .high_ticks(high_ticks),
        .deadtime_ticks(deadtime_ticks),
        .pwm_high(pwm_high), .pwm_low(pwm_low),
        .cycle_pulse(cycle_pulse)
    );

    pwm_capture dut_cap (
        .clk(clk), .rst_n(rst_n), .pwm_async(pwm_high),
        .timestamp(timestamp), .period_ticks(measured_period),
        .high_ticks(measured_high), .low_ticks(measured_low),
        .last_rise_timestamp(), .last_fall_timestamp(),
        .period_valid(period_valid), .high_valid(high_valid),
        .low_valid(low_valid), .pwm_sync(pwm_sync)
    );

    always #5 clk = ~clk;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            timestamp <= 64'd0;
        else
            timestamp <= timestamp + 64'd1;
    end

    always @(posedge clk) begin
        if (pwm_high && pwm_low) begin
            $display("FAIL: complementary outputs overlap");
            $fatal;
        end
        if (cycle_pulse)
            cycles_seen = cycles_seen + 1;
        if (period_valid)
            period_seen = period_seen + 1;
    end

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        enable = 1'b0;
        period_ticks = 32'd100;
        high_ticks = 32'd50;
        deadtime_ticks = 32'd5;
        timestamp = 64'd0;
        cycles_seen = 0;
        period_seen = 0;

        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        enable = 1'b1;

        repeat (450) @(posedge clk);

        if (cycles_seen < 3) begin
            $display("FAIL: too few PWM cycles: %0d", cycles_seen);
            $fatal;
        end

        if (period_seen < 2) begin
            $display("FAIL: no stable PWM capture result");
            $fatal;
        end

        if (measured_period != 32'd100) begin
            $display("FAIL: period %0d != 100", measured_period);
            $fatal;
        end

        if ((measured_high < 32'd44) || (measured_high > 32'd46)) begin
            $display("FAIL: measured high %0d outside expected range", measured_high);
            $fatal;
        end

        enable = 1'b0;
        repeat (4) @(posedge clk);
        if (pwm_high || pwm_low) begin
            $display("FAIL: outputs not safe when disabled");
            $fatal;
        end

        $display("PASS: pwm complementary generator");
        $finish;
    end

endmodule

`default_nettype wire
