# ALINX AX7010 FPGA-Lite HIL constraints
# Device: XC7Z010-1CLG400
# Source: ALINX AX7010 user manual / J10/J11 pin tables.
# All mapped PL expansion I/O below is 3.3 V. J10/J11 include 33 ohm
# series resistors on the board. Never connect 5 V logic directly.

set_property PACKAGE_PIN U18 [get_ports pl_clk_50m]
set_property IOSTANDARD LVCMOS33 [get_ports pl_clk_50m]
create_clock -period 20.000 -name pl_clk_50m -waveform {0.000 10.000} [get_ports pl_clk_50m]

# J10: DUT -> HIL, encoder inputs and bench controls.
set_property PACKAGE_PIN W19 [get_ports {dut_pwm_high_in[0]}] ; # J10-3
set_property PACKAGE_PIN W18 [get_ports {dut_pwm_low_in[0]}]  ; # J10-4
set_property PACKAGE_PIN R14 [get_ports {dut_pwm_high_in[1]}] ; # J10-5
set_property PACKAGE_PIN P14 [get_ports {dut_pwm_low_in[1]}]  ; # J10-6
set_property PACKAGE_PIN Y17 [get_ports {dut_pwm_high_in[2]}] ; # J10-7
set_property PACKAGE_PIN Y16 [get_ports {dut_pwm_low_in[2]}]  ; # J10-8
set_property PACKAGE_PIN W15 [get_ports dut_enc_a_in]         ; # J10-9
set_property PACKAGE_PIN V15 [get_ports dut_enc_b_in]         ; # J10-10
set_property PACKAGE_PIN Y14 [get_ports dut_enc_z_in]         ; # J10-11
set_property PACKAGE_PIN W14 [get_ports dut_ssi_data_in]      ; # J10-12
set_property PACKAGE_PIN P18 [get_ports dut_ssi_clk_in]       ; # J10-13
set_property PACKAGE_PIN U15 [get_ports ext_reset_n]          ; # J10-15
set_property PACKAGE_PIN U14 [get_ports hil_enable_in]        ; # J10-16
set_property PACKAGE_PIN P16 [get_ports force_safe_in]        ; # J10-17
set_property PACKAGE_PIN P15 [get_ports clear_faults_in]      ; # J10-18
set_property PACKAGE_PIN U17 [get_ports encoder_direction_in] ; # J10-19
set_property PACKAGE_PIN T16 [get_ports ssi_master_start_in]  ; # J10-20

set_property IOSTANDARD LVCMOS33 [get_ports {dut_pwm_high_in[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports {dut_pwm_low_in[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports dut_enc_a_in]
set_property IOSTANDARD LVCMOS33 [get_ports dut_enc_b_in]
set_property IOSTANDARD LVCMOS33 [get_ports dut_enc_z_in]
set_property IOSTANDARD LVCMOS33 [get_ports dut_ssi_data_in]
set_property IOSTANDARD LVCMOS33 [get_ports dut_ssi_clk_in]
set_property IOSTANDARD LVCMOS33 [get_ports ext_reset_n]
set_property IOSTANDARD LVCMOS33 [get_ports hil_enable_in]
set_property IOSTANDARD LVCMOS33 [get_ports force_safe_in]
set_property IOSTANDARD LVCMOS33 [get_ports clear_faults_in]
set_property IOSTANDARD LVCMOS33 [get_ports encoder_direction_in]
set_property IOSTANDARD LVCMOS33 [get_ports ssi_master_start_in]

set_property PULLDOWN true [get_ports {dut_pwm_high_in[*]}]
set_property PULLDOWN true [get_ports {dut_pwm_low_in[*]}]
set_property PULLDOWN true [get_ports dut_enc_a_in]
set_property PULLDOWN true [get_ports dut_enc_b_in]
set_property PULLDOWN true [get_ports dut_enc_z_in]
set_property PULLDOWN true [get_ports dut_ssi_data_in]
set_property PULLUP   true [get_ports dut_ssi_clk_in]
set_property PULLUP   true [get_ports ext_reset_n]
set_property PULLDOWN true [get_ports hil_enable_in]
set_property PULLUP   true [get_ports force_safe_in]
set_property PULLDOWN true [get_ports clear_faults_in]
set_property PULLUP   true [get_ports encoder_direction_in]
set_property PULLDOWN true [get_ports ssi_master_start_in]

# J11: HIL -> DUT stimulus/status.
set_property PACKAGE_PIN F17 [get_ports {stim_pwm_high_out[0]}] ; # J11-3
set_property PACKAGE_PIN F16 [get_ports {stim_pwm_low_out[0]}]  ; # J11-4
set_property PACKAGE_PIN F20 [get_ports {stim_pwm_high_out[1]}] ; # J11-5
set_property PACKAGE_PIN F19 [get_ports {stim_pwm_low_out[1]}]  ; # J11-6
set_property PACKAGE_PIN G20 [get_ports {stim_pwm_high_out[2]}] ; # J11-7
set_property PACKAGE_PIN G19 [get_ports {stim_pwm_low_out[2]}]  ; # J11-8
set_property PACKAGE_PIN H18 [get_ports stim_enc_a_out]         ; # J11-9
set_property PACKAGE_PIN J18 [get_ports stim_enc_b_out]         ; # J11-10
set_property PACKAGE_PIN L20 [get_ports stim_enc_z_out]         ; # J11-11
set_property PACKAGE_PIN L19 [get_ports stim_ssi_clk_out]       ; # J11-12
set_property PACKAGE_PIN M20 [get_ports stim_ssi_data_out]      ; # J11-13
set_property PACKAGE_PIN M19 [get_ports fault_out]              ; # J11-14
set_property PACKAGE_PIN K18 [get_ports {status_out[0]}]        ; # J11-15
set_property PACKAGE_PIN K17 [get_ports {status_out[1]}]        ; # J11-16
set_property PACKAGE_PIN J19 [get_ports {status_out[2]}]        ; # J11-17
set_property PACKAGE_PIN K19 [get_ports {status_out[3]}]        ; # J11-18

set_property IOSTANDARD LVCMOS33 [get_ports {stim_pwm_high_out[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports {stim_pwm_low_out[*]}]
set_property IOSTANDARD LVCMOS33 [get_ports stim_enc_a_out]
set_property IOSTANDARD LVCMOS33 [get_ports stim_enc_b_out]
set_property IOSTANDARD LVCMOS33 [get_ports stim_enc_z_out]
set_property IOSTANDARD LVCMOS33 [get_ports stim_ssi_clk_out]
set_property IOSTANDARD LVCMOS33 [get_ports stim_ssi_data_out]
set_property IOSTANDARD LVCMOS33 [get_ports fault_out]
set_property IOSTANDARD LVCMOS33 [get_ports {status_out[*]}]

set_property DRIVE 8 [get_ports {stim_pwm_high_out[*]}]
set_property DRIVE 8 [get_ports {stim_pwm_low_out[*]}]
set_property DRIVE 8 [get_ports stim_enc_a_out]
set_property DRIVE 8 [get_ports stim_enc_b_out]
set_property DRIVE 8 [get_ports stim_enc_z_out]
set_property DRIVE 8 [get_ports stim_ssi_clk_out]
set_property DRIVE 8 [get_ports stim_ssi_data_out]
set_property SLEW FAST [get_ports {stim_pwm_high_out[*]}]
set_property SLEW FAST [get_ports {stim_pwm_low_out[*]}]
set_property SLEW FAST [get_ports stim_enc_a_out]
set_property SLEW FAST [get_ports stim_enc_b_out]
set_property SLEW FAST [get_ports stim_enc_z_out]
set_property SLEW FAST [get_ports stim_ssi_clk_out]
set_property SLEW FAST [get_ports stim_ssi_data_out]

# Active-low PL LEDs.
set_property PACKAGE_PIN M14 [get_ports {led_n[0]}]
set_property PACKAGE_PIN M15 [get_ports {led_n[1]}]
set_property PACKAGE_PIN K16 [get_ports {led_n[2]}]
set_property PACKAGE_PIN J16 [get_ports {led_n[3]}]
set_property IOSTANDARD LVCMOS33 [get_ports {led_n[*]}]
