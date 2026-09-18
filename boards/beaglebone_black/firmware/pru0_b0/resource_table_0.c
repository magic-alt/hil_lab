#include "resource_table_0.h"

/*
 * RPMsg system events for PRU0.
 *   16: PRU0 -> ARM, route through channel 2 -> host 2
 *   17: ARM -> PRU0, route through channel 0 -> host 0 (R31 bit 30)
 */
struct ch_map pru_intc_map[] = {
    { 16u, 2u },
    { 17u, 0u },
};

#pragma DATA_SECTION(resourceTable, ".resource_table")
#pragma RETAIN(resourceTable)
struct hil_b0_resource_table resourceTable = {
    { 1u, 2u, 0u, 0u },
    {
        offsetof(struct hil_b0_resource_table, rpmsg_vdev),
        offsetof(struct hil_b0_resource_table, pru_ints)
    },
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
    },
    {
        TYPE_CUSTOM,
        TYPE_PRU_INTS,
        sizeof(struct fw_rsc_custom_ints),
        {
            0x0000u,
            {
                0u, HOST_UNUSED, 2u, HOST_UNUSED, HOST_UNUSED,
                HOST_UNUSED, HOST_UNUSED, HOST_UNUSED, HOST_UNUSED, HOST_UNUSED
            },
            (sizeof(pru_intc_map) / sizeof(struct ch_map)),
            pru_intc_map
        }
    }
};
