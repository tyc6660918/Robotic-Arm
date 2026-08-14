#ifndef __MOTOR_DRIVER_H__
#define __MOTOR_DRIVER_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include "rst_config.h"

/* 电机驱动函数 */
void Motor_SetPWM(MotorChannel_t ch, int16_t duty);
void Motor_Brake(MotorChannel_t ch);
void Motor_Coast(MotorChannel_t ch);

#ifdef __cplusplus
}
#endif

#endif /* __MOTOR_DRIVER_H__ */
