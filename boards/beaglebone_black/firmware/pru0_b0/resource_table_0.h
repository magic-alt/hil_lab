#ifndef HIL_B0_RESOURCE_TABLE_0_H_
#define HIL_B0_RESOURCE_TABLE_0_H_

#include <stddef.h>
#include <stdint.h>
#include <rsc_types.h>
#include <pru_rpmsg.h>

struct hil_b0_resource_table {
    struct resource_table base;
    uint32_t offset[1];
    struct fw_rsc_vdev rpmsg_vdev;
    struct fw_rsc_vdev_vring rpmsg_vring0;
    struct fw_rsc_vdev_vring rpmsg_vring1;
};

extern struct hil_b0_resource_table resourceTable;

#endif
