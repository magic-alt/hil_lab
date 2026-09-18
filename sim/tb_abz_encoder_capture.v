`timescale 1ns/1ps
`default_nettype none

module tb_abz_encoder_capture;

    reg clk;
    reg rst_n;
    reg enable;
    reg direction_forward;
    reg [63:0] timestamp;

    wire enc_a;
    wire enc_b;
    wire enc_z;
    wire [31:0] generated_position;

    wire [31:0] captured_position;
    wire captured_direction;
    wire step_pulse;
    wire index_pulse;
    wire illegal_transition;
    wire [63:0] last_edge_timestamp;

    abz_encoder_emulator #(.COUNTS_PER_REV(32)) gen (
        .clk(clk), .rst_n(rst_n), .enable(enable),
        .direction_forward(direction_forward),
        .step_period_ticks(32'd4),
        .enc_a(enc_a), .enc_b(enc_b), .enc_z(enc_z),
        .position_edges(generated_position)
    );

    abz_encoder_capture cap (
        .clk(clk), .rst_n(rst_n),
        .enc_a_async(enc_a), .enc_b_async(enc_b), .enc_z_async(enc_z),
        .timestamp(timestamp), .clear_faults(1'b0),
        .position_edges(captured_position),
        .direction_forward(captured_direction),
        .step_pulse(step_pulse), .index_pulse(index_pulse),
        .illegal_transition_latched(illegal_transition),
        .last_edge_timestamp(last_edge_timestamp)
    );

    always #5 clk = ~clk;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            timestamp <= 64'd0;
        else
            timestamp <= timestamp + 64'd1;
    end

    initial begin
        clk = 1'b0;
        rst_n = 1'b0;
        enable = 1'b0;
        direction_forward = 1'b1;
        timestamp = 64'd0;

        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        enable = 1'b1;

        repeat (90) @(posedge clk);

        if (illegal_transition) begin
            $display("FAIL: nominal ABZ produced illegal transition");
            $fatal;
        end

        if (captured_position < 32'd15) begin
            $display("FAIL: captured too few forward edges: %0d", captured_position);
            $fatal;
        end

        direction_forward = 1'b0;
        repeat (40) @(posedge clk);

        if (captured_direction !== 1'b0) begin
            $display("FAIL: reverse direction not detected");
            $fatal;
        end

        if (illegal_transition) begin
            $display("FAIL: reverse ABZ produced illegal transition");
            $fatal;
        end

        $display("PASS: ABZ generator/capture loopback");
        $finish;
    end

endmodule

`default_nettype wire
