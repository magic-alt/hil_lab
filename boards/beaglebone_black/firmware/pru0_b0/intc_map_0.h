#ifndef HIL_B0_INTC_MAP_0_H_
#define HIL_B0_INTC_MAP_0_H_

#include <stddef.h>
#include <rsc_types.h>

/*
 * PSSP v6.0.x uses the dedicated .pru_irq_map section for PRU-side INTC
 * mappings. Interrupts that target the ARM host are owned by the Linux device
 * tree and must not be duplicated here.
 *
 * PRU0 ARM -> PRU RPMsg kick:
 *   system event 17 -> channel 0 -> host interrupt 0 (R31 bit 30)
 */
#pragma DATA_SECTION(hil_b0_irq_rsc, ".pru_irq_map")
#pragma RETAIN(hil_b0_irq_rsc)

struct pru_irq_rsc hil_b0_irq_rsc = {
    0u,
    1u,
    {
        { 17u, 0u, 0u }
    }
};

#endif
