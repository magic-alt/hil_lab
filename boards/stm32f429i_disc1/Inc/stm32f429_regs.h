#ifndef HIL_STM32F429_REGS_H_
#define HIL_STM32F429_REGS_H_

#include <stdint.h>

#define REG32(addr) (*(volatile uint32_t *)(addr))

#define RCC_BASE        0x40023800UL
#define FLASH_BASE      0x40023C00UL
#define PWR_BASE        0x40007000UL
#define GPIOA_BASE      0x40020000UL
#define GPIOC_BASE      0x40020800UL
#define GPIOG_BASE      0x40021800UL
#define TIM8_BASE       0x40010400UL

#define RCC_CR          REG32(RCC_BASE + 0x00UL)
#define RCC_PLLCFGR     REG32(RCC_BASE + 0x04UL)
#define RCC_CFGR        REG32(RCC_BASE + 0x08UL)
#define RCC_AHB1ENR     REG32(RCC_BASE + 0x30UL)
#define RCC_APB1ENR     REG32(RCC_BASE + 0x40UL)
#define RCC_APB2ENR     REG32(RCC_BASE + 0x44UL)

#define FLASH_ACR       REG32(FLASH_BASE + 0x00UL)

#define PWR_CR          REG32(PWR_BASE + 0x00UL)
#define PWR_CSR         REG32(PWR_BASE + 0x04UL)

#define GPIO_MODER(base)    REG32((base) + 0x00UL)
#define GPIO_OTYPER(base)   REG32((base) + 0x04UL)
#define GPIO_OSPEEDR(base)  REG32((base) + 0x08UL)
#define GPIO_PUPDR(base)    REG32((base) + 0x0CUL)
#define GPIO_ODR(base)      REG32((base) + 0x14UL)
#define GPIO_AFRL(base)     REG32((base) + 0x20UL)

#define TIM8_CR1        REG32(TIM8_BASE + 0x00UL)
#define TIM8_EGR        REG32(TIM8_BASE + 0x14UL)
#define TIM8_CCMR1      REG32(TIM8_BASE + 0x18UL)
#define TIM8_CCER       REG32(TIM8_BASE + 0x20UL)
#define TIM8_PSC        REG32(TIM8_BASE + 0x28UL)
#define TIM8_ARR        REG32(TIM8_BASE + 0x2CUL)
#define TIM8_CCR1       REG32(TIM8_BASE + 0x34UL)
#define TIM8_BDTR       REG32(TIM8_BASE + 0x44UL)

#define SCB_VTOR        REG32(0xE000ED08UL)
#define SCB_CPACR       REG32(0xE000ED88UL)

#define RCC_CR_HSION        (1UL << 0)
#define RCC_CR_HSIRDY       (1UL << 1)
#define RCC_CR_HSEON        (1UL << 16)
#define RCC_CR_HSERDY       (1UL << 17)
#define RCC_CR_HSEBYP       (1UL << 18)
#define RCC_CR_PLLON        (1UL << 24)
#define RCC_CR_PLLRDY       (1UL << 25)

#define RCC_PLLCFGR_PLLSRC_HSE  (1UL << 22)

#define RCC_AHB1ENR_GPIOAEN (1UL << 0)
#define RCC_AHB1ENR_GPIOCEN (1UL << 2)
#define RCC_AHB1ENR_GPIOGEN (1UL << 6)
#define RCC_APB1ENR_PWREN   (1UL << 28)
#define RCC_APB2ENR_TIM8EN  (1UL << 1)

#define FLASH_ACR_LATENCY_5WS (5UL)
#define FLASH_ACR_PRFTEN      (1UL << 8)
#define FLASH_ACR_ICEN        (1UL << 9)
#define FLASH_ACR_DCEN        (1UL << 10)

#define PWR_CR_VOS_SCALE1   (3UL << 14)
#define PWR_CR_ODEN         (1UL << 16)
#define PWR_CR_ODSWEN       (1UL << 17)
#define PWR_CSR_ODRDY       (1UL << 16)
#define PWR_CSR_ODSWRDY     (1UL << 17)

#define RCC_CFGR_SW_HSI     (0UL << 0)
#define RCC_CFGR_SW_PLL     (2UL << 0)
#define RCC_CFGR_SW_MASK    (3UL << 0)
#define RCC_CFGR_HPRE_MASK  (15UL << 4)
#define RCC_CFGR_PPRE1_MASK (7UL << 10)
#define RCC_CFGR_PPRE2_MASK (7UL << 13)
#define RCC_CFGR_SWS_MASK   (3UL << 2)
#define RCC_CFGR_SWS_HSI    (0UL << 2)
#define RCC_CFGR_SWS_PLL    (2UL << 2)
#define RCC_CFGR_PPRE1_DIV4 (5UL << 10)
#define RCC_CFGR_PPRE2_DIV2 (4UL << 13)

#define TIM_CR1_CEN         (1UL << 0)
#define TIM_CR1_ARPE        (1UL << 7)
#define TIM_EGR_UG          (1UL << 0)
#define TIM_CCMR1_OC1PE     (1UL << 3)
#define TIM_CCMR1_OC1M_PWM1 (6UL << 4)
#define TIM_CCER_CC1E       (1UL << 0)
#define TIM_CCER_CC1NE      (1UL << 2)
#define TIM_BDTR_MOE        (1UL << 15)

static __inline void cpu_wfi(void)
{
#if defined(__ARMCC_VERSION)
    __asm volatile ("wfi");
#else
    __asm volatile ("wfi");
#endif
}

#endif
