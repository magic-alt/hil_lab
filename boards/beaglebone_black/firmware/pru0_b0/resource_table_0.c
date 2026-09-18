#include "resource_table_0.h"

#pragma DATA_SECTION(resourceTable, ".resource_table")
#pragma RETAIN(resourceTable)
struct hil_b0_resource_table resourceTable = {
    { 1u, 1u, 0u, 0u },
    { offsetof(struct hil_b0_resource_table, rpmsg_vdev) },
    {
        (uint32_t)TYPE_VDEV,
        (uint32_t)VIRTIO_ID_RPMSG,
        0u,
        (uint32_t)RPMSG_PRU_C0_FEATURES,
        0u,
        0u,
        0u,
        2u,
        { 0u, 0u }
    },
    {
        FW_RSC_ADDR_ANY,
        16u,
        PRU_RPMSG_VQ0_SIZE,
        0u,
        0u
    },
    {
        FW_RSC_ADDR_ANY,
        16u,
        PRU_RPMSG_VQ1_SIZE,
        0u,
        0u
    }
};
