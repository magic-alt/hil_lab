`timescale 1ns/1ps
`default_nettype none

module tb_abz_encoder_emulator;

    reg clk;
    reg rst_n;
    reg enable;
    reg direction_forward;
    reg [31:0] step_period;

    wire enc_a;
    wire enc_b;
    wire enc_z;
    wire [31:0] position_edges;

    reg [1:0] previous_ab;
    integer transition_count;
    integer index_count;
    integer errors;
    integer reverse_start;

    abz_encoder_emulator #(
        .COUNTS_PER_REV(8)
    ) u_dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .direction_forward(direction_forward),
        .step_period_ticks(step_period),
        .enc_a(enc_a),
        .enc_b(enc_b),
        .enc_z(enc_z),
        .position_edges(position_edges)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (rst_n) begin
            if ({enc_a, enc_b} != previous_ab) begin
                transition_count = transition_count + 1;
                previous_ab = {enc_a, enc_b};
            end
            if (enc_z)
                index_count = index_count + 1;
        end
    end

    initial begin
        $dumpfile("build/tb_abz_encoder_emulator.vcd");
        $dumpvars(0, tb_abz_encoder_emulator);

        clk = 1'b0;
        rst_n = 1'b0;
        enable = 1'b0;
        direction_forward = 1'b1;
        step_period = 32'd3;
        previous_ab = 2'b00;
        transition_count = 0;
        index_count = 0;
        errors = 0;
        reverse_start = 0;

        repeat (4) @(posedge clk);
        rst_n = 1'b1;
        enable = 1'b1;

        wait (transition_count >= 8);
        repeat (2) @(posedge clk);

        if (position_edges < 32'd8) begin
            $display("ERROR: forward position_edges=%0d", position_edges);
            errors = errors + 1;
        end
        if (index_count == 0) begin
            $display("ERROR: index pulse was not generated");
            errors = errors + 1;
        end

        reverse_start = position_edges;
        direction_forward = 1'b0;
        repeat (9) @(posedge clk);

        if (position_edges >= reverse_start) begin
            $display("ERROR: reverse direction did not decrement position");
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_abz_encoder_emulator");
            $finish;
        end

        $display("FAIL: tb_abz_encoder_emulator errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
