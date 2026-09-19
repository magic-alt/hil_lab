`timescale 1ns/1ps
`default_nettype none

module tb_hil_event_queue;

    reg clk;
    reg rst_n;
    reg clear_queue;
    reg clear_errors;
    reg push;
    reg pop;
    reg [63:0] push_timestamp;
    reg [7:0] push_mask;
    reg [7:0] push_value;
    reg [7:0] push_event_id;

    wire [63:0] head_timestamp;
    wire [7:0] head_mask;
    wire [7:0] head_value;
    wire [7:0] head_event_id;
    wire empty;
    wire full;
    wire [15:0] level;
    wire overflow_latched;
    wire order_error_latched;

    integer errors;

    hil_event_queue #(
        .WIDTH(8),
        .ID_WIDTH(8),
        .DEPTH(3)
    ) u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .clear_queue(clear_queue),
        .clear_errors(clear_errors),
        .push(push),
        .push_timestamp(push_timestamp),
        .push_mask(push_mask),
        .push_value(push_value),
        .push_event_id(push_event_id),
        .pop(pop),
        .head_timestamp(head_timestamp),
        .head_mask(head_mask),
        .head_value(head_value),
        .head_event_id(head_event_id),
        .empty(empty),
        .full(full),
        .level(level),
        .overflow_latched(overflow_latched),
        .order_error_latched(order_error_latched)
    );

    always #5 clk = ~clk;

    task push_one;
        input [63:0] ts;
        input [7:0] id;
        begin
            @(negedge clk);
            push_timestamp = ts;
            push_mask = 8'hff;
            push_value = id;
            push_event_id = id;
            push = 1'b1;
            @(negedge clk);
            push = 1'b0;
        end
    endtask

    task pop_one;
        begin
            @(negedge clk);
            pop = 1'b1;
            @(negedge clk);
            pop = 1'b0;
        end
    endtask

    initial begin
        $dumpfile("build/tb_hil_event_queue.vcd");
        $dumpvars(0, tb_hil_event_queue);

        clk = 1'b0;
        rst_n = 1'b0;
        clear_queue = 1'b0;
        clear_errors = 1'b0;
        push = 1'b0;
        pop = 1'b0;
        push_timestamp = 64'd0;
        push_mask = 8'd0;
        push_value = 8'd0;
        push_event_id = 8'd0;
        errors = 0;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;

        push_one(64'd10, 8'd1);
        push_one(64'd20, 8'd2);
        push_one(64'd30, 8'd3);

        if (!full || (level != 16'd3) || (head_event_id != 8'd1)) begin
            $display("ERROR: queue fill state full=%0d level=%0d head=%0d",
                     full, level, head_event_id);
            errors = errors + 1;
        end

        push_one(64'd40, 8'd4);
        if (!overflow_latched || (level != 16'd3)) begin
            $display("ERROR: overflow not latched or count changed");
            errors = errors + 1;
        end

        pop_one();
        if ((level != 16'd2) || (head_event_id != 8'd2)) begin
            $display("ERROR: pop/head order level=%0d head=%0d", level, head_event_id);
            errors = errors + 1;
        end

        @(negedge clk);
        clear_errors = 1'b1;
        @(negedge clk);
        clear_errors = 1'b0;

        push_one(64'd15, 8'd5);
        if (!order_error_latched || (level != 16'd2)) begin
            $display("ERROR: out-of-order event was not rejected");
            errors = errors + 1;
        end

        @(negedge clk);
        clear_queue = 1'b1;
        @(negedge clk);
        clear_queue = 1'b0;
        if (!empty || (level != 16'd0)) begin
            $display("ERROR: clear_queue failed");
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_hil_event_queue");
            $finish;
        end

        $display("FAIL: tb_hil_event_queue errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
