#ifndef HIL_GD32H75E_PWM_PROFILE_H_
#define HIL_GD32H75E_PWM_PROFILE_H_

#include <stdint.h>

#ifndef PWM_FREQUENCY_HZ
#define PWM_FREQUENCY_HZ 20000UL
#endif
#ifndef PWM_DUTY_PERMILLE
#define PWM_DUTY_PERMILLE 500UL
#endif
#ifndef PWM_DEADTIME_NS
#define PWM_DEADTIME_NS 700UL
#endif
#ifndef PWM_PROFILE_ID
#define PWM_PROFILE_ID 2UL
#endif

#if PWM_FREQUENCY_HZ == 0
#error "PWM_FREQUENCY_HZ must be > 0"
#endif
#if (PWM_DUTY_PERMILLE == 0) || (PWM_DUTY_PERMILLE >= 1000)
#error "PWM_DUTY_PERMILLE must be in (0, 1000)"
#endif

#endif
