`timescale 1ns/1ps
`default_nettype none

module tb_pwm_complementary_monitor;

    reg clk;
    reg rst_n;
    reg pwm_h;
    reg pwm_l;
    reg clear_faults;
    reg [31:0] min_deadtime;

    wire [63:0] timestamp;
    wire [31:0] dead_hl;
    wire [31:0] dead_lh;
    wire valid_hl;
    wire valid_lh;
    wire shoot_fault;
    wire dead_fault;

    integer errors;
    reg [31:0] last_hl;
    reg [31:0] last_lh;

    hil_timebase u_time (
        .clk(clk),
        .rst_n(rst_n),
        .timestamp(timestamp)
    );

    pwm_complementary_monitor u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .high_async(pwm_h),
        .low_async(pwm_l),
        .timestamp(timestamp),
        .min_deadtime_ticks(min_deadtime),
        .clear_faults(clear_faults),
        .deadtime_high_to_low_ticks(dead_hl),
        .deadtime_low_to_high_ticks(dead_lh),
        .deadtime_high_to_low_valid(valid_hl),
        .deadtime_low_to_high_valid(valid_lh),
        .shoot_through_latched(shoot_fault),
        .deadtime_violation_latched(dead_fault)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (valid_hl)
            last_hl = dead_hl;
        if (valid_lh)
            last_lh = dead_lh;
    end

    task set_h;
        input value;
        begin
            @(negedge clk);
            pwm_h = value;
        end
    endtask

    task set_l;
        input value;
        begin
            @(negedge clk);
            pwm_l = value;
        end
    endtask

    initial begin
        $dumpfile("build/tb_pwm_complementary_monitor.vcd");
        $dumpvars(0, tb_pwm_complementary_monitor);

        clk = 1'b0;
        rst_n = 1'b0;
        pwm_h = 1'b0;
        pwm_l = 1'b0;
        clear_faults = 1'b0;
        min_deadtime = 32'd3;
        errors = 0;
        last_hl = 0;
        last_lh = 0;

        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk);

        set_h(1'b1);
        repeat (20) @(posedge clk);
        set_h(1'b0);
        repeat (5) @(posedge clk);
        set_l(1'b1);
        repeat (20) @(posedge clk);
        set_l(1'b0);
        repeat (5) @(posedge clk);
        set_h(1'b1);
        repeat (10) @(posedge clk);

        if (last_hl < 32'd4 || last_hl > 32'd6) begin
            $display("ERROR: H->L deadtime=%0d expected around 5", last_hl);
            errors = errors + 1;
        end
        if (last_lh < 32'd4 || last_lh > 32'd6) begin
            $display("ERROR: L->H deadtime=%0d expected around 5", last_lh);
            errors = errors + 1;
        end
        if (dead_fault) begin
            $display("ERROR: safe deadtime unexpectedly latched violation");
            errors = errors + 1;
        end

        set_l(1'b1);
        repeat (8) @(posedge clk);
        if (!shoot_fault) begin
            $display("ERROR: overlap did not latch shoot-through fault");
            errors = errors + 1;
        end

        clear_faults = 1'b1;
        @(posedge clk);
        clear_faults = 1'b0;
        set_l(1'b0);
        set_h(1'b0);
        repeat (6) @(posedge clk);

        set_h(1'b1);
        repeat (10) @(posedge clk);
        set_h(1'b0);
        repeat (1) @(posedge clk);
        set_l(1'b1);
        repeat (8) @(posedge clk);

        if (!dead_fault) begin
            $display("ERROR: short deadtime did not latch violation");
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_pwm_complementary_monitor");
            $finish;
        end

        $display("FAIL: tb_pwm_complementary_monitor errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
