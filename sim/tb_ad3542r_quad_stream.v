`timescale 1ns/1ps
`default_nettype none

module tb_ad3542r_quad_stream;

    reg clk = 1'b0;
    reg rst_n = 1'b0;
    reg enable = 1'b1;
    reg force_safe = 1'b0;
    reg [15:0] ch0 = 16'h1111;
    reg [15:0] ch1 = 16'h2222;
    reg [15:0] ch2 = 16'h3333;
    reg [15:0] ch3 = 16'h4444;
    reg sample_valid = 1'b0;

    wire sample_ready;
    wire sample_accepted;
    wire sample_update;
    wire sclk;
    wire cs_n;
    wire mosi_a;
    wire mosi_b;
    wire dac_reset_n;
    wire ldac_n;
    wire output_enable;
    wire initialized;
    wire stream_active;

    reg [7:0] byte_a;
    reg [7:0] byte_b;
    reg [7:0] frame_bytes_a [0:7];
    reg [7:0] frame_bytes_b [0:7];
    integer bit_count;
    integer byte_count;
    integer errors = 0;
    integer update_count = 0;

    ad3542r_quad_stream #(
        .STARTUP_DELAY_CYCLES(8)
    ) dut (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .force_safe(force_safe),
        .ch0_code(ch0),
        .ch1_code(ch1),
        .ch2_code(ch2),
        .ch3_code(ch3),
        .sample_valid(sample_valid),
        .sample_ready(sample_ready),
        .sample_accepted_pulse(sample_accepted),
        .sample_update_pulse(sample_update),
        .dac_sclk(sclk),
        .dac_cs_n(cs_n),
        .dac_sdio0_a(mosi_a),
        .dac_sdio0_b(mosi_b),
        .dac_reset_n(dac_reset_n),
        .dac_ldac_n(ldac_n),
        .dac_output_enable(output_enable),
        .initialized(initialized),
        .stream_active(stream_active)
    );

    always #5 clk = ~clk;

    always @(posedge clk) begin
        if (sample_update)
            update_count = update_count + 1;
    end

    task capture_bytes_from_cs_fall;
        input integer expected_bytes;
        begin
            byte_count = 0;
            bit_count = 0;
            byte_a = 8'h00;
            byte_b = 8'h00;
            @(negedge cs_n);
            while (byte_count < expected_bytes) begin
                @(posedge sclk);
                byte_a = {byte_a[6:0], mosi_a};
                byte_b = {byte_b[6:0], mosi_b};
                bit_count = bit_count + 1;
                if (bit_count == 8) begin
                    frame_bytes_a[byte_count] = byte_a;
                    frame_bytes_b[byte_count] = byte_b;
                    byte_count = byte_count + 1;
                    bit_count = 0;
                    byte_a = 8'h00;
                    byte_b = 8'h00;
                end
            end
        end
    endtask

    task expect_config;
        input [15:0] expected_word;
        begin
            capture_bytes_from_cs_fall(2);
            if ({frame_bytes_a[0], frame_bytes_a[1]} !== expected_word ||
                {frame_bytes_b[0], frame_bytes_b[1]} !== expected_word) begin
                $display("ERROR: config got A=%02x%02x B=%02x%02x expected=%04x",
                         frame_bytes_a[0], frame_bytes_a[1],
                         frame_bytes_b[0], frame_bytes_b[1], expected_word);
                errors = errors + 1;
            end
            wait (cs_n === 1'b1);
        end
    endtask

    task submit_current_sample;
        begin
            wait (sample_ready === 1'b1);
            @(negedge clk);
            sample_valid = 1'b1;
            @(negedge clk);
            if (sample_accepted !== 1'b1) begin
                $display("ERROR: sample was not accepted while ready");
                errors = errors + 1;
            end
            sample_valid = 1'b0;
        end
    endtask

    initial begin
        $dumpfile("build/tb_ad3542r_quad_stream.vcd");
        $dumpvars(0, tb_ad3542r_quad_stream);

        repeat (5) @(posedge clk);
        rst_n = 1'b1;

        expect_config(16'h0E04);
        expect_config(16'h0F04);
        expect_config(16'h1911);

        wait (initialized === 1'b1);
        if (dac_reset_n !== 1'b1 || ldac_n !== 1'b1) begin
            $display("ERROR: DAC reset/LDAC state reset_n=%b ldac_n=%b",
                     dac_reset_n, ldac_n);
            errors = errors + 1;
        end

        fork
            begin
                capture_bytes_from_cs_fall(5);
            end
            begin
                submit_current_sample();
            end
        join

        if (frame_bytes_a[0] !== 8'h2C ||
            frame_bytes_a[1] !== 8'h22 || frame_bytes_a[2] !== 8'h22 ||
            frame_bytes_a[3] !== 8'h11 || frame_bytes_a[4] !== 8'h11) begin
            $display("ERROR: stream A bytes %02x %02x %02x %02x %02x",
                     frame_bytes_a[0], frame_bytes_a[1], frame_bytes_a[2],
                     frame_bytes_a[3], frame_bytes_a[4]);
            errors = errors + 1;
        end
        if (frame_bytes_b[0] !== 8'h2C ||
            frame_bytes_b[1] !== 8'h44 || frame_bytes_b[2] !== 8'h44 ||
            frame_bytes_b[3] !== 8'h33 || frame_bytes_b[4] !== 8'h33) begin
            $display("ERROR: stream B bytes %02x %02x %02x %02x %02x",
                     frame_bytes_b[0], frame_bytes_b[1], frame_bytes_b[2],
                     frame_bytes_b[3], frame_bytes_b[4]);
            errors = errors + 1;
        end

        repeat (4) @(posedge clk);
        if (!stream_active || !output_enable || ldac_n !== 1'b1) begin
            $display("ERROR: stream/output status active=%b output_enable=%b ldac=%b",
                     stream_active, output_enable, ldac_n);
            errors = errors + 1;
        end
        if (update_count < 1) begin
            $display("ERROR: no completed DAC vector was reported");
            errors = errors + 1;
        end

        @(negedge clk);
        force_safe = 1'b1;
        #1;
        if (output_enable !== 1'b0 || sample_ready !== 1'b0) begin
            $display("ERROR: FORCE_SAFE did not disable analog-output seam");
            errors = errors + 1;
        end

        repeat (80) @(posedge clk);
        force_safe = 1'b0;
        wait (sample_ready === 1'b1);

        ch0 = 16'h5555;
        ch1 = 16'h6666;
        ch2 = 16'h7777;
        ch3 = 16'h8888;
        submit_current_sample();

        @(negedge clk);
        enable = 1'b0;
        #1;
        if (output_enable !== 1'b0) begin
            $display("ERROR: enable=0 did not disable analog-output seam");
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: tb_ad3542r_quad_stream");
        else
            $display("FAIL: tb_ad3542r_quad_stream errors=%0d", errors);

        $finish;
    end

endmodule

`default_nettype wire
