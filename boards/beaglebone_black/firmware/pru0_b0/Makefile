PRU_CGT ?=

# Prefer an explicitly supplied PSSP_DIR when it is valid, then common
# BeagleBoard Debian/TI locations. Newer Debian images may not install PSSP by
# default, so check-env prints the exact clone command when none exists.
PSSP_REQUESTED := $(strip $(PSSP_DIR))
PSSP_CANDIDATES := \
	$(PSSP_REQUESTED) \
	/usr/lib/ti/pru-software-support-package \
	$(sort $(wildcard /usr/lib/ti/pru-software-support-package-v*)) \
	/opt/source/pru-software-support-package \
	$(HOME)/pru-software-support-package
PSSP_DIR := $(firstword $(foreach d,$(PSSP_CANDIDATES),$(if $(wildcard $(d)/include/pru_rpmsg.h),$(d))))

GEN_DIR := gen
TARGET := $(GEN_DIR)/hil_b0_pru0.out
MAP := $(GEN_DIR)/hil_b0_pru0.map
SOURCES := main.c resource_table_0.c
OBJECTS := $(patsubst %.c,$(GEN_DIR)/%.object,$(SOURCES))
LINKER_COMMAND_FILE := AM335x_PRU.cmd

CFLAGS := -v3 -O2 --display_error_number --endian=little --hardware_mac=on \
	--obj_directory=$(GEN_DIR) --pp_directory=$(GEN_DIR) -ppd -ppa
LFLAGS := --reread_libs --warn_sections --stack_size=0x100 --heap_size=0x100
INCLUDES := --include_path=$(PRU_CGT)/include \
	--include_path=$(PSSP_DIR)/include \
	--include_path=$(PSSP_DIR)/include/am335x \
	--include_path=../common
LIBS := --library=$(PSSP_DIR)/lib/rpmsg_lib.lib

.PHONY: all clean env check-env

all: check-env $(TARGET)

env:
	@echo "PRU_CGT=$(PRU_CGT)"
	@echo "PSSP_REQUESTED=$(PSSP_REQUESTED)"
	@echo "PSSP_DIR=$(PSSP_DIR)"
	@command -v clpru 2>/dev/null | sed 's/^/clpru(PATH)=/' || true
	@if [ -n "$(PSSP_DIR)" ]; then \
		echo "PSSP header=$(PSSP_DIR)/include/pru_rpmsg.h"; \
		echo "PSSP library=$(PSSP_DIR)/lib/rpmsg_lib.lib"; \
	fi

check-env:
	@test -n "$(PRU_CGT)" || (echo "ERROR: set PRU_CGT to TI PRU Code Generation Tools (normally /usr/share/ti/cgt-pru)"; exit 2)
	@test -x "$(PRU_CGT)/bin/clpru" || (echo "ERROR: $(PRU_CGT)/bin/clpru not found"; echo "       On current BeagleBoard Debian try: sudo apt update && sudo apt install ti-pru-cgt-v2.3"; exit 2)
	@test -n "$(PSSP_DIR)" || ( \
		echo "ERROR: PRU Software Support Package (PSSP) not found."; \
		echo "       Expected include/pru_rpmsg.h and lib/rpmsg_lib.lib."; \
		echo "       Common path: /usr/lib/ti/pru-software-support-package"; \
		echo "       Install/clone with:"; \
		echo "         sudo mkdir -p /usr/lib/ti"; \
		echo "         sudo git clone --depth 1 --branch v6.5.0 https://git.ti.com/git/pru-software-support-package/pru-software-support-package.git /usr/lib/ti/pru-software-support-package"; \
		echo "       Or export PSSP_DIR=/path/to/pru-software-support-package"; \
		exit 2)
	@test -f "$(PSSP_DIR)/include/pru_rpmsg.h" || (echo "ERROR: $(PSSP_DIR)/include/pru_rpmsg.h not found"; exit 2)
	@test -f "$(PSSP_DIR)/lib/rpmsg_lib.lib" || (echo "ERROR: $(PSSP_DIR)/lib/rpmsg_lib.lib not found"; exit 2)
	@echo "PRU toolchain: $(PRU_CGT)"
	@echo "PSSP: $(PSSP_DIR)"

$(TARGET): $(OBJECTS) $(LINKER_COMMAND_FILE)
	$(PRU_CGT)/bin/clpru $(CFLAGS) -z -i$(PRU_CGT)/lib -i$(PRU_CGT)/include \
		$(LFLAGS) -o $@ $(OBJECTS) -m$(MAP) $(LINKER_COMMAND_FILE) \
		--library=libc.a $(LIBS)

$(GEN_DIR)/%.object: %.c
	@mkdir -p $(GEN_DIR)
	$(PRU_CGT)/bin/clpru $(INCLUDES) $(CFLAGS) -fe $@ $<

clean:
	rm -rf $(GEN_DIR)

-include $(OBJECTS:%.object=%.pp)
