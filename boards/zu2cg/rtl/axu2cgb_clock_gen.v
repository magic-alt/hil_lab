`default_nettype none

// AXU2CGB PL reference clock is 25 MHz on AB11. The pin is an HDGC input,
// so the hardware path intentionally inserts a BUFG before the MMCM, matching
// ALINX's own PLL guidance for this board family.
module axu2cgb_clock_gen (
    input  wire pl_ref_clk,
    input  wire reset_n,
    output wire hil_clk,
    output wire locked
);

`ifdef HIL_SIMULATION
    // Unit-level simulation drives pl_ref_clk at the desired HIL frequency.
    // Frequency multiplication is verified by Vivado timing/implementation,
    // not by the dependency-free Icarus regression.
    assign hil_clk = pl_ref_clk;
    assign locked  = reset_n;
`else
    wire ref_clk_buf;
    wire clkfb_unbuf;
    wire clkfb_buf;
    wire hil_clk_unbuf;
    wire mmcm_locked;

    BUFG u_refclk_bufg (
        .I(pl_ref_clk),
        .O(ref_clk_buf)
    );

    // 25 MHz * 40 / 10 = 100 MHz. VCO = 1 GHz.
    MMCME4_BASE #(
        .BANDWIDTH("OPTIMIZED"),
        .CLKFBOUT_MULT_F(40.000),
        .CLKFBOUT_PHASE(0.000),
        .CLKIN1_PERIOD(40.000),
        .CLKOUT0_DIVIDE_F(10.000),
        .CLKOUT0_DUTY_CYCLE(0.500),
        .CLKOUT0_PHASE(0.000),
        .DIVCLK_DIVIDE(1),
        .STARTUP_WAIT("FALSE")
    ) u_mmcm (
        .CLKFBOUT(clkfb_unbuf),
        .CLKOUT0(hil_clk_unbuf),
        .LOCKED(mmcm_locked),
        .CLKFBIN(clkfb_buf),
        .CLKIN1(ref_clk_buf),
        .PWRDWN(1'b0),
        .RST(~reset_n)
    );

    BUFG u_clkfb_bufg (
        .I(clkfb_unbuf),
        .O(clkfb_buf)
    );

    BUFG u_hilclk_bufg (
        .I(hil_clk_unbuf),
        .O(hil_clk)
    );

    assign locked = mmcm_locked;
`endif

endmodule

`default_nettype wire
