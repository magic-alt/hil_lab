#include <stdint.h>

#include "stm32f429_regs.h"

uint32_t SystemCoreClock = 16000000UL;

void SystemInit(void)
{
    /* Enable CP10/CP11 full access for the Cortex-M4F FPU. */
    SCB_CPACR |= (0xFUL << 20);

    /* Application vector table lives at the start of internal Flash. */
    SCB_VTOR = 0x08000000UL;

    /*
     * After reset STM32F429 runs from HSI. main() then requires the
     * MB1075-F429I-E01 X3 8 MHz HSE crystal and switches to HSE->PLL.
     */
    SystemCoreClock = 16000000UL;
}

void SystemCoreClockUpdate(void)
{
    if ((RCC_CFGR & RCC_CFGR_SWS_MASK) == RCC_CFGR_SWS_PLL) {
        SystemCoreClock = 180000000UL;
    } else {
        SystemCoreClock = 16000000UL;
    }
}
