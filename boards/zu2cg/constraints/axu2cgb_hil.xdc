# ALINX AXU2CGB signal-level HIL constraints
# Device: XCZU2CG-1SFVC784E
# Reference: ALINX AXU2CGA/AXU2CGB expansion tables and factory XDC.
# NOTE: vendor manual text and factory XDC disagree on PL_REF_CLK voltage;
# this project follows the factory LVCMOS33 XDC pending physical verification.

set_property PACKAGE_PIN AB11 [get_ports pl_ref_clk]
set_property IOSTANDARD LVCMOS33 [get_ports pl_ref_clk]
create_clock -period 40.000 -name pl_ref_clk -waveform {0.000 20.000} [get_ports pl_ref_clk]

# J12 -- DUT -> HIL and bench-control inputs, 3.3 V logic.
set_property PACKAGE_PIN F7 [get_ports {pwm_high_in[0]}] ; # J12-3
set_property PACKAGE_PIN G8 [get_ports {pwm_low_in[0]}]  ; # J12-4
set_property PACKAGE_PIN F6 [get_ports {pwm_high_in[1]}] ; # J12-5
set_property PACKAGE_PIN G6 [get_ports {pwm_low_in[1]}]  ; # J12-6
set_property PACKAGE_PIN D9 [get_ports {pwm_high_in[2]}] ; # J12-7
set_property PACKAGE_PIN E9 [get_ports {pwm_low_in[2]}]  ; # J12-8
set_property PACKAGE_PIN F5 [get_ports spi_sclk_in]      ; # J12-9
set_property PACKAGE_PIN G5 [get_ports spi_cs_n_in]     ; # J12-10
set_property PACKAGE_PIN E8 [get_ports spi_mosi_in]     ; # J12-11
set_property PACKAGE_PIN F8 [get_ports ext_reset_n]     ; # J12-12
set_property PACKAGE_PIN D5 [get_ports hil_enable_in]   ; # J12-13
set_property PACKAGE_PIN E5 [get_ports encoder_direction_in] ; # J12-14
set_property PACKAGE_PIN C4 [get_ports clear_faults_in] ; # J12-15
set_property PACKAGE_PIN D4 [get_ports force_safe_in]   ; # J12-16
set_property PACKAGE_PIN E3 [get_ports test_pattern_enable_in] ; # J12-17
set_property PACKAGE_PIN E4 [get_ports {dac_pattern_select_in[0]}] ; # J12-18
set_property PACKAGE_PIN F1 [get_ports {dac_pattern_select_in[1]}] ; # J12-19

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
set_property IOSTANDARD LVCMOS33 [get_ports {dac_pattern_select_in[*]}]

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
set_property PULLDOWN true [get_ports {dac_pattern_select_in[*]}]

# J15 -- G0 HIL -> DUT outputs, 3.3 V logic.
set_property PACKAGE_PIN A11 [get_ports enc_a_out]       ; # J15-3
set_property PACKAGE_PIN A12 [get_ports enc_b_out]       ; # J15-4
set_property PACKAGE_PIN A13 [get_ports enc_z_out]       ; # J15-5
set_property PACKAGE_PIN B13 [get_ports spi_miso_out]    ; # J15-6
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
set_property PACKAGE_PIN G14 [get_ports {status_out[0]}] ; # J15-23
set_property PACKAGE_PIN G15 [get_ports {status_out[1]}] ; # J15-24
set_property PACKAGE_PIN F10 [get_ports {status_out[2]}] ; # J15-25
set_property PACKAGE_PIN G11 [get_ports {status_out[3]}] ; # J15-26

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

# J15 -- G1 FPGA -> 3.3V/1.8V DAC level-shifter interposer.
# These pins must never be wired directly to AD3542R VLOGIC.
set_property PACKAGE_PIN H12 [get_ports dac_sclk_out]          ; # J15-27
set_property PACKAGE_PIN J12 [get_ports dac_cs_n_out]          ; # J15-28
set_property PACKAGE_PIN J14 [get_ports dac_mosi_a_out]        ; # J15-29
set_property PACKAGE_PIN K14 [get_ports dac_mosi_b_out]        ; # J15-30
set_property PACKAGE_PIN K12 [get_ports dac_reset_n_out]       ; # J15-31
set_property PACKAGE_PIN K13 [get_ports dac_ldac_n_out]        ; # J15-32
set_property PACKAGE_PIN L13 [get_ports dac_output_enable_out] ; # J15-33
set_property PACKAGE_PIN L14 [get_ports dac_initialized_out]   ; # J15-34
set_property PACKAGE_PIN G10 [get_ports dac_stream_active_out] ; # J15-35

set_property IOSTANDARD LVCMOS33 [get_ports dac_sclk_out]
set_property IOSTANDARD LVCMOS33 [get_ports dac_cs_n_out]
set_property IOSTANDARD LVCMOS33 [get_ports dac_mosi_a_out]
set_property IOSTANDARD LVCMOS33 [get_ports dac_mosi_b_out]
set_property IOSTANDARD LVCMOS33 [get_ports dac_reset_n_out]
set_property IOSTANDARD LVCMOS33 [get_ports dac_ldac_n_out]
set_property IOSTANDARD LVCMOS33 [get_ports dac_output_enable_out]
set_property IOSTANDARD LVCMOS33 [get_ports dac_initialized_out]
set_property IOSTANDARD LVCMOS33 [get_ports dac_stream_active_out]
set_property SLEW FAST [get_ports dac_sclk_out]
set_property SLEW FAST [get_ports dac_cs_n_out]
set_property SLEW FAST [get_ports dac_mosi_a_out]
set_property SLEW FAST [get_ports dac_mosi_b_out]
set_property SLEW SLOW [get_ports dac_reset_n_out]
set_property SLEW SLOW [get_ports dac_ldac_n_out]
set_property SLEW SLOW [get_ports dac_output_enable_out]
set_property SLEW SLOW [get_ports dac_initialized_out]
set_property SLEW SLOW [get_ports dac_stream_active_out]
set_property DRIVE 8 [get_ports dac_sclk_out]
set_property DRIVE 8 [get_ports dac_cs_n_out]
set_property DRIVE 8 [get_ports dac_mosi_a_out]
set_property DRIVE 8 [get_ports dac_mosi_b_out]
set_property DRIVE 8 [get_ports dac_reset_n_out]
set_property DRIVE 8 [get_ports dac_ldac_n_out]
set_property DRIVE 8 [get_ports dac_output_enable_out]
set_property DRIVE 8 [get_ports dac_initialized_out]
set_property DRIVE 8 [get_ports dac_stream_active_out]

# On-board active-low LEDs.
set_property PACKAGE_PIN W13 [get_ports {led_n[0]}]
set_property PACKAGE_PIN Y12 [get_ports {led_n[1]}]
set_property PACKAGE_PIN AA12 [get_ports {led_n[2]}]
set_property PACKAGE_PIN AB13 [get_ports {led_n[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led_n[*]}]
set_property SLEW SLOW [get_ports {led_n[*]}]
