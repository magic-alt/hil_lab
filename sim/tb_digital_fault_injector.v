`timescale 1ns/1ps
`default_nettype none

module tb_digital_fault_injector;

    reg [7:0] normal_value;
    reg [7:0] force_low_mask;
    reg [7:0] force_high_mask;
    reg [7:0] safe_value;
    reg force_safe;

    wire [7:0] injected_value;
    wire [7:0] active_fault_mask;
    wire [7:0] conflict_mask;

    integer errors;

    digital_fault_injector #(
        .WIDTH(8)
    ) u_dut (
        .normal_value(normal_value),
        .force_low_mask(force_low_mask),
        .force_high_mask(force_high_mask),
        .safe_value(safe_value),
        .force_safe(force_safe),
        .injected_value(injected_value),
        .active_fault_mask(active_fault_mask),
        .conflict_mask(conflict_mask)
    );

    initial begin
        normal_value = 8'h55;
        force_low_mask = 8'h00;
        force_high_mask = 8'h00;
        safe_value = 8'ha5;
        force_safe = 1'b0;
        errors = 0;

        #1;
        if (injected_value != 8'h55)
            errors = errors + 1;

        force_high_mask = 8'h0a;
        #1;
        if (injected_value != 8'h5f)
            errors = errors + 1;

        force_low_mask = 8'h05;
        #1;
        if (injected_value != 8'h5a)
            errors = errors + 1;

        force_high_mask = 8'h0f;
        force_low_mask = 8'h03;
        #1;
        if ((conflict_mask != 8'h03) || (active_fault_mask != 8'h0f) ||
            (injected_value[1:0] != 2'b00)) begin
            $display("ERROR: conflict/priority behavior");
            errors = errors + 1;
        end

        force_safe = 1'b1;
        #1;
        if (injected_value != 8'ha5) begin
            $display("ERROR: force-safe value=%02x", injected_value);
            errors = errors + 1;
        end

        if (errors == 0) begin
            $display("PASS: tb_digital_fault_injector");
            $finish;
        end

        $display("FAIL: tb_digital_fault_injector errors=%0d", errors);
        $fatal(1);
    end

endmodule

`default_nettype wire
