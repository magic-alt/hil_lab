#include "stm32f4xx_hal.h"
#include "pwm_profile.h"

TIM_HandleTypeDef htim8;

static void SystemClock_Config(void);
static void GPIO_Init(void);
static void TIM8_Init(void);
static uint32_t deadtime_ns_to_dtg(uint32_t deadtime_ns);
static void Error_Handler(void);

static uint32_t div_round_closest_u64(uint64_t numerator, uint64_t denominator)
{
    return (uint32_t)((numerator + (denominator / 2ULL)) / denominator);
}

/*
 * Encode requested dead-time into STM32F4 TIMx_BDTR.DTG.
 *
 * RM0090 encoding:
 *   0xx: DT = DTG * tDTS
 *   10x: DT = (64 + DTG[5:0]) * 2 * tDTS
 *   110: DT = (32 + DTG[4:0]) * 8 * tDTS
 *   111: DT = (32 + DTG[4:0]) * 16 * tDTS
 *
 * TIM8 uses CKD=DIV1, so tDTS = 1 / 180 MHz.
 */
static uint32_t deadtime_ns_to_dtg(uint32_t deadtime_ns)
{
    uint32_t ticks = div_round_closest_u64(
        (uint64_t)deadtime_ns * (uint64_t)HIL_APB2_TIMER_HZ,
        1000000000ULL);

    if (ticks <= 127U) {
        return ticks;
    }

    if (ticks <= 254U) {
        uint32_t scaled = (ticks + 1U) / 2U;
        if (scaled < 64U) {
            scaled = 64U;
        }
        if (scaled > 127U) {
            scaled = 127U;
        }
        return 0x80U | (scaled - 64U);
    }

    if (ticks <= 504U) {
        uint32_t scaled = (ticks + 4U) / 8U;
        if (scaled < 32U) {
            scaled = 32U;
        }
        if (scaled > 63U) {
            scaled = 63U;
        }
        return 0xC0U | (scaled - 32U);
    }

    {
        uint32_t scaled = (ticks + 8U) / 16U;
        if (scaled < 32U) {
            scaled = 32U;
        }
        if (scaled > 63U) {
            scaled = 63U;
        }
        return 0xE0U | (scaled - 32U);
    }
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    GPIO_Init();
    TIM8_Init();

    if (HAL_TIM_PWM_Start(&htim8, TIM_CHANNEL_1) != HAL_OK) {
        Error_Handler();
    }

    if (HAL_TIMEx_PWMN_Start(&htim8, TIM_CHANNEL_1) != HAL_OK) {
        Error_Handler();
    }

    /* Green LED indicates that the stimulus generator is active. */
    HAL_GPIO_WritePin(GPIOG, GPIO_PIN_13, GPIO_PIN_SET);

    while (1) {
        __WFI();
    }
}

static void TIM8_Init(void)
{
    TIM_OC_InitTypeDef oc = {0};
    TIM_BreakDeadTimeConfigTypeDef bdtr = {0};

    __HAL_RCC_TIM8_CLK_ENABLE();

    htim8.Instance = TIM8;
    htim8.Init.Prescaler = 0U;
    htim8.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim8.Init.Period = HIL_PWM_ARR;
    htim8.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim8.Init.RepetitionCounter = 0U;
    htim8.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;

    if (HAL_TIM_PWM_Init(&htim8) != HAL_OK) {
        Error_Handler();
    }

    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = HIL_PWM_CCR1;
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    oc.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    oc.OCFastMode = TIM_OCFAST_DISABLE;
    oc.OCIdleState = TIM_OCIDLESTATE_RESET;
    oc.OCNIdleState = TIM_OCNIDLESTATE_RESET;

    if (HAL_TIM_PWM_ConfigChannel(&htim8, &oc, TIM_CHANNEL_1) != HAL_OK) {
        Error_Handler();
    }

    bdtr.OffStateRunMode = TIM_OSSR_DISABLE;
    bdtr.OffStateIDLEMode = TIM_OSSI_DISABLE;
    bdtr.LockLevel = TIM_LOCKLEVEL_OFF;
    bdtr.DeadTime = deadtime_ns_to_dtg(PWM_DEADTIME_NS);
    bdtr.BreakState = TIM_BREAK_DISABLE;
    bdtr.BreakPolarity = TIM_BREAKPOLARITY_HIGH;
    bdtr.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;

    if (HAL_TIMEx_ConfigBreakDeadTime(&htim8, &bdtr) != HAL_OK) {
        Error_Handler();
    }
}

static void GPIO_Init(void)
{
    GPIO_InitTypeDef gpio = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOG_CLK_ENABLE();

    /*
     * PC6: TIM8_CH1  (UH), AF3, exposed on P1 pin 57.
     * PA5: TIM8_CH1N (UL), AF3, exposed on P2 pin 21.
     *
     * PC6 is also connected to the onboard LCD HSYNC input. The LCD is not
     * initialized by this firmware, so there is no output contention; the LCD
     * may simply display garbage/flicker while the stimulus is running.
     */
    gpio.Mode = GPIO_MODE_AF_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    gpio.Alternate = GPIO_AF3_TIM8;

    gpio.Pin = GPIO_PIN_6;
    HAL_GPIO_Init(GPIOC, &gpio);

    gpio.Pin = GPIO_PIN_5;
    HAL_GPIO_Init(GPIOA, &gpio);

    /* Green status LED LD3 on PG13. */
    gpio.Pin = GPIO_PIN_13;
    gpio.Mode = GPIO_MODE_OUTPUT_PP;
    gpio.Pull = GPIO_NOPULL;
    gpio.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOG, &gpio);
    HAL_GPIO_WritePin(GPIOG, GPIO_PIN_13, GPIO_PIN_RESET);
}

static void SystemClock_Config(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};

    __HAL_RCC_PWR_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);

    /*
     * STM32F429I-DISC1 factory configuration routes an 8 MHz ST-LINK MCO
     * clock to PH0/OSC_IN. Use HSE bypass, then PLL to 180 MHz.
     */
    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    osc.HSEState = RCC_HSE_BYPASS;
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLM = 8U;
    osc.PLL.PLLN = 360U;
    osc.PLL.PLLP = RCC_PLLP_DIV2;
    osc.PLL.PLLQ = 7U;

    if (HAL_RCC_OscConfig(&osc) != HAL_OK) {
        Error_Handler();
    }

    if (HAL_PWREx_EnableOverDrive() != HAL_OK) {
        Error_Handler();
    }

    clk.ClockType =
        RCC_CLOCKTYPE_SYSCLK |
        RCC_CLOCKTYPE_HCLK |
        RCC_CLOCKTYPE_PCLK1 |
        RCC_CLOCKTYPE_PCLK2;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.AHBCLKDivider = RCC_SYSCLK_DIV1;
    clk.APB1CLKDivider = RCC_HCLK_DIV4;
    clk.APB2CLKDivider = RCC_HCLK_DIV2;

    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_5) != HAL_OK) {
        Error_Handler();
    }

    SystemCoreClockUpdate();
}

static void Error_Handler(void)
{
    __disable_irq();
    HAL_GPIO_WritePin(GPIOG, GPIO_PIN_13, GPIO_PIN_RESET);
    while (1) {
    }
}
