#ifndef HIL_STM32F429I_PWM_PROFILE_H_
#define HIL_STM32F429I_PWM_PROFILE_H_

#include <stdint.h>

#ifndef PWM_FREQUENCY_HZ
#define PWM_FREQUENCY_HZ      (20000UL)
#endif

#ifndef PWM_DUTY_PERMILLE
#define PWM_DUTY_PERMILLE     (500UL)
#endif

#ifndef PWM_DEADTIME_NS
#define PWM_DEADTIME_NS       (700UL)
#endif

#define HIL_SYSCLK_HZ         (180000000UL)
#define HIL_APB2_TIMER_HZ     (180000000UL)
#define HIL_PWM_PERIOD_TICKS  (HIL_APB2_TIMER_HZ / PWM_FREQUENCY_HZ)
#define HIL_PWM_ARR           (HIL_PWM_PERIOD_TICKS - 1UL)
#define HIL_PWM_CCR1          ((HIL_PWM_PERIOD_TICKS * PWM_DUTY_PERMILLE) / 1000UL)

#if PWM_FREQUENCY_HZ == 0
#error "PWM_FREQUENCY_HZ must be > 0"
#endif

#if (HIL_APB2_TIMER_HZ % PWM_FREQUENCY_HZ) != 0
#error "PWM_FREQUENCY_HZ must divide the 180 MHz TIM8 clock exactly"
#endif

#if (PWM_DUTY_PERMILLE == 0) || (PWM_DUTY_PERMILLE >= 1000)
#error "PWM_DUTY_PERMILLE must be in the open interval (0, 1000)"
#endif

#endif
