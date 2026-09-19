`timescale 1ns/1ps
`default_nettype none

module tb_dio_scenario_engine;

    reg clk;
    reg rst_n;
    reg enqueue_event;
    reg [63:0] event_timestamp;
    reg [7:0] event_mask;
    reg [7:0] event_value;
    reg [7:0] event_id;
    reg clear_queue;
    reg clear_status;
    reg [7:0] safe_value;
    reg force_safe;

    wire [63:0] timestamp;
    wire [7:0] dio_out;
    wire [15:0] queue_level;
    wire queue_empty;
    wire queue_full;
    wire queue_overflow_latched;
    wire queue_order_error_latched;
    wire event_applied_pulse;
    wire [7:0] applied_event_id;
    wire [63:0] requested_timestamp;
    wire [63:0] actual_timestamp;
    wire [63:0] late_ticks;
    wire late_event_latched;

    integer errors;
    reg [63:0] first_target;
    reg [63:0] second_target;

    hil_timebase u_time (
        .clk(clk),
        .rst_n(rst_n),
        .timestamp(timestamp)
    );

    dio_scenario_engine #(
        .WIDTH(8),
        .ID_WIDTH(8),
        .QUEUE_DEPTH(4)
    ) u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .timestamp(timestamp),
        .enqueue_event(enqueue_event),
        .event_timestamp(event_timestamp),
        .event_mask(event_mask),
        .event_value(event_value),
        .event_id(event_id),
        .clear_queue(clear_queue),
        .clear_status(clear_status),
        .safe_value(safe_value),
        .force_safe(force_safe),
        .dio_out(dio_out),
        .queue_level(queue_level),
        .queue_empty(queue_empty),
        .queue_full(queue_full),
        .queue_overflow_latched(queue_overflow_latched),
        .queue_order_error_latched(queue_order_error_latched),
        .event_applied_pulse(event_applied_pulse),
        .applied_event_id(applied_event_id),
        .requested_timestamp(requested_timestamp),
        .actual_timestamp(actual_timestamp),
        .late_ticks(late_ticks),
        .late_event_latched(late_event_latched)
    );

    always #5 clk = ~clk;

    task enqueue_one;
        input [63:0] ts;
        input [7:0] mask;
        input [7:0] value;
        input [7:0] id;
        begin
            @(negedge clk);
            event_timestamp = ts;
            event_mask = mask;
            event_value = value;
            event_id = id;
            enqueue_event = 1'b1;
            @(negedge clk);
            enqueue_event = 1'b0;
        end
    endtask

    initial begin
        $dumpfile("build/tb_dio_scenario_engine.vcd");
        $dumpvars(0, tb_dio_scenario_engine);

        clk = 1'b0;
        rst_n = 1'b0;
        enqueue_event = 1'b0;
        event_timestamp = 64'd0;
        event_mask = 8'd0;
        event_value = 8'd0;
        event_id = 8'd0;
        clear_queue = 1'b0;
        clear_status = 1'b0;
        safe_value = 8'h5a;
        force_safe = 1'b0;
        errors = 0;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        repeat (3) @(posedge clk);

        first_target = timestamp + 64'd30;
        second_target = timestamp + 64'd50;
        enqueue_one(first_target, 8'h0f, 8'h05, 8'd1);
        enqueue_one(second_target, 8'hf0, 8'ha0, 8'd2);

        wait (event_applied_pulse == 1'b1);
        if ((applied_event_id != 8'd1) || (dio_out != 8'h05)) begin
            $display("ERROR: first event id=%0d dio=%02x", applied_event_id, dio_out);
            errors = errors + 1;
        end

        @(negedge clk);
        wait (event_applied_pulse == 1'b1);
        if ((applied_event_id != 8'd2) || (dio_out != 8'ha5)) begin
            $display("ERROR: second event id=%0d dio=%02x", applied_event_id, dio_out);
            errors = errors + 1;
        end

        enqueue_one(timestamp + 64'd100, 8'hff, 8'hff, 8'd3);
        @(negedge clk);
        force_safe = 1'b1;
        @(posedge clk);
        #1;
        if ((dio_out != 8'h5a) || !queue_empty) begin
            $display("ERROR: FORCE_SAFE did not force value/flush queue dio=%02x empty=%0d",
                     dio_out, queue_empty);
            errors = errors + 1;
        end
        @(negedge clk);
        force_safe = 1'b0;

        @(negedge clk);
        clear_status = 1'b1;
        @(negedge clk);
        clear_status = 1'b0;
        enqueue_one(timestamp - 64'd2, 8'h03, 8'h03, 8'd4);

        wait (event_applied_pulse == 1'b1);
        if ((applied_event_id != 8'd4) || !late_event_latched || (late_ticks == 64'd0)) begin
            $display("ERROR: late-event evidence missing id=%0d late=%0d ticks=%0d",
                     applied_event_id, late_event_latched, late_ticks);
            errors = errors + 1;
        end

        if (queue_overflow_latched || queue_order_error_latched || queue_full) begin
            $display("ERROR: unexpected queue status");
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_dio_scenario_engine");
            $finish;
        end

        $display("FAIL: tb_dio_scenario_engine errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
