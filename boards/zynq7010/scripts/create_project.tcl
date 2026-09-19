set script_dir [file dirname [file normalize [info script]]]
set board_dir [file normalize [file join $script_dir ..]]
set repo_root [file normalize [file join $board_dir .. ..]]
set build_dir [file join $repo_root build zynq7010_ax7010]
file mkdir $build_dir

create_project ax7010_fpga_lite $build_dir -part xc7z010clg400-1 -force

set_property target_language Verilog [current_project]
set_property simulator_language Mixed [current_project]

set rtl_files [list     [file join $repo_root rtl common sync_2ff.v]     [file join $repo_root rtl common timebase hil_timebase.v]     [file join $repo_root rtl capture pwm_capture.v]     [file join $repo_root rtl capture pwm_complementary_monitor.v]     [file join $repo_root rtl generator pwm_complementary_generator.v]     [file join $repo_root rtl generator abz_encoder_emulator.v]     [file join $repo_root rtl capture abz_encoder_capture.v]     [file join $repo_root rtl generator ssi_encoder_emulator.v]     [file join $repo_root rtl capture ssi_encoder_master_capture.v]     [file join $repo_root rtl motor pmsm_dq_plant_q16.v]     [file join $board_dir rtl ax7010_clock_gen.v]     [file join $board_dir rtl ax7010_fpga_lite_top.v] ]

add_files -norecurse $rtl_files
add_files -fileset constrs_1 -norecurse     [file join $board_dir constraints ax7010_fpga_lite.xdc]

set_property top ax7010_fpga_lite_top [current_fileset]
update_compile_order -fileset sources_1
save_project_as ax7010_fpga_lite $build_dir -force
close_project

puts "Created AX7010 FPGA-Lite HIL project under $build_dir"
