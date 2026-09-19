# Reproducible Vivado project creation for ALINX AXU2CGB.
# Usage:
#   vivado -mode batch -source boards/zu2cg/scripts/create_project.tcl

set script_dir [file dirname [file normalize [info script]]]
set repo_root [file normalize [file join $script_dir ../../..]]
set board_dir [file join $repo_root boards zu2cg]
set project_dir [file join $repo_root build vivado_axu2cgb]
set project_name hil_axu2cgb
set device_part xczu2cg-sfvc784-1-e

file mkdir [file join $repo_root build]
create_project -force $project_name $project_dir -part $device_part
set_property target_language Verilog [current_project]
set_property simulator_language Verilog [current_project]

set rtl_files [concat \
    [glob -nocomplain [file join $repo_root rtl common *.v]] \
    [glob -nocomplain [file join $repo_root rtl common timebase *.v]] \
    [glob -nocomplain [file join $repo_root rtl capture *.v]] \
    [glob -nocomplain [file join $repo_root rtl generator *.v]] \
    [glob -nocomplain [file join $repo_root rtl io *.v]] \
    [glob -nocomplain [file join $repo_root rtl dac *.v]] \
    [glob -nocomplain [file join $repo_root rtl top *.v]] \
    [glob -nocomplain [file join $board_dir rtl *.v]]]

if {[llength $rtl_files] == 0} {
    error "No RTL files found under $repo_root"
}

add_files -norecurse $rtl_files
add_files -fileset constrs_1 -norecurse [file join $board_dir constraints axu2cgb_hil.xdc]
set_property top axu2cgb_hil_top [current_fileset]
update_compile_order -fileset sources_1

puts "INFO: Created $project_name for $device_part"
puts "INFO: Project directory: $project_dir"
puts "INFO: Top: axu2cgb_hil_top"
puts "INFO: Run boards/zu2cg/scripts/build_bitstream.tcl to synthesize/implement."
