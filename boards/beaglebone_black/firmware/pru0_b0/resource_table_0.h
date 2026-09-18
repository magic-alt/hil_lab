#ifndef HIL_B0_RESOURCE_TABLE_0_H_
#define HIL_B0_RESOURCE_TABLE_0_H_

#include <stddef.h>
#include <stdint.h>
#include <rsc_types.h>
#include <pru_rpmsg.h>
#include <pru_virtio_ids.h>
#include <pru_types.h>

#define PRU_RPMSG_VQ0_SIZE          (16u)
#define PRU_RPMSG_VQ1_SIZE          (16u)
#define VIRTIO_RPMSG_F_NS           (0u)
#define RPMSG_PRU_C0_FEATURES       (1u << VIRTIO_RPMSG_F_NS)
#define HOST_UNUSED                 (255u)

extern struct ch_map pru_intc_map[];

struct hil_b0_resource_table {
    struct resource_table base;
    uint32_t offset[2];
    struct fw_rsc_vdev rpmsg_vdev;
    struct fw_rsc_vdev_vring rpmsg_vring0;
    struct fw_rsc_vdev_vring rpmsg_vring1;
    struct fw_rsc_custom pru_ints;
};

extern struct hil_b0_resource_table resourceTable;

#endif
