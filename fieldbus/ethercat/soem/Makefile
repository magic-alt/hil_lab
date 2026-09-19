CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra
SOEM_CFLAGS ?= $(shell pkg-config --cflags soem 2>/dev/null)
SOEM_LIBS ?= $(shell pkg-config --libs soem 2>/dev/null)

.PHONY: all clean
all: soem_cycle

soem_cycle: soem_cycle.c
	$(CC) $(CFLAGS) $(SOEM_CFLAGS) -o $@ $< $(SOEM_LIBS) -lrt

clean:
	rm -f soem_cycle
