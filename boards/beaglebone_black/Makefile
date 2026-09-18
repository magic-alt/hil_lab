PYTHON ?= python3
CC ?= cc
PRU0_B0_DIR := firmware/pru0_b0
PRU0_B1_DIR := firmware/pru0_b1
PRU0_B1_RAW_DIR := firmware/pru0_b1_raw
HOST_DIR := host
BUILD_DIR := build
FIRMWARE_B0 := $(PRU0_B0_DIR)/gen/hil_b0_pru0.out
FIRMWARE_B1 := $(PRU0_B1_DIR)/gen/hil_b1_pru0.out
FIRMWARE_B1_RAW := $(PRU0_B1_RAW_DIR)/gen/hil_b1_raw_pru0.out
PWM_CORE_TEST := $(BUILD_DIR)/test_pwm_capture_core

.PHONY: check protocol-test python-check pwm-core-test shell-check \
	env b1-env b1-raw-env pru0 pru0-b1 pru0-b1-raw deploy deploy-b1 deploy-b1-raw clean

check: python-check protocol-test pwm-core-test shell-check

python-check:
	$(PYTHON) -m py_compile \
		$(HOST_DIR)/hil_pru_protocol.py \
		$(HOST_DIR)/hil_pru_cli.py \
		$(HOST_DIR)/hil_pwm_shared.py \
		$(HOST_DIR)/hil_pwm_cli.py \
		$(HOST_DIR)/hil_raw_shared.py \
		$(HOST_DIR)/hil_raw_cli.py \
		scripts/pru0_ctl.py

protocol-test:
	PYTHONPATH=$(HOST_DIR) $(PYTHON) -m unittest discover -v -s $(HOST_DIR) -p 'test_*.py'

pwm-core-test:
	@mkdir -p $(BUILD_DIR)
	$(CC) -std=c11 -Wall -Wextra -Werror -Ifirmware/common \
		firmware/common/pwm_capture_core.c \
		firmware/common/test_pwm_capture_core.c \
		-o $(PWM_CORE_TEST)
	$(PWM_CORE_TEST)

shell-check:
	sh -n pinmux/setup_b0_loopback.sh
	sh -n pinmux/setup_b1_pwm_inputs.sh

env:
	$(MAKE) -C $(PRU0_B0_DIR) env

b1-env:
	$(MAKE) -C $(PRU0_B1_DIR) env

b1-raw-env:
	$(MAKE) -C $(PRU0_B1_RAW_DIR) env

pru0:
	$(MAKE) -C $(PRU0_B0_DIR)

pru0-b1:
	$(MAKE) -C $(PRU0_B1_DIR)

pru0-b1-raw:
	$(MAKE) -C $(PRU0_B1_RAW_DIR)

deploy: pru0
	sudo $(PYTHON) scripts/pru0_ctl.py deploy $(FIRMWARE_B0)

deploy-b1: pru0-b1
	sudo $(PYTHON) scripts/pru0_ctl.py deploy $(FIRMWARE_B1)

deploy-b1-raw: pru0-b1-raw
	sudo $(PYTHON) scripts/pru0_ctl.py deploy $(FIRMWARE_B1_RAW)

clean:
	$(MAKE) -C $(PRU0_B0_DIR) clean
	$(MAKE) -C $(PRU0_B1_DIR) clean
	$(MAKE) -C $(PRU0_B1_RAW_DIR) clean
	rm -rf $(BUILD_DIR) $(HOST_DIR)/__pycache__ scripts/__pycache__
