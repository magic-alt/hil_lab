#define _GNU_SOURCE
#include <ecrt.h>
#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define NS_PER_S 1000000000LL
#define NSEC_PER_USEC 1000LL

static unsigned int off_controlword, off_mode, off_target_position;
static unsigned int off_target_velocity, off_target_torque;
static unsigned int off_statusword, off_mode_display, off_position;
static unsigned int off_velocity, off_torque_actual;

static ec_pdo_entry_info_t rx_entries[] = {
    {0x6040, 0x00, 16}, {0x6060, 0x00, 8}, {0x607A, 0x00, 32},
    {0x60FF, 0x00, 32}, {0x6071, 0x00, 16},
};
static ec_pdo_entry_info_t tx_entries[] = {
    {0x6041, 0x00, 16}, {0x6061, 0x00, 8}, {0x6064, 0x00, 32},
    {0x606C, 0x00, 32}, {0x6077, 0x00, 16},
};
static ec_pdo_info_t pdos[] = {
    {0x1600, 5, rx_entries},
    {0x1A00, 5, tx_entries},
};
static ec_sync_info_t syncs[] = {
    {0, EC_DIR_OUTPUT, 0, NULL, EC_WD_DISABLE},
    {1, EC_DIR_INPUT, 0, NULL, EC_WD_DISABLE},
    {2, EC_DIR_OUTPUT, 1, &pdos[0], EC_WD_ENABLE},
    {3, EC_DIR_INPUT, 1, &pdos[1], EC_WD_DISABLE},
    {0xff}
};

static int64_t ts_ns(const struct timespec *ts) {
    return (int64_t)ts->tv_sec * NS_PER_S + ts->tv_nsec;
}
static void add_ns(struct timespec *ts, int64_t ns) {
    int64_t n = (int64_t)ts->tv_nsec + ns;
    ts->tv_sec += n / NS_PER_S;
    ts->tv_nsec = n % NS_PER_S;
}
static uint16_t cia402_next(uint16_t sw) {
    if (sw & 0x0008) return 0x0080;
    if ((sw & 0x004f) == 0x0040) return 0x0006;
    if ((sw & 0x006f) == 0x0021) return 0x0007;
    if ((sw & 0x006f) == 0x0023) return 0x000f;
    if ((sw & 0x006f) == 0x0027) return 0x000f;
    return 0x0000;
}
static int cia402_enabled(uint16_t sw) {
    return (sw & 0x006f) == 0x0027;
}

static void usage(const char *name) {
    fprintf(stderr,
        "usage: %s <position> <vendor_hex> <product_hex> "
        "[cycle_us=1000] [seconds=10] [mode=8] "
        "[assign_activate=0x300] [enable_drive=0]\n", name);
}

int main(int argc, char **argv) {
    if (argc < 4) { usage(argv[0]); return 2; }

    unsigned int position = (unsigned int)strtoul(argv[1], NULL, 0);
    uint32_t vendor = (uint32_t)strtoul(argv[2], NULL, 0);
    uint32_t product = (uint32_t)strtoul(argv[3], NULL, 0);
    unsigned int cycle_us = argc > 4 ? (unsigned int)strtoul(argv[4], NULL, 0) : 1000;
    unsigned int seconds = argc > 5 ? (unsigned int)strtoul(argv[5], NULL, 0) : 10;
    int mode = argc > 6 ? atoi(argv[6]) : 8;
    uint16_t assign_activate = argc > 7 ? (uint16_t)strtoul(argv[7], NULL, 0) : 0x0300;
    int enable_drive = argc > 8 ? atoi(argv[8]) : 0;

    if (!cycle_us || !seconds || (mode < 1 || mode > 10)) {
        usage(argv[0]); return 2;
    }

    const uint32_t cycle_ns = cycle_us * 1000U;
    const uint64_t requested_cycles = ((uint64_t)seconds * 1000000ULL) / cycle_us;

    ec_master_t *master = ecrt_request_master(0);
    if (!master) { fprintf(stderr, "ecrt_request_master failed\n"); return 3; }
    ec_domain_t *domain = ecrt_master_create_domain(master);
    if (!domain) { fprintf(stderr, "ecrt_master_create_domain failed\n"); return 3; }
    ec_slave_config_t *sc = ecrt_master_slave_config(master, 0, position, vendor, product);
    if (!sc) { fprintf(stderr, "ecrt_master_slave_config failed\n"); return 3; }
    if (ecrt_slave_config_pdos(sc, EC_END, syncs)) {
        fprintf(stderr, "ecrt_slave_config_pdos failed\n"); return 3;
    }

    ec_pdo_entry_reg_t regs[] = {
        {0, position, vendor, product, 0x6040, 0, &off_controlword, NULL},
        {0, position, vendor, product, 0x6060, 0, &off_mode, NULL},
        {0, position, vendor, product, 0x607A, 0, &off_target_position, NULL},
        {0, position, vendor, product, 0x60FF, 0, &off_target_velocity, NULL},
        {0, position, vendor, product, 0x6071, 0, &off_target_torque, NULL},
        {0, position, vendor, product, 0x6041, 0, &off_statusword, NULL},
        {0, position, vendor, product, 0x6061, 0, &off_mode_display, NULL},
        {0, position, vendor, product, 0x6064, 0, &off_position, NULL},
        {0, position, vendor, product, 0x606C, 0, &off_velocity, NULL},
        {0, position, vendor, product, 0x6077, 0, &off_torque_actual, NULL},
        {}
    };
    if (ecrt_domain_reg_pdo_entry_list(domain, regs)) {
        fprintf(stderr, "ecrt_domain_reg_pdo_entry_list failed\n"); return 3;
    }

    ecrt_master_select_reference_clock(master, sc);
    ecrt_slave_config_dc(sc, assign_activate, cycle_ns, 0, 0, 0);

    if (ecrt_master_activate(master)) {
        fprintf(stderr, "ecrt_master_activate failed\n"); return 3;
    }
    uint8_t *pd = ecrt_domain_data(domain);
    if (!pd) { fprintf(stderr, "ecrt_domain_data failed\n"); return 3; }

    if (mlockall(MCL_CURRENT | MCL_FUTURE)) perror("mlockall");
    struct sched_param sp = {.sched_priority = 80};
    if (sched_setscheduler(0, SCHED_FIFO, &sp)) perror("sched_setscheduler");

    struct timespec wake;
    clock_gettime(CLOCK_MONOTONIC, &wake);

    uint64_t cycles = 0, bad_wkc = 0, wc_complete = 0;
    uint64_t deadline_misses = 0, enabled_cycles = 0;
    long double sum_abs_jitter = 0.0L;
    int64_t max_abs_jitter = 0;
    uint16_t last_sw = 0;
    ec_domain_state_t ds;
    memset(&ds, 0, sizeof(ds));

    while (cycles < requested_cycles) {
        add_ns(&wake, cycle_ns);
        int rc = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &wake, NULL);
        if (rc && rc != EINTR) { errno = rc; perror("clock_nanosleep"); break; }

        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        int64_t jitter = ts_ns(&now) - ts_ns(&wake);
        int64_t abs_jitter = jitter < 0 ? -jitter : jitter;
        if (abs_jitter > max_abs_jitter) max_abs_jitter = abs_jitter;
        sum_abs_jitter += (long double)abs_jitter;
        if (abs_jitter > (int64_t)cycle_ns / 2) deadline_misses++;

        ecrt_master_application_time(master, (uint64_t)ts_ns(&now));
        ecrt_master_receive(master);
        ecrt_domain_process(domain);
        ecrt_domain_state(domain, &ds);

        last_sw = EC_READ_U16(pd + off_statusword);
        if (ds.wc_state == EC_WC_COMPLETE) wc_complete++;
        else if (cycles > 100) bad_wkc++;

        EC_WRITE_S8(pd + off_mode, (int8_t)mode);
        EC_WRITE_S32(pd + off_target_position, EC_READ_S32(pd + off_position));
        EC_WRITE_S32(pd + off_target_velocity, 0);
        EC_WRITE_S16(pd + off_target_torque, 0);

        if (enable_drive) {
            uint16_t cw = cia402_next(last_sw);
            EC_WRITE_U16(pd + off_controlword, cw);
            if (cia402_enabled(last_sw)) enabled_cycles++;
        } else {
            EC_WRITE_U16(pd + off_controlword, 0x0000);
        }

        ecrt_master_sync_reference_clock(master);
        ecrt_master_sync_slave_clocks(master);
        ecrt_domain_queue(domain);
        ecrt_master_send(master);
        cycles++;
    }

    double mean_abs = cycles ? (double)(sum_abs_jitter / cycles) : 0.0;
    printf("{\"cycles\":%" PRIu64 ",\"cycle_ns\":%u,"
           "\"last_wkc\":%u,\"wc_complete_cycles\":%" PRIu64 ","
           "\"bad_wkc\":%" PRIu64 ",\"max_abs_jitter_ns\":%" PRId64 ","
           "\"mean_abs_jitter_ns\":%.3f,\"deadline_misses\":%" PRIu64 ","
           "\"statusword\":%u,\"operation_enabled_cycles\":%" PRIu64 ","
           "\"enable_drive\":%s}\n",
           cycles, cycle_ns, ds.working_counter, wc_complete, bad_wkc,
           max_abs_jitter, mean_abs, deadline_misses, last_sw,
           enabled_cycles, enable_drive ? "true" : "false");

    ecrt_release_master(master);
    return cycles == requested_cycles ? 0 : 4;
}
