PRU_CGT ?=
PSSP_DIR ?=

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

.PHONY: all clean check-env

all: check-env $(TARGET)

check-env:
	@test -n "$(PRU_CGT)" || (echo "ERROR: set PRU_CGT to TI PRU Code Generation Tools"; exit 2)
	@test -x "$(PRU_CGT)/bin/clpru" || (echo "ERROR: $(PRU_CGT)/bin/clpru not found"; exit 2)
	@test -n "$(PSSP_DIR)" || (echo "ERROR: set PSSP_DIR to TI PRU Software Support Package"; exit 2)
	@test -f "$(PSSP_DIR)/include/pru_rpmsg.h" || (echo "ERROR: pru_rpmsg.h not found under PSSP_DIR"; exit 2)
	@test -f "$(PSSP_DIR)/lib/rpmsg_lib.lib" || (echo "ERROR: rpmsg_lib.lib not found under PSSP_DIR"; exit 2)

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
