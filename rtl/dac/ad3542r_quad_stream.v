`default_nettype none

// Four-channel signal-level DAC path using two AD3542R devices in parallel.
//
// Both devices share CS/SCLK and receive independent SDIO0/MOSI data.  Each
// AD3542R carries two channels, so one 32-bit stream group updates four HIL
// analog values across the two devices.  This module intentionally implements
// the write-only G1 evaluation path; readback/ALERT diagnostics are added after
// the physical P5 level-shifter interposer is qualified.
module ad3542r_quad_stream #(
    parameter [31:0] STARTUP_DELAY_CYCLES = 32'd1000000,
    parameter [7:0] OUTPUT_RANGE_CONFIG = 8'h11,
    parameter [15:0] SAFE_CODE = 16'h0000
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        enable,
    input  wire        force_safe,

    input  wire [15:0] ch0_code,
    input  wire [15:0] ch1_code,
    input  wire [15:0] ch2_code,
    input  wire [15:0] ch3_code,
    input  wire        sample_valid,
    output wire        sample_ready,
    output reg         sample_accepted_pulse,
    output reg         sample_update_pulse,

    output reg         dac_sclk,
    output reg         dac_cs_n,
    output reg         dac_sdio0_a,
    output reg         dac_sdio0_b,
    output reg         dac_reset_n,
    output wire        dac_ldac_n,
    output wire        dac_output_enable,

    output reg         initialized,
    output reg         stream_active
);

    localparam [2:0] ST_DELAY        = 3'd0;
    localparam [2:0] ST_CFG_START    = 3'd1;
    localparam [2:0] ST_CFG_SHIFT    = 3'd2;
    localparam [2:0] ST_CFG_GAP      = 3'd3;
    localparam [2:0] ST_WAIT_SAMPLE  = 3'd4;
    localparam [2:0] ST_STREAM_INSTR = 3'd5;
    localparam [2:0] ST_STREAM_DATA  = 3'd6;

    reg [2:0] state;
    reg [1:0] config_index;
    reg [31:0] startup_count;
    reg [5:0] bits_remaining;
    reg [31:0] shift_a;
    reg [31:0] shift_b;

    reg [15:0] active_ch0;
    reg [15:0] active_ch1;
    reg [15:0] active_ch2;
    reg [15:0] active_ch3;

    reg [15:0] pending_ch0;
    reg [15:0] pending_ch1;
    reg [15:0] pending_ch2;
    reg [15:0] pending_ch3;
    reg        pending_valid;

    wire [31:0] active_word_a;
    wire [31:0] active_word_b;
    wire [31:0] pending_word_a;
    wire [31:0] pending_word_b;
    wire [31:0] safe_word;
    wire [15:0] config_current;

    function [15:0] config_word;
        input [1:0] index;
        begin
            case (index)
                // STREAM_MODE = 4 bytes: CH1[15:8], CH1[7:0],
                // CH0[15:8], CH0[7:0], then loop.
                2'd0: config_word = 16'h0E04;
                // Keep the stream loop length while continuously writing.
                2'd1: config_word = 16'h0F04;
                // Both channels: 0 V to 5 V range (0x1 per channel).
                2'd2: config_word = {8'h19, OUTPUT_RANGE_CONFIG};
                default: config_word = 16'h0000;
            endcase
        end
    endfunction

    assign config_current = config_word(config_index);
    assign active_word_a  = {active_ch1, active_ch0};
    assign active_word_b  = {active_ch3, active_ch2};
    assign pending_word_a = {pending_ch1, pending_ch0};
    assign pending_word_b = {pending_ch3, pending_ch2};
    assign safe_word      = {SAFE_CODE, SAFE_CODE};

    assign sample_ready = initialized & ~pending_valid & ~force_safe;
    assign dac_ldac_n = 1'b1;

    // This signal is intended to control an external analog-output switch on
    // the G1 interposer.  SPI zero-code streaming alone is not treated as the
    // independent hardware safety mechanism.
    assign dac_output_enable = initialized & stream_active & enable & ~force_safe;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state                 <= ST_DELAY;
            config_index          <= 2'd0;
            startup_count         <= 32'd0;
            bits_remaining        <= 6'd0;
            shift_a               <= 32'd0;
            shift_b               <= 32'd0;
            active_ch0             <= SAFE_CODE;
            active_ch1             <= SAFE_CODE;
            active_ch2             <= SAFE_CODE;
            active_ch3             <= SAFE_CODE;
            pending_ch0            <= SAFE_CODE;
            pending_ch1            <= SAFE_CODE;
            pending_ch2            <= SAFE_CODE;
            pending_ch3            <= SAFE_CODE;
            pending_valid          <= 1'b0;
            sample_accepted_pulse <= 1'b0;
            sample_update_pulse   <= 1'b0;
            dac_sclk               <= 1'b0;
            dac_cs_n               <= 1'b1;
            dac_sdio0_a            <= 1'b0;
            dac_sdio0_b            <= 1'b0;
            dac_reset_n            <= 1'b0;
            initialized            <= 1'b0;
            stream_active          <= 1'b0;
        end else begin
            sample_accepted_pulse <= 1'b0;
            sample_update_pulse   <= 1'b0;
            dac_reset_n           <= 1'b1;

            if (sample_valid && sample_ready) begin
                pending_ch0            <= ch0_code;
                pending_ch1            <= ch1_code;
                pending_ch2            <= ch2_code;
                pending_ch3            <= ch3_code;
                pending_valid          <= 1'b1;
                sample_accepted_pulse <= 1'b1;
            end

            if (force_safe)
                pending_valid <= 1'b0;

            case (state)
                ST_DELAY: begin
                    dac_cs_n <= 1'b1;
                    dac_sclk <= 1'b0;
                    if ((STARTUP_DELAY_CYCLES == 32'd0) ||
                        (startup_count >= (STARTUP_DELAY_CYCLES - 32'd1))) begin
                        startup_count <= 32'd0;
                        config_index <= 2'd0;
                        state <= ST_CFG_START;
                    end else begin
                        startup_count <= startup_count + 32'd1;
                    end
                end

                ST_CFG_START: begin
                    dac_cs_n <= 1'b0;
                    dac_sclk <= 1'b0;
                    shift_a <= {config_current, 16'd0};
                    shift_b <= {config_current, 16'd0};
                    bits_remaining <= 6'd16;
                    dac_sdio0_a <= config_current[15];
                    dac_sdio0_b <= config_current[15];
                    state <= ST_CFG_SHIFT;
                end

                ST_CFG_SHIFT: begin
                    if (!dac_sclk) begin
                        dac_sclk <= 1'b1;
                    end else begin
                        dac_sclk <= 1'b0;
                        if (bits_remaining > 6'd1) begin
                            shift_a <= {shift_a[30:0], 1'b0};
                            shift_b <= {shift_b[30:0], 1'b0};
                            dac_sdio0_a <= shift_a[30];
                            dac_sdio0_b <= shift_b[30];
                            bits_remaining <= bits_remaining - 6'd1;
                        end else begin
                            bits_remaining <= 6'd0;
                            dac_cs_n <= 1'b1;
                            dac_sdio0_a <= 1'b0;
                            dac_sdio0_b <= 1'b0;
                            state <= ST_CFG_GAP;
                        end
                    end
                end

                ST_CFG_GAP: begin
                    dac_cs_n <= 1'b1;
                    dac_sclk <= 1'b0;
                    if (config_index < 2'd2) begin
                        config_index <= config_index + 2'd1;
                        state <= ST_CFG_START;
                    end else begin
                        initialized <= 1'b1;
                        state <= ST_WAIT_SAMPLE;
                    end
                end

                ST_WAIT_SAMPLE: begin
                    dac_cs_n <= 1'b1;
                    dac_sclk <= 1'b0;
                    if (pending_valid) begin
                        active_ch0 <= pending_ch0;
                        active_ch1 <= pending_ch1;
                        active_ch2 <= pending_ch2;
                        active_ch3 <= pending_ch3;
                        pending_valid <= 1'b0;

                        // Write instruction: R/W=0 and 7-bit address 0x2C
                        // (CH1_DAC_16B MSB).  With descending addressing and
                        // STREAM_MODE=4, data loops 0x2C..0x29.
                        shift_a <= {8'h2C, 24'd0};
                        shift_b <= {8'h2C, 24'd0};
                        bits_remaining <= 6'd8;
                        dac_sdio0_a <= 1'b0;
                        dac_sdio0_b <= 1'b0;
                        dac_cs_n <= 1'b0;
                        stream_active <= 1'b1;
                        state <= ST_STREAM_INSTR;
                    end
                end

                ST_STREAM_INSTR: begin
                    if (!dac_sclk) begin
                        dac_sclk <= 1'b1;
                    end else begin
                        dac_sclk <= 1'b0;
                        if (bits_remaining > 6'd1) begin
                            shift_a <= {shift_a[30:0], 1'b0};
                            shift_b <= {shift_b[30:0], 1'b0};
                            dac_sdio0_a <= shift_a[30];
                            dac_sdio0_b <= shift_b[30];
                            bits_remaining <= bits_remaining - 6'd1;
                        end else begin
                            bits_remaining <= 6'd32;
                            if (force_safe || !enable) begin
                                shift_a <= safe_word;
                                shift_b <= safe_word;
                                dac_sdio0_a <= safe_word[31];
                                dac_sdio0_b <= safe_word[31];
                            end else begin
                                shift_a <= active_word_a;
                                shift_b <= active_word_b;
                                dac_sdio0_a <= active_word_a[31];
                                dac_sdio0_b <= active_word_b[31];
                            end
                            state <= ST_STREAM_DATA;
                        end
                    end
                end

                ST_STREAM_DATA: begin
                    // CS intentionally remains low for the unlimited stream.
                    dac_cs_n <= 1'b0;
                    if (!dac_sclk) begin
                        dac_sclk <= 1'b1;
                    end else begin
                        dac_sclk <= 1'b0;
                        if (bits_remaining > 6'd1) begin
                            shift_a <= {shift_a[30:0], 1'b0};
                            shift_b <= {shift_b[30:0], 1'b0};
                            dac_sdio0_a <= shift_a[30];
                            dac_sdio0_b <= shift_b[30];
                            bits_remaining <= bits_remaining - 6'd1;
                        end else begin
                            bits_remaining <= 6'd32;
                            sample_update_pulse <= 1'b1;

                            if (force_safe || !enable) begin
                                active_ch0 <= SAFE_CODE;
                                active_ch1 <= SAFE_CODE;
                                active_ch2 <= SAFE_CODE;
                                active_ch3 <= SAFE_CODE;
                                shift_a <= safe_word;
                                shift_b <= safe_word;
                                dac_sdio0_a <= safe_word[31];
                                dac_sdio0_b <= safe_word[31];
                            end else if (pending_valid) begin
                                active_ch0 <= pending_ch0;
                                active_ch1 <= pending_ch1;
                                active_ch2 <= pending_ch2;
                                active_ch3 <= pending_ch3;
                                pending_valid <= 1'b0;
                                shift_a <= pending_word_a;
                                shift_b <= pending_word_b;
                                dac_sdio0_a <= pending_word_a[31];
                                dac_sdio0_b <= pending_word_b[31];
                            end else begin
                                shift_a <= active_word_a;
                                shift_b <= active_word_b;
                                dac_sdio0_a <= active_word_a[31];
                                dac_sdio0_b <= active_word_b[31];
                            end
                        end
                    end
                end

                default: begin
                    state <= ST_DELAY;
                    initialized <= 1'b0;
                    stream_active <= 1'b0;
                    dac_cs_n <= 1'b1;
                    dac_sclk <= 1'b0;
                end
            endcase
        end
    end

endmodule

`default_nettype wire
