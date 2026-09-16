PYTHON ?= python3
IVERILOG ?= iverilog
VVP ?= vvp
VERILATOR ?= verilator

BUILD_DIR := build

RTL_COMMON := rtl/common/sync_2ff.v
RTL_TIME := rtl/time/hil_timebase.v
RTL_PWM := rtl/pwm/pwm_capture.v rtl/pwm/pwm_complementary_monitor.v
RTL_ENCODER := rtl/encoder/abz_encoder_emulator.v rtl/encoder/spi_encoder_emulator.v
RTL_IO := rtl/io/dio_event_scheduler.v
RTL_TOP := rtl/top/hil_digital_core.v
RTL := $(RTL_COMMON) $(RTL_TIME) $(RTL_PWM) $(RTL_ENCODER) $(RTL_IO) $(RTL_TOP)

AXU2CGB_RTL := boards/zu2cg/rtl/axu2cgb_clock_gen.v boards/zu2cg/rtl/axu2cgb_hil_top.v

.PHONY: all verify policy compile lint test test-pwm test-deadtime test-abz test-spi test-event \
	board-constraints board-compile board-test board-lint clean

all: verify

verify: policy compile test lint board-constraints board-compile board-test board-lint

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

policy:
	$(PYTHON) tools/rtl_policy_check.py

compile: $(BUILD_DIR)
	$(IVERILOG) -g2005 -Wall -s hil_digital_core -o $(BUILD_DIR)/hil_digital_core.vvp $(RTL)

lint:
	$(VERILATOR) --lint-only --language 1364-2005 -Wall -Wno-fatal --top-module hil_digital_core $(RTL)

test: test-pwm test-deadtime test-abz test-spi test-event

test-pwm: $(BUILD_DIR)
	$(IVERILOG) -g2012 -Wall -o $(BUILD_DIR)/tb_pwm_capture.vvp $(RTL_COMMON) $(RTL_TIME) rtl/pwm/pwm_capture.v sim/tb_pwm_capture.v
	$(VVP) $(BUILD_DIR)/tb_pwm_capture.vvp

test-deadtime: $(BUILD_DIR)
	$(IVERILOG) -g2012 -Wall -o $(BUILD_DIR)/tb_pwm_complementary_monitor.vvp $(RTL_COMMON) $(RTL_TIME) rtl/pwm/pwm_complementary_monitor.v sim/tb_pwm_complementary_monitor.v
	$(VVP) $(BUILD_DIR)/tb_pwm_complementary_monitor.vvp

test-abz: $(BUILD_DIR)
	$(IVERILOG) -g2012 -Wall -o $(BUILD_DIR)/tb_abz_encoder_emulator.vvp rtl/encoder/abz_encoder_emulator.v sim/tb_abz_encoder_emulator.v
	$(VVP) $(BUILD_DIR)/tb_abz_encoder_emulator.vvp

test-spi: $(BUILD_DIR)
	$(IVERILOG) -g2012 -Wall -o $(BUILD_DIR)/tb_spi_encoder_emulator.vvp $(RTL_COMMON) rtl/encoder/spi_encoder_emulator.v sim/tb_spi_encoder_emulator.v
	$(VVP) $(BUILD_DIR)/tb_spi_encoder_emulator.vvp

test-event: $(BUILD_DIR)
	$(IVERILOG) -g2012 -Wall -o $(BUILD_DIR)/tb_dio_event_scheduler.vvp $(RTL_TIME) rtl/io/dio_event_scheduler.v sim/tb_dio_event_scheduler.v
	$(VVP) $(BUILD_DIR)/tb_dio_event_scheduler.vvp

board-constraints:
	$(PYTHON) tools/axu2cgb_constraints_check.py

board-compile: $(BUILD_DIR)
	$(IVERILOG) -DHIL_SIMULATION -g2005 -Wall -s axu2cgb_hil_top -o $(BUILD_DIR)/axu2cgb_hil_top.vvp $(RTL) $(AXU2CGB_RTL)

board-test: $(BUILD_DIR)
	$(IVERILOG) -DHIL_SIMULATION -g2012 -Wall -s tb_axu2cgb_hil_top -o $(BUILD_DIR)/tb_axu2cgb_hil_top.vvp $(RTL) $(AXU2CGB_RTL) sim/tb_axu2cgb_hil_top.v
	$(VVP) $(BUILD_DIR)/tb_axu2cgb_hil_top.vvp

board-lint:
	$(VERILATOR) -DHIL_SIMULATION --lint-only --language 1364-2005 -Wall -Wno-fatal --top-module axu2cgb_hil_top $(RTL) $(AXU2CGB_RTL)

clean:
	rm -rf $(BUILD_DIR)
