`default_nettype none

module hil_axi_digital_core #(
    parameter [31:0] BACKEND_ID = 32'h00007010,
    parameter [31:0] BUILD_ID = 32'h00000001,
    parameter [31:0] CAPABILITIES = 32'h00000C37,
    parameter SPI_FRAME_BITS = 24,
    parameter [SPI_FRAME_BITS-1:0] SPI_FRAME_DATA = 24'hA55A3C,
    parameter DIO_WIDTH = 16
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     external_force_safe,

    input  wire [11:0]              s_axi_awaddr,
    input  wire                     s_axi_awvalid,
    output wire                     s_axi_awready,
    input  wire [31:0]              s_axi_wdata,
    input  wire [3:0]               s_axi_wstrb,
    input  wire                     s_axi_wvalid,
    output wire                     s_axi_wready,
    output wire [1:0]               s_axi_bresp,
    output wire                     s_axi_bvalid,
    input  wire                     s_axi_bready,
    input  wire [11:0]              s_axi_araddr,
    input  wire                     s_axi_arvalid,
    output wire                     s_axi_arready,
    output wire [31:0]              s_axi_rdata,
    output wire [1:0]               s_axi_rresp,
    output wire                     s_axi_rvalid,
    input  wire                     s_axi_rready,

    input  wire [2:0]               pwm_high_in,
    input  wire [2:0]               pwm_low_in,
    input  wire                     spi_sclk_in,
    input  wire                     spi_cs_n_in,
    input  wire                     spi_mosi_in,

    output wire                     enc_a_out,
    output wire                     enc_b_out,
    output wire                     enc_z_out,
    output wire                     spi_miso_out,
    output wire [DIO_WIDTH-1:0]     dio_out,
    output wire                     hil_active,
    output wire                     fault_summary
);

    wire cfg_hil_enable;
    wire cfg_force_safe;
    wire clear_faults_pulse;
    wire [31:0] cfg_min_deadtime_ticks;
    wire cfg_abz_enable;
    wire cfg_abz_direction_forward;
    wire [31:0] cfg_abz_step_period_ticks;

    wire dio_event_arm_pulse;
    wire [63:0] dio_event_timestamp;
    wire [DIO_WIDTH-1:0] dio_event_mask;
    wire [DIO_WIDTH-1:0] dio_event_value;
    wire [15:0] dio_event_id;
    wire dio_event_armed;
    wire dio_event_done_pulse;

    wire [63:0] timestamp;
    wire [95:0] pwm_period_ticks;
    wire [95:0] pwm_high_ticks;
    wire [95:0] pwm_low_ticks;
    wire [2:0] pwm_measurement_valid;
    wire [95:0] dead_hl;
    wire [95:0] dead_lh;
    wire [2:0] shoot_faults;
    wire [2:0] dead_faults;
    wire [31:0] encoder_position_edges;
    wire spi_frame_active;
    wire spi_frame_done;
    wire [15:0] spi_rx_count;
    wire [SPI_FRAME_BITS-1:0] spi_rx_data;

    assign hil_active = cfg_hil_enable & ~cfg_force_safe;
    assign fault_summary = |shoot_faults | |dead_faults;

    hil_digital_core #(
        .SPI_FRAME_BITS(SPI_FRAME_BITS),
        .DIO_WIDTH(DIO_WIDTH)
    ) u_core (
        .clk(clk),
        .rst_n(rst_n),
        .pwm_high(pwm_high_in),
        .pwm_low(pwm_low_in),
        .min_deadtime_ticks(cfg_min_deadtime_ticks),
        .clear_pwm_faults(clear_faults_pulse),
        .encoder_enable(hil_active & cfg_abz_enable),
        .encoder_direction_forward(cfg_abz_direction_forward),
        .encoder_step_period_ticks(cfg_abz_step_period_ticks),
        .enc_a(enc_a_out),
        .enc_b(enc_b_out),
        .enc_z(enc_z_out),
        .encoder_position_edges(encoder_position_edges),
        .spi_sclk(spi_sclk_in),
        .spi_cs_n(spi_cs_n_in),
        .spi_mosi(spi_mosi_in),
        .spi_frame_data(SPI_FRAME_DATA),
        .spi_fault_flip_mask({SPI_FRAME_BITS{1'b0}}),
        .spi_fault_enable(1'b0),
        .spi_miso(spi_miso_out),
        .spi_frame_active(spi_frame_active),
        .spi_frame_done_pulse(spi_frame_done),
        .spi_received_bit_count(spi_rx_count),
        .spi_received_mosi_data(spi_rx_data),
        .dio_event_arm(dio_event_arm_pulse),
        .dio_event_timestamp(dio_event_timestamp),
        .dio_event_mask(dio_event_mask),
        .dio_event_value(dio_event_value),
        .dio_safe_value({DIO_WIDTH{1'b0}}),
        .dio_force_safe(~hil_active),
        .dio_out(dio_out),
        .dio_event_armed(dio_event_armed),
        .dio_event_done_pulse(dio_event_done_pulse),
        .timestamp(timestamp),
        .pwm_period_ticks(pwm_period_ticks),
        .pwm_high_ticks(pwm_high_ticks),
        .pwm_low_ticks(pwm_low_ticks),
        .pwm_measurement_valid(pwm_measurement_valid),
        .deadtime_high_to_low_ticks(dead_hl),
        .deadtime_low_to_high_ticks(dead_lh),
        .shoot_through_latched(shoot_faults),
        .deadtime_violation_latched(dead_faults)
    );

    hil_axi_control_plane #(
        .DIO_WIDTH(DIO_WIDTH),
        .BACKEND_ID(BACKEND_ID),
        .CAPABILITIES(CAPABILITIES),
        .BUILD_ID(BUILD_ID)
    ) u_control (
        .clk(clk),
        .rst_n(rst_n),
        .s_axi_awaddr(s_axi_awaddr),
        .s_axi_awvalid(s_axi_awvalid),
        .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata),
        .s_axi_wstrb(s_axi_wstrb),
        .s_axi_wvalid(s_axi_wvalid),
        .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp),
        .s_axi_bvalid(s_axi_bvalid),
        .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr),
        .s_axi_arvalid(s_axi_arvalid),
        .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata),
        .s_axi_rresp(s_axi_rresp),
        .s_axi_rvalid(s_axi_rvalid),
        .s_axi_rready(s_axi_rready),
        .external_force_safe(external_force_safe),
        .timestamp(timestamp),
        .pwm_period_ticks(pwm_period_ticks),
        .pwm_high_ticks(pwm_high_ticks),
        .pwm_low_ticks(pwm_low_ticks),
        .pwm_measurement_valid(pwm_measurement_valid),
        .pwm_fault_flags({dead_faults, shoot_faults}),
        .encoder_position_edges(encoder_position_edges),
        .dio_event_armed(dio_event_armed),
        .dio_event_done_pulse(dio_event_done_pulse),
        .cfg_hil_enable(cfg_hil_enable),
        .cfg_force_safe(cfg_force_safe),
        .clear_faults_pulse(clear_faults_pulse),
        .cfg_min_deadtime_ticks(cfg_min_deadtime_ticks),
        .cfg_abz_enable(cfg_abz_enable),
        .cfg_abz_direction_forward(cfg_abz_direction_forward),
        .cfg_abz_step_period_ticks(cfg_abz_step_period_ticks),
        .dio_event_arm_pulse(dio_event_arm_pulse),
        .dio_event_timestamp(dio_event_timestamp),
        .dio_event_mask(dio_event_mask),
        .dio_event_value(dio_event_value),
        .dio_event_id(dio_event_id)
    );

endmodule

`default_nettype wire
