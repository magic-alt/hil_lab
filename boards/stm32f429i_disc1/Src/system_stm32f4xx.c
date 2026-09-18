#include <stdint.h>

#include "stm32f429_regs.h"

uint32_t SystemCoreClock = 16000000UL;

void SystemInit(void)
{
    /* Enable CP10/CP11 full access for the Cortex-M4F FPU. */
    SCB_CPACR |= (0xFUL << 20);

    /* Application vector table lives at the start of internal Flash. */
    SCB_VTOR = 0x08000000UL;

    SystemCoreClock = 16000000UL;
}

void SystemCoreClockUpdate(void)
{
    /*
     * This project owns the entire clock tree and always switches to
     * 180 MHz before calling this function.
     */
    SystemCoreClock = 180000000UL;
}
