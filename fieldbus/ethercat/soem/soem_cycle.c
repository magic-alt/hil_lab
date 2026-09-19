#define _GNU_SOURCE
#include "ethercat.h"
#include <inttypes.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>

#define NS_PER_S 1000000000LL

static int64_t ts_ns(const struct timespec *ts) {
    return (int64_t)ts->tv_sec * NS_PER_S + ts->tv_nsec;
}
static void add_ns(struct timespec *ts, int64_t ns) {
    int64_t n = (int64_t)ts->tv_nsec + ns;
    ts->tv_sec += n / NS_PER_S;
    ts->tv_nsec = n % NS_PER_S;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <interface> [cycle_us=1000] [seconds=10]\n", argv[0]);
        return 2;
    }
    const char *ifname = argv[1];
    unsigned cycle_us = argc > 2 ? (unsigned)strtoul(argv[2], NULL, 0) : 1000;
    unsigned seconds = argc > 3 ? (unsigned)strtoul(argv[3], NULL, 0) : 10;
    if (!cycle_us || !seconds) return 2;

    char IOmap[4096];
    if (!ec_init(ifname)) {
        fprintf(stderr, "ec_init failed for %s\n", ifname);
        return 3;
    }
    int slaves = ec_config_init(FALSE);
    if (slaves <= 0) {
        fprintf(stderr, "no EtherCAT slaves found\n");
        ec_close();
        return 3;
    }

    ec_config_map(&IOmap);
    ec_configdc();
    ec_statecheck(0, EC_STATE_SAFE_OP, EC_TIMEOUTSTATE * 4);

    ec_slave[0].state = EC_STATE_OPERATIONAL;
    ec_writestate(0);
    ec_statecheck(0, EC_STATE_OPERATIONAL, EC_TIMEOUTSTATE * 4);

    int expected_wkc = (ec_group[0].outputsWKC * 2) + ec_group[0].inputsWKC;
    uint64_t requested = ((uint64_t)seconds * 1000000ULL) / cycle_us;
    uint64_t cycles = 0, bad_wkc = 0, deadline_misses = 0;
    long double sum_abs = 0.0L;
    int64_t max_abs = 0;
    int last_wkc = 0;
    const int64_t cycle_ns = (int64_t)cycle_us * 1000LL;

    mlockall(MCL_CURRENT | MCL_FUTURE);
    struct sched_param sp = {.sched_priority = 80};
    sched_setscheduler(0, SCHED_FIFO, &sp);

    struct timespec wake;
    clock_gettime(CLOCK_MONOTONIC, &wake);

    while (cycles < requested) {
        add_ns(&wake, cycle_ns);
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &wake, NULL);
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        int64_t jitter = ts_ns(&now) - ts_ns(&wake);
        int64_t abs_jitter = jitter < 0 ? -jitter : jitter;
        if (abs_jitter > max_abs) max_abs = abs_jitter;
        sum_abs += abs_jitter;
        if (abs_jitter > cycle_ns / 2) deadline_misses++;

        ec_send_processdata();
        last_wkc = ec_receive_processdata(EC_TIMEOUTRET);
        if (cycles > 100 && last_wkc < expected_wkc) bad_wkc++;
        cycles++;
    }

    printf("{\"cycles\":%" PRIu64 ",\"cycle_ns\":%" PRId64 ","
           "\"expected_wkc\":%d,\"last_wkc\":%d,\"bad_wkc\":%" PRIu64 ","
           "\"max_abs_jitter_ns\":%" PRId64 ",\"mean_abs_jitter_ns\":%.3f,"
           "\"deadline_misses\":%" PRIu64 ",\"dc_time_ns\":%" PRId64 ","
           "\"slave_count\":%d}\n",
           cycles, cycle_ns, expected_wkc, last_wkc, bad_wkc, max_abs,
           cycles ? (double)(sum_abs / cycles) : 0.0, deadline_misses,
           (int64_t)ec_DCtime, slaves);

    ec_slave[0].state = EC_STATE_SAFE_OP;
    ec_writestate(0);
    ec_close();
    return cycles == requested ? 0 : 4;
}
