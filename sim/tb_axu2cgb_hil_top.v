`timescale 1ns/1ps
`default_nettype none

module tb_axu2cgb_hil_top;

    reg clk = 1'b0;
    reg [2:0] pwm_high = 3'b000;
    reg [2:0] pwm_low = 3'b000;
    reg spi_sclk = 1'b0;
    reg spi_cs_n = 1'b1;
    reg spi_mosi = 1'b0;
    reg ext_reset_n = 1'b0;
    reg hil_enable = 1'b0;
    reg encoder_direction = 1'b1;
    reg clear_faults = 1'b0;
    reg force_safe = 1'b1;
    reg test_pattern_enable = 1'b0;

    wire enc_a;
    wire enc_b;
    wire enc_z;
    wire spi_miso;
    wire [15:0] dio;
    wire [3:0] status;
    wire [3:0] led_n;

    reg [23:0] spi_rx;
    reg encoder_changed;
    integer bit_index;
    integer errors = 0;

    axu2cgb_hil_top #(
        .ENCODER_COUNTS_PER_REV(16),
        .ENCODER_STEP_PERIOD_TICKS(4),
        .SPI_FRAME_BITS(24),
        .SPI_FRAME_DATA(24'hA55A3C),
        .MIN_DEADTIME_TICKS(2)
    ) dut (
        .pl_ref_clk(clk),
        .pwm_high_in(pwm_high),
        .pwm_low_in(pwm_low),
        .spi_sclk_in(spi_sclk),
        .spi_cs_n_in(spi_cs_n),
        .spi_mosi_in(spi_mosi),
        .ext_reset_n(ext_reset_n),
        .hil_enable_in(hil_enable),
        .encoder_direction_in(encoder_direction),
        .clear_faults_in(clear_faults),
        .force_safe_in(force_safe),
        .test_pattern_enable_in(test_pattern_enable),
        .enc_a_out(enc_a),
        .enc_b_out(enc_b),
        .enc_z_out(enc_z),
        .spi_miso_out(spi_miso),
        .dio_out(dio),
        .status_out(status),
        .led_n(led_n)
    );

    // HIL_SIMULATION bypasses the physical 25 -> 100 MHz MMCM, so the testbench
    // directly drives a 100 MHz logical HIL clock.
    always #5 clk = ~clk;

    task spi_transfer_24;
        input [23:0] tx_word;
        output [23:0] rx_word;
        begin
            rx_word = 24'd0;
            spi_sclk = 1'b0;
            spi_cs_n = 1'b0;
            repeat (12) @(posedge clk);

            for (bit_index = 23; bit_index >= 0; bit_index = bit_index - 1) begin
                spi_mosi = tx_word[bit_index];
                repeat (10) @(posedge clk);
                spi_sclk = 1'b1;
                repeat (4) @(posedge clk);
                rx_word[bit_index] = spi_miso;
                repeat (6) @(posedge clk);
                spi_sclk = 1'b0;
                repeat (10) @(posedge clk);
            end

            spi_cs_n = 1'b1;
            spi_mosi = 1'b0;
            repeat (12) @(posedge clk);
        end
    endtask

    task make_pwm_period;
        begin
            pwm_high[0] = 1'b1;
            pwm_low[0]  = 1'b0;
            repeat (20) @(posedge clk);
            pwm_high[0] = 1'b0;
            repeat (4) @(posedge clk);
            pwm_low[0] = 1'b1;
            repeat (20) @(posedge clk);
            pwm_low[0] = 1'b0;
            repeat (4) @(posedge clk);
        end
    endtask

    initial begin
        $dumpfile("build/tb_axu2cgb_hil_top.vcd");
        $dumpvars(0, tb_axu2cgb_hil_top);

        repeat (8) @(posedge clk);
        ext_reset_n = 1'b1;
        repeat (10) @(posedge clk);

        if (status[0] !== 1'b1 || status[1] !== 1'b1) begin
            $display("ERROR: clock/reset status=%b expected xx11", status);
            errors = errors + 1;
        end

        if (dio !== 16'h0000 || enc_a !== 1'b0 || enc_b !== 1'b0 || spi_miso !== 1'b0) begin
            $display("ERROR: outputs not safe while disabled");
            errors = errors + 1;
        end

        hil_enable = 1'b1;
        force_safe = 1'b0;
        test_pattern_enable = 1'b1;
        repeat (8) @(posedge clk);

        if (dio !== 16'hA55A) begin
            $display("ERROR: test pattern dio=%04x expected=A55A", dio);
            errors = errors + 1;
        end

        encoder_changed = 1'b0;
        repeat (24) begin
            @(posedge clk);
            if ((enc_a !== 1'b0) || (enc_b !== 1'b0))
                encoder_changed = 1'b1;
        end
        if (!encoder_changed) begin
            $display("ERROR: ABZ emulator did not advance after enable");
            errors = errors + 1;
        end

        spi_transfer_24(24'h123456, spi_rx);
        if (spi_rx !== 24'hA55A3C) begin
            $display("ERROR: SPI frame=%06x expected=A55A3C", spi_rx);
            errors = errors + 1;
        end

        make_pwm_period();
        make_pwm_period();
        make_pwm_period();
        repeat (8) @(posedge clk);
        if (status[2] !== 1'b1 || led_n[1] !== 1'b0) begin
            $display("ERROR: PWM-seen latch/LED did not assert status=%b led_n=%b", status, led_n);
            errors = errors + 1;
        end

        // Intentional phase-U shoot-through command should latch a fault.
        pwm_high[0] = 1'b1;
        pwm_low[0]  = 1'b1;
        repeat (8) @(posedge clk);
        pwm_high[0] = 1'b0;
        pwm_low[0]  = 1'b0;
        repeat (8) @(posedge clk);
        if (status[3] !== 1'b1 || led_n[2] !== 1'b0) begin
            $display("ERROR: shoot-through fault did not latch status=%b led_n=%b", status, led_n);
            errors = errors + 1;
        end

        clear_faults = 1'b1;
        repeat (8) @(posedge clk);
        clear_faults = 1'b0;
        repeat (8) @(posedge clk);
        if (status[3] !== 1'b0) begin
            $display("ERROR: fault did not clear status=%b", status);
            errors = errors + 1;
        end

        force_safe = 1'b1;
        repeat (8) @(posedge clk);
        if (dio !== 16'h0000 || enc_a !== 1'b0 || enc_b !== 1'b0 || spi_miso !== 1'b0) begin
            $display("ERROR: FORCE_SAFE did not suppress physical outputs");
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: tb_axu2cgb_hil_top");
        else
            $display("FAIL: tb_axu2cgb_hil_top errors=%0d", errors);

        $finish;
    end

endmodule

`default_nettype wire
