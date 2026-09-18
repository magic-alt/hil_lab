PRU_CGT ?=

PSSP_REQUESTED := $(strip $(PSSP_DIR))
PSSP_CANDIDATES := \
	$(PSSP_REQUESTED) \
	/usr/lib/ti/pru-software-support-package \
	$(sort $(wildcard /usr/lib/ti/pru-software-support-package-v*)) \
	/opt/source/pru-software-support-package \
	$(HOME)/pru-software-support-package
PSSP_DIR := $(firstword $(foreach d,$(PSSP_CANDIDATES),$(if $(wildcard $(d)/include/pru_rpmsg.h),$(d))))

GEN_DIR := gen
TARGET := $(GEN_DIR)/hil_b1_pru0.out
MAP := $(GEN_DIR)/hil_b1_pru0.map
LINKER_COMMAND_FILE := AM335x_PRU_B1.cmd

CFLAGS := -v3 -O2 --display_error_number --endian=little --hardware_mac=on \
	--obj_directory=$(GEN_DIR) --pp_directory=$(GEN_DIR) -ppd -ppa
LFLAGS := --reread_libs --warn_sections --stack_size=0x100 --heap_size=0x100
INCLUDES := --include_path=$(PRU_CGT)/include \
	--include_path=$(PSSP_DIR)/include \
	--include_path=$(PSSP_DIR)/include/am335x \
	--include_path=../common \
	--include_path=../pru0_b0
LIBS := --library=$(PSSP_DIR)/lib/rpmsg_lib.lib

OBJECTS := \
	$(GEN_DIR)/main.object \
	$(GEN_DIR)/resource_table_0.object \
	$(GEN_DIR)/pwm_capture_core.object

.PHONY: all clean env check-env

all: check-env $(TARGET)

env:
	@echo "PRU_CGT=$(PRU_CGT)"
	@echo "PSSP_REQUESTED=$(PSSP_REQUESTED)"
	@echo "PSSP_DIR=$(PSSP_DIR)"
	@command -v clpru 2>/dev/null | sed 's/^/clpru(PATH)=/' || true

check-env:
	@test -n "$(PRU_CGT)" || (echo "ERROR: set PRU_CGT"; exit 2)
	@test -x "$(PRU_CGT)/bin/clpru" || (echo "ERROR: $(PRU_CGT)/bin/clpru not found"; exit 2)
	@test -n "$(PSSP_DIR)" || (echo "ERROR: PSSP not found"; exit 2)
	@test -f "$(PSSP_DIR)/include/pru_rpmsg.h" || (echo "ERROR: pru_rpmsg.h not found"; exit 2)
	@test -f "$(PSSP_DIR)/lib/rpmsg_lib.lib" || (echo "ERROR: rpmsg_lib.lib not found"; exit 2)

$(TARGET): $(OBJECTS) $(LINKER_COMMAND_FILE)
	$(PRU_CGT)/bin/clpru $(CFLAGS) -z -i$(PRU_CGT)/lib -i$(PRU_CGT)/include \
		$(LFLAGS) -o $@ $(OBJECTS) -m$(MAP) $(LINKER_COMMAND_FILE) \
		--library=libc.a $(LIBS)

$(GEN_DIR)/main.object: main.c
	@mkdir -p $(GEN_DIR)
	$(PRU_CGT)/bin/clpru $(INCLUDES) $(CFLAGS) -fe $@ $<

$(GEN_DIR)/resource_table_0.object: ../pru0_b0/resource_table_0.c
	@mkdir -p $(GEN_DIR)
	$(PRU_CGT)/bin/clpru $(INCLUDES) $(CFLAGS) -fe $@ $<

$(GEN_DIR)/pwm_capture_core.object: ../common/pwm_capture_core.c
	@mkdir -p $(GEN_DIR)
	$(PRU_CGT)/bin/clpru $(INCLUDES) $(CFLAGS) -fe $@ $<

clean:
	rm -rf $(GEN_DIR)
