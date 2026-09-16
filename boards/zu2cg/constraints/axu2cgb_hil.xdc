# ALINX AXU2CGB signal-level HIL constraints
# Device: XCZU2CG-1SFVC784E
# Reference sources:
#   - ALINX AXU2CGA/AXU2CGB user manual, J12/J15 expansion tables
#   - ALINX factory Vivado project system.xdc / gpio.xdc
#
# NOTE: The user manual text labels PL_REF_CLK as +1.8 V, while ALINX's
# factory XDC and official PLL tutorial both constrain AB11 as LVCMOS33.
# This project follows the vendor factory XDC. Verify the exact board revision
# and clock amplitude before first hardware qualification.

# -----------------------------------------------------------------------------
# 25 MHz PL reference clock (AB11, IO_L8P_44 / HDGC)
# -----------------------------------------------------------------------------
set_property PACKAGE_PIN AB11 [get_ports pl_ref_clk]
set_property IOSTANDARD LVCMOS33 [get_ports pl_ref_clk]
create_clock -period 40.000 -name pl_ref_clk -waveform {0.000 20.000} [get_ports pl_ref_clk]

# -----------------------------------------------------------------------------
# J12 -- DUT -> HIL and bench control, 3.3 V I/O
# -----------------------------------------------------------------------------
set_property PACKAGE_PIN F7 [get_ports {pwm_high_in[0]}] ; # J12-3  IO1_1N
set_property PACKAGE_PIN G8 [get_ports {pwm_low_in[0]}]  ; # J12-4  IO1_1P
set_property PACKAGE_PIN F6 [get_ports {pwm_high_in[1]}] ; # J12-5  IO1_2N
set_property PACKAGE_PIN G6 [get_ports {pwm_low_in[1]}]  ; # J12-6  IO1_2P
set_property PACKAGE_PIN D9 [get_ports {pwm_high_in[2]}] ; # J12-7  IO1_3N
set_property PACKAGE_PIN E9 [get_ports {pwm_low_in[2]}]  ; # J12-8  IO1_3P
set_property PACKAGE_PIN F5 [get_ports spi_sclk_in]      ; # J12-9  IO1_4N
set_property PACKAGE_PIN G5 [get_ports spi_cs_n_in]     ; # J12-10 IO1_4P
set_property PACKAGE_PIN E8 [get_ports spi_mosi_in]     ; # J12-11 IO1_5N
set_property PACKAGE_PIN F8 [get_ports ext_reset_n]     ; # J12-12 IO1_5P
set_property PACKAGE_PIN D5 [get_ports hil_enable_in]   ; # J12-13 IO1_6N
set_property PACKAGE_PIN E5 [get_ports encoder_direction_in] ; # J12-14 IO1_6P
set_property PACKAGE_PIN C4 [get_ports clear_faults_in] ; # J12-15 IO1_7N
set_property PACKAGE_PIN D4 [get_ports force_safe_in]   ; # J12-16 IO1_7P
set_property PACKAGE_PIN E3 [get_ports test_pattern_enable_in] ; # J12-17 IO1_8N

set_property IOSTANDARD LVCMOS33 [get_ports {pwm_high_in[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports {pwm_low_in[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports spi_sclk_in]
set_property IOSTANDARD LVCMOS33 [get_ports spi_cs_n_in]
set_property IOSTANDARD LVCMOS33 [get_ports spi_mosi_in]
set_property IOSTANDARD LVCMOS33 [get_ports ext_reset_n]
set_property IOSTANDARD LVCMOS33 [get_ports hil_enable_in]
set_property IOSTANDARD LVCMOS33 [get_ports encoder_direction_in]
set_property IOSTANDARD LVCMOS33 [get_ports clear_faults_in]
set_property IOSTANDARD LVCMOS33 [get_ports force_safe_in]
set_property IOSTANDARD LVCMOS33 [get_ports test_pattern_enable_in]

# Fail-safe defaults while the DUT adapter/controller is disconnected.
set_property PULLDOWN true [get_ports {pwm_high_in[*]}]
set_property PULLDOWN true [get_ports {pwm_low_in[*]}]
set_property PULLDOWN true [get_ports spi_sclk_in]
set_property PULLUP   true [get_ports spi_cs_n_in]
set_property PULLDOWN true [get_ports spi_mosi_in]
set_property PULLUP   true [get_ports ext_reset_n]
set_property PULLDOWN true [get_ports hil_enable_in]
set_property PULLUP   true [get_ports encoder_direction_in]
set_property PULLDOWN true [get_ports clear_faults_in]
set_property PULLUP   true [get_ports force_safe_in]
set_property PULLDOWN true [get_ports test_pattern_enable_in]

# -----------------------------------------------------------------------------
# J15 -- HIL -> DUT, 3.3 V I/O
# -----------------------------------------------------------------------------
set_property PACKAGE_PIN A11 [get_ports enc_a_out]       ; # J15-3  IO2_1N
set_property PACKAGE_PIN A12 [get_ports enc_b_out]       ; # J15-4  IO2_1P
set_property PACKAGE_PIN A13 [get_ports enc_z_out]       ; # J15-5  IO2_2N
set_property PACKAGE_PIN B13 [get_ports spi_miso_out]    ; # J15-6  IO2_2P

set_property PACKAGE_PIN A14 [get_ports {dio_out[0]}]    ; # J15-7
set_property PACKAGE_PIN B14 [get_ports {dio_out[1]}]    ; # J15-8
set_property PACKAGE_PIN E13 [get_ports {dio_out[2]}]    ; # J15-9
set_property PACKAGE_PIN E14 [get_ports {dio_out[3]}]    ; # J15-10
set_property PACKAGE_PIN A15 [get_ports {dio_out[4]}]    ; # J15-11
set_property PACKAGE_PIN B15 [get_ports {dio_out[5]}]    ; # J15-12
set_property PACKAGE_PIN C13 [get_ports {dio_out[6]}]    ; # J15-13
set_property PACKAGE_PIN C14 [get_ports {dio_out[7]}]    ; # J15-14
set_property PACKAGE_PIN B10 [get_ports {dio_out[8]}]    ; # J15-15
set_property PACKAGE_PIN C11 [get_ports {dio_out[9]}]    ; # J15-16
set_property PACKAGE_PIN D14 [get_ports {dio_out[10]}]   ; # J15-17
set_property PACKAGE_PIN D15 [get_ports {dio_out[11]}]   ; # J15-18
set_property PACKAGE_PIN F11 [get_ports {dio_out[12]}]   ; # J15-19
set_property PACKAGE_PIN F12 [get_ports {dio_out[13]}]   ; # J15-20
set_property PACKAGE_PIN H13 [get_ports {dio_out[14]}]   ; # J15-21
set_property PACKAGE_PIN H14 [get_ports {dio_out[15]}]   ; # J15-22

set_property PACKAGE_PIN G14 [get_ports {status_out[0]}] ; # J15-23 clock locked
set_property PACKAGE_PIN G15 [get_ports {status_out[1]}] ; # J15-24 core reset released
set_property PACKAGE_PIN F10 [get_ports {status_out[2]}] ; # J15-25 PWM seen
set_property PACKAGE_PIN G11 [get_ports {status_out[3]}] ; # J15-26 fault summary

set_property IOSTANDARD LVCMOS33 [get_ports enc_a_out]
set_property IOSTANDARD LVCMOS33 [get_ports enc_b_out]
set_property IOSTANDARD LVCMOS33 [get_ports enc_z_out]
set_property IOSTANDARD LVCMOS33 [get_ports spi_miso_out]
set_property IOSTANDARD LVCMOS33 [get_ports {dio_out[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports {status_out[*]}]
set_property SLEW SLOW [get_ports enc_a_out]
set_property SLEW SLOW [get_ports enc_b_out]
set_property SLEW SLOW [get_ports enc_z_out]
set_property SLEW SLOW [get_ports spi_miso_out]
set_property SLEW SLOW [get_ports {dio_out[*]}]
set_property SLEW SLOW [get_ports {status_out[*]}]
set_property DRIVE 8 [get_ports enc_a_out]
set_property DRIVE 8 [get_ports enc_b_out]
set_property DRIVE 8 [get_ports enc_z_out]
set_property DRIVE 8 [get_ports spi_miso_out]
set_property DRIVE 8 [get_ports {dio_out[*]}]
set_property DRIVE 8 [get_ports {status_out[*]}]

# -----------------------------------------------------------------------------
# On-board active-low LEDs, BANK24
# -----------------------------------------------------------------------------
set_property PACKAGE_PIN W13 [get_ports {led_n[0]}]
set_property PACKAGE_PIN Y12 [get_ports {led_n[1]}]
set_property PACKAGE_PIN AA12 [get_ports {led_n[2]}]
set_property PACKAGE_PIN AB13 [get_ports {led_n[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led_n[*]}]
set_property SLEW SLOW [get_ports {led_n[*]}]
