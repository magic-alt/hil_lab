PYTHON ?= python3
PRU0_DIR := firmware/pru0_b0
HOST_DIR := host
FIRMWARE := $(PRU0_DIR)/gen/hil_b0_pru0.out

.PHONY: check protocol-test python-check shell-check env pru0 deploy clean

check: python-check protocol-test shell-check

python-check:
	$(PYTHON) -m py_compile $(HOST_DIR)/hil_pru_protocol.py $(HOST_DIR)/hil_pru_cli.py scripts/pru0_ctl.py

protocol-test:
	PYTHONPATH=$(HOST_DIR) $(PYTHON) -m unittest -v $(HOST_DIR)/test_hil_pru_protocol.py

shell-check:
	sh -n pinmux/setup_b0_loopback.sh

env:
	$(MAKE) -C $(PRU0_DIR) env

pru0:
	$(MAKE) -C $(PRU0_DIR)

deploy: pru0
	sudo $(PYTHON) scripts/pru0_ctl.py deploy $(FIRMWARE)

clean:
	$(MAKE) -C $(PRU0_DIR) clean
	rm -rf $(HOST_DIR)/__pycache__ scripts/__pycache__
