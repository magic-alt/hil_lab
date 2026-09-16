# Create, synthesize, implement and export the AXU2CGB HIL bitstream.
# Usage:
#   vivado -mode batch -source boards/zu2cg/scripts/build_bitstream.tcl

set script_dir [file dirname [file normalize [info script]]]
set repo_root [file normalize [file join $script_dir ../../..]]
source [file join $script_dir create_project.tcl]

set jobs 4
launch_runs synth_1 -jobs $jobs
wait_on_run synth_1
if {[get_property STATUS [get_runs synth_1]] ne "synth_design Complete!"} {
    error "Synthesis failed: [get_property STATUS [get_runs synth_1]]"
}

launch_runs impl_1 -to_step write_bitstream -jobs $jobs
wait_on_run impl_1
if {![string match "write_bitstream Complete!" [get_property STATUS [get_runs impl_1]]]} {
    error "Implementation/bitstream failed: [get_property STATUS [get_runs impl_1]]"
}

open_run impl_1
set report_dir [file join $repo_root build reports axu2cgb]
file mkdir $report_dir
report_timing_summary -file [file join $report_dir timing_summary.rpt]
report_utilization -file [file join $report_dir utilization.rpt]
report_drc -file [file join $report_dir drc.rpt]

set bit_files [glob -nocomplain [file join $project_dir ${project_name}.runs impl_1 *.bit]]
if {[llength $bit_files] != 1} {
    error "Expected one bitstream, found [llength $bit_files]: $bit_files"
}

set artifact_dir [file join $repo_root build artifacts axu2cgb]
file mkdir $artifact_dir
file copy -force [lindex $bit_files 0] [file join $artifact_dir axu2cgb_hil.bit]
puts "INFO: Bitstream: [file join $artifact_dir axu2cgb_hil.bit]"
