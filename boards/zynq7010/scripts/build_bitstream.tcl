set script_dir [file dirname [file normalize [info script]]]
set board_dir [file normalize [file join $script_dir ..]]
set repo_root [file normalize [file join $board_dir .. ..]]
set build_dir [file join $repo_root build zynq7010_ax7010]
set project_file [file join $build_dir ax7010_fpga_lite.xpr]

source [file join $script_dir create_project.tcl]
open_project $project_file

launch_runs synth_1 -jobs 4
wait_on_run synth_1
open_run synth_1
report_utilization -file [file join $build_dir post_synth_utilization.rpt]

launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
open_run impl_1
report_timing_summary -file [file join $build_dir post_impl_timing_summary.rpt]
report_utilization -file [file join $build_dir post_impl_utilization.rpt]
report_drc -file [file join $build_dir post_impl_drc.rpt]

puts "AX7010 FPGA-Lite bitstream build complete"
close_project
