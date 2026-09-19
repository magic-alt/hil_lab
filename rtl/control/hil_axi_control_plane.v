`default_nettype none

module hil_axi_control_plane #(
    parameter ADDR_WIDTH = 12,
    parameter DIO_WIDTH = 16,
    parameter EVENT_ID_WIDTH = 16,
    parameter EVENT_DEPTH = 64,
    parameter [31:0] BACKEND_ID = 32'h00007010,
    parameter [31:0] CAPABILITIES = 32'h00000C37,
    parameter [31:0] TICK_HZ = 32'd100000000,
    parameter [31:0] BUILD_ID = 32'h00000001
) (
    input  wire                     clk,
    input  wire                     rst_n,

    input  wire [ADDR_WIDTH-1:0]    s_axi_awaddr,
    input  wire                     s_axi_awvalid,
    output wire                     s_axi_awready,
    input  wire [31:0]              s_axi_wdata,
    input  wire [3:0]               s_axi_wstrb,
    input  wire                     s_axi_wvalid,
    output wire                     s_axi_wready,
    output reg  [1:0]               s_axi_bresp,
    output reg                      s_axi_bvalid,
    input  wire                     s_axi_bready,

    input  wire [ADDR_WIDTH-1:0]    s_axi_araddr,
    input  wire                     s_axi_arvalid,
    output wire                     s_axi_arready,
    output reg  [31:0]              s_axi_rdata,
    output reg  [1:0]               s_axi_rresp,
    output reg                      s_axi_rvalid,
    input  wire                     s_axi_rready,

    input  wire                     external_force_safe,
    input  wire [63:0]              timestamp,
    input  wire [95:0]              pwm_period_ticks,
    input  wire [95:0]              pwm_high_ticks,
    input  wire [95:0]              pwm_low_ticks,
    input  wire [2:0]               pwm_measurement_valid,
    input  wire [5:0]               pwm_fault_flags,
    input  wire [31:0]              encoder_position_edges,
    input  wire                     dio_event_armed,
    input  wire                     dio_event_done_pulse,

    output reg                      cfg_hil_enable,
    output wire                     cfg_force_safe,
    output reg                      clear_faults_pulse,
    output reg  [31:0]              cfg_min_deadtime_ticks,
    output reg                      cfg_abz_enable,
    output reg                      cfg_abz_direction_forward,
    output reg  [31:0]              cfg_abz_step_period_ticks,

    output reg                      dio_event_arm_pulse,
    output reg  [63:0]              dio_event_timestamp,
    output reg  [DIO_WIDTH-1:0]     dio_event_mask,
    output reg  [DIO_WIDTH-1:0]     dio_event_value,
    output reg  [EVENT_ID_WIDTH-1:0] dio_event_id
);

    localparam [31:0] MAGIC = 32'h48494C32;
    localparam [31:0] ABI_VERSION = 32'h00010000;

    localparam [11:0] REG_MAGIC        = 12'h000;
    localparam [11:0] REG_ABI_VERSION  = 12'h004;
    localparam [11:0] REG_BACKEND_ID   = 12'h008;
    localparam [11:0] REG_CAPABILITIES = 12'h00C;
    localparam [11:0] REG_TICK_HZ      = 12'h010;
    localparam [11:0] REG_COUNTER_BITS = 12'h014;
    localparam [11:0] REG_TIMESTAMP_LO = 12'h018;
    localparam [11:0] REG_TIMESTAMP_HI = 12'h01C;
    localparam [11:0] REG_CONTROL      = 12'h020;
    localparam [11:0] REG_MIN_DEADTIME = 12'h024;
    localparam [11:0] REG_ABZ_STEP     = 12'h028;
    localparam [11:0] REG_BUILD_ID     = 12'h02C;
    localparam [11:0] REG_STATUS       = 12'h030;
    localparam [11:0] REG_PWM_SEQ      = 12'h034;
    localparam [11:0] REG_ENCODER_POS  = 12'h038;

    localparam [11:0] REG_PWM0_PERIOD  = 12'h040;
    localparam [11:0] REG_PWM0_HIGH    = 12'h044;
    localparam [11:0] REG_PWM0_LOW     = 12'h048;
    localparam [11:0] REG_PWM1_PERIOD  = 12'h050;
    localparam [11:0] REG_PWM1_HIGH    = 12'h054;
    localparam [11:0] REG_PWM1_LOW     = 12'h058;
    localparam [11:0] REG_PWM2_PERIOD  = 12'h060;
    localparam [11:0] REG_PWM2_HIGH    = 12'h064;
    localparam [11:0] REG_PWM2_LOW     = 12'h068;
    localparam [11:0] REG_PWM_VALID    = 12'h06C;
    localparam [11:0] REG_PWM_FAULTS   = 12'h070;

    localparam [11:0] REG_EVT_TS_LO    = 12'h100;
    localparam [11:0] REG_EVT_TS_HI    = 12'h104;
    localparam [11:0] REG_EVT_MASK     = 12'h108;
    localparam [11:0] REG_EVT_VALUE    = 12'h10C;
    localparam [11:0] REG_EVT_ID       = 12'h110;
    localparam [11:0] REG_EVT_PUSH     = 12'h114;
    localparam [11:0] REG_EVT_STATUS   = 12'h118;

    reg cfg_force_safe_sw;
    reg [31:0] pwm_sequence;

    reg [63:0] event_stage_timestamp;
    reg [DIO_WIDTH-1:0] event_stage_mask;
    reg [DIO_WIDTH-1:0] event_stage_value;
    reg [EVENT_ID_WIDTH-1:0] event_stage_id;
    reg event_push_pulse;

    wire [63:0] fifo_head_timestamp;
    wire [DIO_WIDTH-1:0] fifo_head_mask;
    wire [DIO_WIDTH-1:0] fifo_head_value;
    wire [EVENT_ID_WIDTH-1:0] fifo_head_id;
    wire fifo_empty;
    wire fifo_full;
    wire [15:0] fifo_level;
    wire fifo_overflow_latched;
    wire fifo_order_error_latched;
    reg fifo_pop;
    reg dispatch_inflight;

    reg aw_pending;
    reg [ADDR_WIDTH-1:0] awaddr_hold;
    reg w_pending;
    reg [31:0] wdata_hold;
    reg [3:0] wstrb_hold;

    wire write_commit;
    wire fifo_clear;
    wire [31:0] control_current;
    wire [31:0] control_write_merged;
    wire [31:0] event_mask_write_merged;
    wire [31:0] event_value_write_merged;
    wire [31:0] event_id_write_merged;

    assign control_current =
        {27'd0, cfg_abz_direction_forward, cfg_abz_enable,
         1'b0, cfg_force_safe_sw, cfg_hil_enable};
    assign control_write_merged =
        apply_wstrb(control_current, wdata_hold, wstrb_hold);
    assign event_mask_write_merged =
        apply_wstrb({{(32-DIO_WIDTH){1'b0}}, event_stage_mask},
                    wdata_hold, wstrb_hold);
    assign event_value_write_merged =
        apply_wstrb({{(32-DIO_WIDTH){1'b0}}, event_stage_value},
                    wdata_hold, wstrb_hold);
    assign event_id_write_merged =
        apply_wstrb({{(32-EVENT_ID_WIDTH){1'b0}}, event_stage_id},
                    wdata_hold, wstrb_hold);

    assign cfg_force_safe = cfg_force_safe_sw | external_force_safe;
    assign fifo_clear = cfg_force_safe;
    assign s_axi_awready = !aw_pending;
    assign s_axi_wready = !w_pending;
    assign s_axi_arready = !s_axi_rvalid;
    assign write_commit = aw_pending && w_pending && !s_axi_bvalid;

    function [31:0] apply_wstrb;
        input [31:0] old_value;
        input [31:0] new_value;
        input [3:0] strb;
        integer i;
        begin
            apply_wstrb = old_value;
            for (i = 0; i < 4; i = i + 1)
                if (strb[i])
                    apply_wstrb[i*8 +: 8] = new_value[i*8 +: 8];
        end
    endfunction

    hil_axi_event_fifo #(
        .WIDTH(DIO_WIDTH),
        .ID_WIDTH(EVENT_ID_WIDTH),
        .DEPTH(EVENT_DEPTH)
    ) u_event_fifo (
        .clk(clk),
        .rst_n(rst_n),
        .clear(fifo_clear),
        .push(event_push_pulse),
        .push_timestamp(event_stage_timestamp),
        .push_mask(event_stage_mask),
        .push_value(event_stage_value),
        .push_id(event_stage_id),
        .pop(fifo_pop),
        .head_timestamp(fifo_head_timestamp),
        .head_mask(fifo_head_mask),
        .head_value(fifo_head_value),
        .head_id(fifo_head_id),
        .empty(fifo_empty),
        .full(fifo_full),
        .level(fifo_level),
        .overflow_latched(fifo_overflow_latched),
        .order_error_latched(fifo_order_error_latched)
    );

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            aw_pending <= 1'b0;
            awaddr_hold <= {ADDR_WIDTH{1'b0}};
            w_pending <= 1'b0;
            wdata_hold <= 32'd0;
            wstrb_hold <= 4'd0;
            s_axi_bvalid <= 1'b0;
            s_axi_bresp <= 2'b00;

            cfg_hil_enable <= 1'b0;
            cfg_force_safe_sw <= 1'b1;
            clear_faults_pulse <= 1'b0;
            cfg_min_deadtime_ticks <= 32'd80;
            cfg_abz_enable <= 1'b0;
            cfg_abz_direction_forward <= 1'b1;
            cfg_abz_step_period_ticks <= 32'd1000;
            pwm_sequence <= 32'd0;

            event_stage_timestamp <= 64'd0;
            event_stage_mask <= {DIO_WIDTH{1'b0}};
            event_stage_value <= {DIO_WIDTH{1'b0}};
            event_stage_id <= {EVENT_ID_WIDTH{1'b0}};
            event_push_pulse <= 1'b0;

            dio_event_arm_pulse <= 1'b0;
            dio_event_timestamp <= 64'd0;
            dio_event_mask <= {DIO_WIDTH{1'b0}};
            dio_event_value <= {DIO_WIDTH{1'b0}};
            dio_event_id <= {EVENT_ID_WIDTH{1'b0}};
            fifo_pop <= 1'b0;
            dispatch_inflight <= 1'b0;
        end else begin
            clear_faults_pulse <= 1'b0;
            event_push_pulse <= 1'b0;
            dio_event_arm_pulse <= 1'b0;
            fifo_pop <= 1'b0;

            if (|pwm_measurement_valid)
                pwm_sequence <= pwm_sequence + 32'd1;

            if (!aw_pending && s_axi_awvalid) begin
                aw_pending <= 1'b1;
                awaddr_hold <= s_axi_awaddr;
            end

            if (!w_pending && s_axi_wvalid) begin
                w_pending <= 1'b1;
                wdata_hold <= s_axi_wdata;
                wstrb_hold <= s_axi_wstrb;
            end

            if (write_commit) begin
                case (awaddr_hold[11:0])
                    REG_CONTROL: begin
                        cfg_hil_enable <= control_write_merged[0];
                        cfg_force_safe_sw <= control_write_merged[1];
                        if (wstrb_hold[0] && wdata_hold[2])
                            clear_faults_pulse <= 1'b1;
                        cfg_abz_enable <= control_write_merged[3];
                        cfg_abz_direction_forward <= control_write_merged[4];
                    end
                    REG_MIN_DEADTIME:
                        cfg_min_deadtime_ticks <=
                            apply_wstrb(cfg_min_deadtime_ticks, wdata_hold, wstrb_hold);
                    REG_ABZ_STEP:
                        cfg_abz_step_period_ticks <=
                            apply_wstrb(cfg_abz_step_period_ticks, wdata_hold, wstrb_hold);
                    REG_EVT_TS_LO:
                        event_stage_timestamp[31:0] <=
                            apply_wstrb(event_stage_timestamp[31:0], wdata_hold, wstrb_hold);
                    REG_EVT_TS_HI:
                        event_stage_timestamp[63:32] <=
                            apply_wstrb(event_stage_timestamp[63:32], wdata_hold, wstrb_hold);
                    REG_EVT_MASK:
                        event_stage_mask <= event_mask_write_merged[DIO_WIDTH-1:0];
                    REG_EVT_VALUE:
                        event_stage_value <= event_value_write_merged[DIO_WIDTH-1:0];
                    REG_EVT_ID:
                        event_stage_id <= event_id_write_merged[EVENT_ID_WIDTH-1:0];
                    REG_EVT_PUSH:
                        if (wstrb_hold[0] && wdata_hold[0])
                            event_push_pulse <= 1'b1;
                    default: begin
                    end
                endcase
                aw_pending <= 1'b0;
                w_pending <= 1'b0;
                s_axi_bvalid <= 1'b1;
                s_axi_bresp <= 2'b00;
            end else if (s_axi_bvalid && s_axi_bready) begin
                s_axi_bvalid <= 1'b0;
            end

            if (cfg_force_safe) begin
                dispatch_inflight <= 1'b0;
            end else begin
                if (dispatch_inflight && (dio_event_armed || dio_event_done_pulse))
                    dispatch_inflight <= 1'b0;

                if (!dispatch_inflight && !dio_event_armed && !fifo_empty) begin
                    dio_event_timestamp <= fifo_head_timestamp;
                    dio_event_mask <= fifo_head_mask;
                    dio_event_value <= fifo_head_value;
                    dio_event_id <= fifo_head_id;
                    dio_event_arm_pulse <= 1'b1;
                    fifo_pop <= 1'b1;
                    dispatch_inflight <= 1'b1;
                end
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            s_axi_rvalid <= 1'b0;
            s_axi_rresp <= 2'b00;
            s_axi_rdata <= 32'd0;
        end else begin
            if (s_axi_rvalid && s_axi_rready)
                s_axi_rvalid <= 1'b0;

            if (!s_axi_rvalid && s_axi_arvalid) begin
                s_axi_rvalid <= 1'b1;
                s_axi_rresp <= 2'b00;
                case (s_axi_araddr[11:0])
                    REG_MAGIC:        s_axi_rdata <= MAGIC;
                    REG_ABI_VERSION:  s_axi_rdata <= ABI_VERSION;
                    REG_BACKEND_ID:   s_axi_rdata <= BACKEND_ID;
                    REG_CAPABILITIES: s_axi_rdata <= CAPABILITIES;
                    REG_TICK_HZ:      s_axi_rdata <= TICK_HZ;
                    REG_COUNTER_BITS: s_axi_rdata <= 32'd64;
                    REG_TIMESTAMP_LO: s_axi_rdata <= timestamp[31:0];
                    REG_TIMESTAMP_HI: s_axi_rdata <= timestamp[63:32];
                    REG_CONTROL:
                        s_axi_rdata <= {27'd0, cfg_abz_direction_forward,
                                       cfg_abz_enable, 1'b0,
                                       cfg_force_safe, cfg_hil_enable};
                    REG_MIN_DEADTIME: s_axi_rdata <= cfg_min_deadtime_ticks;
                    REG_ABZ_STEP:     s_axi_rdata <= cfg_abz_step_period_ticks;
                    REG_BUILD_ID:     s_axi_rdata <= BUILD_ID;
                    REG_STATUS:
                        s_axi_rdata <= {20'd0, fifo_order_error_latched,
                                       fifo_overflow_latched, 1'b0,
                                       dio_event_armed, pwm_fault_flags,
                                       cfg_force_safe, cfg_hil_enable};
                    REG_PWM_SEQ:     s_axi_rdata <= pwm_sequence;
                    REG_ENCODER_POS: s_axi_rdata <= encoder_position_edges;
                    REG_PWM0_PERIOD: s_axi_rdata <= pwm_period_ticks[31:0];
                    REG_PWM0_HIGH:   s_axi_rdata <= pwm_high_ticks[31:0];
                    REG_PWM0_LOW:    s_axi_rdata <= pwm_low_ticks[31:0];
                    REG_PWM1_PERIOD: s_axi_rdata <= pwm_period_ticks[63:32];
                    REG_PWM1_HIGH:   s_axi_rdata <= pwm_high_ticks[63:32];
                    REG_PWM1_LOW:    s_axi_rdata <= pwm_low_ticks[63:32];
                    REG_PWM2_PERIOD: s_axi_rdata <= pwm_period_ticks[95:64];
                    REG_PWM2_HIGH:   s_axi_rdata <= pwm_high_ticks[95:64];
                    REG_PWM2_LOW:    s_axi_rdata <= pwm_low_ticks[95:64];
                    REG_PWM_VALID:   s_axi_rdata <= {29'd0, pwm_measurement_valid};
                    REG_PWM_FAULTS:  s_axi_rdata <= {26'd0, pwm_fault_flags};
                    REG_EVT_TS_LO:   s_axi_rdata <= event_stage_timestamp[31:0];
                    REG_EVT_TS_HI:   s_axi_rdata <= event_stage_timestamp[63:32];
                    REG_EVT_MASK:    s_axi_rdata <= {{(32-DIO_WIDTH){1'b0}}, event_stage_mask};
                    REG_EVT_VALUE:   s_axi_rdata <= {{(32-DIO_WIDTH){1'b0}}, event_stage_value};
                    REG_EVT_ID:      s_axi_rdata <= {{(32-EVENT_ID_WIDTH){1'b0}}, event_stage_id};
                    REG_EVT_STATUS:
                        s_axi_rdata <= {8'd0, fifo_level, 4'd0,
                                       fifo_order_error_latched,
                                       fifo_overflow_latched,
                                       fifo_full, fifo_empty};
                    default: s_axi_rdata <= 32'd0;
                endcase
            end
        end
    end

endmodule

`default_nettype wire
