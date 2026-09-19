CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -Werror
EC_CFLAGS ?= $(shell ethercat-config --cflags 2>/dev/null)
EC_LIBS ?= $(shell ethercat-config --libs 2>/dev/null)

.PHONY: all clean
all: cia402_cycle

cia402_cycle: cia402_cycle.c
	$(CC) $(CFLAGS) $(EC_CFLAGS) -o $@ $< $(EC_LIBS) -lrt -lm

clean:
	rm -f cia402_cycle
