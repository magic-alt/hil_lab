`timescale 1ns/1ps
`default_nettype none

module tb_dac_eval_pattern_generator;
    reg [1:0] pattern_select;
    wire [15:0] ch0;
    wire [15:0] ch1;
    wire [15:0] ch2;
    wire [15:0] ch3;
    integer errors = 0;

    dac_eval_pattern_generator dut (
        .pattern_select(pattern_select),
        .ch0_code(ch0),
        .ch1_code(ch1),
        .ch2_code(ch2),
        .ch3_code(ch3)
    );

    task expect_codes;
        input [1:0] select_value;
        input [15:0] e0;
        input [15:0] e1;
        input [15:0] e2;
        input [15:0] e3;
        begin
            pattern_select = select_value;
            #1;
            if (ch0 !== e0 || ch1 !== e1 || ch2 !== e2 || ch3 !== e3) begin
                $display("ERROR: select=%b got %04x/%04x/%04x/%04x expected %04x/%04x/%04x/%04x",
                         select_value, ch0, ch1, ch2, ch3, e0, e1, e2, e3);
                errors = errors + 1;
            end
        end
    endtask

    initial begin
        expect_codes(2'b00, 16'h0CCD, 16'h547B, 16'h9999, 16'hA8F5);
        expect_codes(2'b01, 16'h547B, 16'h9999, 16'hA8F5, 16'h0CCD);
        expect_codes(2'b10, 16'h9999, 16'hA8F5, 16'h0CCD, 16'h547B);
        expect_codes(2'b11, 16'hA8F5, 16'h0CCD, 16'h547B, 16'h9999);

        if (errors == 0)
            $display("PASS: tb_dac_eval_pattern_generator");
        else
            $display("FAIL: tb_dac_eval_pattern_generator errors=%0d", errors);
        $finish;
    end
endmodule

`default_nettype wire
