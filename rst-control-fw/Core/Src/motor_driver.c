/**
 ******************************************************************************
 * @file    motor_driver.c
 * @brief   TB6612 双 H 桥驱动 — 3 通道方向 + PWM 控制
 *
 * 硬件映射:
 *   Pitch:  TIM1_CH1 (PA8)  + DIR PB0/PB1
 *   上夹:   TIM8_CH1 (PC6)  + DIR PB5/PB12
 *   下夹:   TIM8_CH2 (PC7)  + DIR PB13/PB14
 *
 * TB6612 真值表 (单通道):
 *   IN1=L  IN2=L  → 惰行 (Coast)  — motor off, free spin
 *   IN1=H  IN2=L  → 正转 (CW)
 *   IN1=L  IN2=H  → 反转 (CCW)
 *   IN1=H  IN2=H  → 短路制动 (Brake)
 ******************************************************************************
 */

#include "rst_config.h"

/*===========================================================================
 * 方向控制
 *===========================================================================*/

void Motor_SetDirection(MotorIndex_t ch, bool forward)
{
    GPIO_TypeDef *port;
    uint16_t pin_in1, pin_in2;

    switch (ch) {
    case MOTOR_PITCH:
        port   = DIR_P_IN1_PORT;
        pin_in1 = DIR_P_IN1_PIN;
        pin_in2 = DIR_P_IN2_PIN;
        break;
    case MOTOR_JAW_UPPER:
        port   = DIR_U_IN1_PORT;
        pin_in1 = DIR_U_IN1_PIN;
        pin_in2 = DIR_U_IN2_PIN;
        break;
    case MOTOR_JAW_LOWER:
        port   = DIR_L_IN1_PORT;
        pin_in1 = DIR_L_IN1_PIN;
        pin_in2 = DIR_L_IN2_PIN;
        break;
    default:
        return;
    }

    if (forward) {
        HAL_GPIO_WritePin(port, pin_in1, GPIO_PIN_SET);   /* IN1=H */
        HAL_GPIO_WritePin(port, pin_in2, GPIO_PIN_RESET); /* IN2=L */
    } else {
        HAL_GPIO_WritePin(port, pin_in1, GPIO_PIN_RESET); /* IN1=L */
        HAL_GPIO_WritePin(port, pin_in2, GPIO_PIN_SET);   /* IN2=H */
    }
}

/*===========================================================================
 * PWM 占空比输出
 *   duty: -1000 ~ +1000, 负值=反转, 正值=正转
 *===========================================================================*/

void Motor_SetPWM(MotorIndex_t ch, int16_t duty)
{
    TIM_HandleTypeDef *htim;
    uint32_t channel;
    bool forward;

    /* 限幅 */
    if (duty > PWM_MAX_DUTY)  duty = PWM_MAX_DUTY;
    if (duty < -PWM_MAX_DUTY) duty = -PWM_MAX_DUTY;

    forward = (duty >= 0);
    uint16_t abs_duty = (uint16_t)(forward ? duty : -duty);

    switch (ch) {
    case MOTOR_PITCH:
        htim    = &PWM_PITCH_TIM;
        channel = PWM_PITCH_CHANNEL;
        break;
    case MOTOR_JAW_UPPER:
        htim    = &PWM_JAWU_TIM;
        channel = PWM_JAWU_CHANNEL;
        break;
    case MOTOR_JAW_LOWER:
        htim    = &PWM_JAWL_TIM;
        channel = PWM_JAWL_CHANNEL;
        break;
    default:
        return;
    }

    /* 方向 */
    Motor_SetDirection(ch, forward);

    /* PWM */
    __HAL_TIM_SET_COMPARE(htim, channel, abs_duty);

    /* 更新全局状态 */
    g_rst.motor[ch].pwm_output = duty;
}

/*===========================================================================
 * 惰行 (Coast) — IN1=L, IN2=L
 *===========================================================================*/

void Motor_Sleep(MotorIndex_t ch)
{
    GPIO_TypeDef *port;
    uint16_t pin_in1, pin_in2;

    switch (ch) {
    case MOTOR_PITCH:
        port   = DIR_P_IN1_PORT;
        pin_in1 = DIR_P_IN1_PIN;
        pin_in2 = DIR_P_IN2_PIN;
        break;
    case MOTOR_JAW_UPPER:
        port   = DIR_U_IN1_PORT;
        pin_in1 = DIR_U_IN1_PIN;
        pin_in2 = DIR_U_IN2_PIN;
        break;
    case MOTOR_JAW_LOWER:
        port   = DIR_L_IN1_PORT;
        pin_in1 = DIR_L_IN1_PIN;
        pin_in2 = DIR_L_IN2_PIN;
        break;
    default:
        return;
    }

    HAL_GPIO_WritePin(port, pin_in1, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(port, pin_in2, GPIO_PIN_RESET);
    g_rst.motor[ch].pwm_output = 0;
}

/*===========================================================================
 * 短路制动 (Brake) — IN1=H, IN2=H
 *===========================================================================*/

void Motor_Brake(MotorIndex_t ch)
{
    GPIO_TypeDef *port;
    uint16_t pin_in1, pin_in2;

    switch (ch) {
    case MOTOR_PITCH:
        port   = DIR_P_IN1_PORT;
        pin_in1 = DIR_P_IN1_PIN;
        pin_in2 = DIR_P_IN2_PIN;
        break;
    case MOTOR_JAW_UPPER:
        port   = DIR_U_IN1_PORT;
        pin_in1 = DIR_U_IN1_PIN;
        pin_in2 = DIR_U_IN2_PIN;
        break;
    case MOTOR_JAW_LOWER:
        port   = DIR_L_IN1_PORT;
        pin_in1 = DIR_L_IN1_PIN;
        pin_in2 = DIR_L_IN2_PIN;
        break;
    default:
        return;
    }

    HAL_GPIO_WritePin(port, pin_in1, GPIO_PIN_SET);
    HAL_GPIO_WritePin(port, pin_in2, GPIO_PIN_SET);
    g_rst.motor[ch].pwm_output = 0;
}
