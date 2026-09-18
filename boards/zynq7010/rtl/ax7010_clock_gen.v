`default_nettype none

module ax7010_clock_gen (
    input  wire pl_clk_50m,
    input  wire reset_n,
    output wire hil_clk,
    output wire locked
);

`ifdef HIL_SIMULATION
    assign hil_clk = pl_clk_50m;
    assign locked  = reset_n;
`else
    wire clk_in_buf;
    wire clkfb_unbuf;
    wire clkfb_buf;
    wire clk_out_unbuf;
    wire mmcm_locked;

    BUFG u_clk_in_bufg (
        .I(pl_clk_50m),
        .O(clk_in_buf)
    );

    // 50 MHz * 20 / 10 = 100 MHz, VCO = 1 GHz.
    MMCME2_BASE #(
        .BANDWIDTH("OPTIMIZED"),
        .CLKFBOUT_MULT_F(20.000),
        .CLKFBOUT_PHASE(0.000),
        .CLKIN1_PERIOD(20.000),
        .CLKOUT0_DIVIDE_F(10.000),
        .CLKOUT0_DUTY_CYCLE(0.500),
        .CLKOUT0_PHASE(0.000),
        .DIVCLK_DIVIDE(1),
        .STARTUP_WAIT("FALSE")
    ) u_mmcm (
        .CLKFBOUT(clkfb_unbuf),
        .CLKOUT0(clk_out_unbuf),
        .LOCKED(mmcm_locked),
        .CLKFBIN(clkfb_buf),
        .CLKIN1(clk_in_buf),
        .PWRDWN(1'b0),
        .RST(~reset_n)
    );

    BUFG u_clkfb_bufg (
        .I(clkfb_unbuf),
        .O(clkfb_buf)
    );

    BUFG u_hil_clk_bufg (
        .I(clk_out_unbuf),
        .O(hil_clk)
    );

    assign locked = mmcm_locked;
`endif

endmodule

`default_nettype wire
