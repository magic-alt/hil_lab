`timescale 1ns/1ps
`default_nettype none

module tb_hil_axi_control_plane;
    reg clk;
    reg rst_n;
    reg [11:0] awaddr;
    reg awvalid;
    wire awready;
    reg [31:0] wdata;
    reg [3:0] wstrb;
    reg wvalid;
    wire wready;
    wire [1:0] bresp;
    wire bvalid;
    reg bready;
    reg [11:0] araddr;
    reg arvalid;
    wire arready;
    wire [31:0] rdata;
    wire [1:0] rresp;
    wire rvalid;
    reg rready;

    reg external_force_safe;
    reg [63:0] timestamp;
    reg [95:0] pwm_period_ticks;
    reg [95:0] pwm_high_ticks;
    reg [95:0] pwm_low_ticks;
    reg [2:0] pwm_valid;
    reg [5:0] pwm_faults;
    reg [31:0] encoder_pos;
    reg dio_armed;
    reg dio_done;

    wire cfg_enable;
    wire cfg_safe;
    wire clear_faults;
    wire [31:0] min_deadtime;
    wire abz_enable;
    wire abz_dir;
    wire [31:0] abz_step;
    wire event_arm;
    wire [63:0] event_ts;
    wire [15:0] event_mask;
    wire [15:0] event_value;
    wire [15:0] event_id;

    integer errors;
    reg [31:0] rd;

    hil_axi_control_plane #(
        .BACKEND_ID(32'h00007010),
        .CAPABILITIES(32'h00000C37),
        .EVENT_DEPTH(4)
    ) dut (
        .clk(clk), .rst_n(rst_n),
        .s_axi_awaddr(awaddr), .s_axi_awvalid(awvalid), .s_axi_awready(awready),
        .s_axi_wdata(wdata), .s_axi_wstrb(wstrb), .s_axi_wvalid(wvalid), .s_axi_wready(wready),
        .s_axi_bresp(bresp), .s_axi_bvalid(bvalid), .s_axi_bready(bready),
        .s_axi_araddr(araddr), .s_axi_arvalid(arvalid), .s_axi_arready(arready),
        .s_axi_rdata(rdata), .s_axi_rresp(rresp), .s_axi_rvalid(rvalid), .s_axi_rready(rready),
        .external_force_safe(external_force_safe),
        .timestamp(timestamp),
        .pwm_period_ticks(pwm_period_ticks),
        .pwm_high_ticks(pwm_high_ticks),
        .pwm_low_ticks(pwm_low_ticks),
        .pwm_measurement_valid(pwm_valid),
        .pwm_fault_flags(pwm_faults),
        .encoder_position_edges(encoder_pos),
        .dio_event_armed(dio_armed),
        .dio_event_done_pulse(dio_done),
        .cfg_hil_enable(cfg_enable), .cfg_force_safe(cfg_safe),
        .clear_faults_pulse(clear_faults), .cfg_min_deadtime_ticks(min_deadtime),
        .cfg_abz_enable(abz_enable), .cfg_abz_direction_forward(abz_dir),
        .cfg_abz_step_period_ticks(abz_step),
        .dio_event_arm_pulse(event_arm), .dio_event_timestamp(event_ts),
        .dio_event_mask(event_mask), .dio_event_value(event_value), .dio_event_id(event_id)
    );

    always #5 clk = ~clk;

    task axi_write;
        input [11:0] addr;
        input [31:0] data;
        begin
            @(negedge clk);
            awaddr = addr; awvalid = 1'b1;
            wdata = data; wstrb = 4'hf; wvalid = 1'b1;
            wait (awready && wready);
            @(negedge clk);
            awvalid = 1'b0; wvalid = 1'b0;
            wait (bvalid);
            @(negedge clk);
        end
    endtask

    task axi_read;
        input [11:0] addr;
        output [31:0] data;
        begin
            @(negedge clk);
            araddr = addr; arvalid = 1'b1;
            wait (arready);
            @(negedge clk);
            arvalid = 1'b0;
            wait (rvalid);
            data = rdata;
            @(negedge clk);
        end
    endtask

    initial begin
        clk=0; rst_n=0; awaddr=0; awvalid=0; wdata=0; wstrb=0; wvalid=0;
        bready=1; araddr=0; arvalid=0; rready=1; external_force_safe=0;
        timestamp=64'h1122334455667788;
        pwm_period_ticks={32'd7000,32'd6000,32'd5000};
        pwm_high_ticks={32'd3500,32'd3000,32'd2500};
        pwm_low_ticks={32'd3500,32'd3000,32'd2500};
        pwm_valid=3'b111; pwm_faults=6'b100001; encoder_pos=32'h12345678;
        dio_armed=1; dio_done=0; errors=0;
        repeat(4) @(posedge clk); rst_n=1;

        axi_read(12'h000,rd);
        if(rd!==32'h48494C32) errors=errors+1;
        axi_read(12'h008,rd);
        if(rd!==32'h00007010) errors=errors+1;
        axi_read(12'h018,rd);
        if(rd!==32'h55667788) errors=errors+1;
        axi_read(12'h044,rd);
        if(rd!==32'd2500) errors=errors+1;

        axi_write(12'h020,32'h00000019);
        if(!cfg_enable || cfg_safe || !abz_enable || !abz_dir) errors=errors+1;
        axi_write(12'h028,32'd4321);
        if(abz_step!==32'd4321) errors=errors+1;

        axi_write(12'h100,32'h00001234);
        axi_write(12'h104,32'h00000001);
        axi_write(12'h108,32'h0000000f);
        axi_write(12'h10c,32'h00000005);
        axi_write(12'h110,32'h00000007);
        axi_write(12'h114,32'h00000001);

        repeat(3) @(posedge clk);
        axi_read(12'h118,rd);
        if(rd[23:8]!==16'd1) begin
            $display("ERROR: event queue level=%0d",rd[23:8]);
            errors=errors+1;
        end

        @(negedge clk); dio_armed=0;
        wait(event_arm);
        if(event_ts!==64'h0000000100001234 || event_mask!==16'h000f ||
           event_value!==16'h0005 || event_id!==16'h0007) begin
            $display("ERROR: dispatched event mismatch");
            errors=errors+1;
        end

        external_force_safe=1;
        @(posedge clk);
        axi_read(12'h020,rd);
        if(!rd[1]) errors=errors+1;

        if(errors==0) begin
            $display("PASS: tb_hil_axi_control_plane");
            $finish;
        end
        $display("FAIL: tb_hil_axi_control_plane errors=%0d",errors);
        $fatal(1);
    end
endmodule

`default_nettype wire
