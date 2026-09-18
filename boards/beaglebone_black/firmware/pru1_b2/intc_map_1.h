#ifndef HIL_B2_INTC_MAP_1_H_
#define HIL_B2_INTC_MAP_1_H_

#include <stddef.h>
#include <rsc_types.h>

/*
 * PRU1 ARM -> PRU RPMsg kick:
 *   system event 19 -> channel 1 -> host interrupt 1 (R31 bit 31)
 *
 * Linux owns the PRU -> ARM system-event 18 mapping.
 */
#pragma DATA_SECTION(hil_b2_irq_rsc, ".pru_irq_map")
#pragma RETAIN(hil_b2_irq_rsc)

struct pru_irq_rsc hil_b2_irq_rsc = {
    0u,
    1u,
    {
        { 19u, 1u, 1u }
    }
};

#endif
