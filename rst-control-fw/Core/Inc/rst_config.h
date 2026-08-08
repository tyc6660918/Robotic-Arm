/**
 ******************************************************************************
 * @file    rst_config.h
 * @brief   RST 三电机控制板 - 硬件配置 (修订版 v3)
 * @note    STM32F103ZET6 (LQFP-144)
 *
 * 引脚分配:
 *   USART1: PA9(TX)  PA10(RX)   — 板载 USB-UART 调试口
 *   CAN1:   PA11(RX) PA12(TX)   — 默认引脚, 无需 Remap
 *   PWM:    PA8(TIM1_CH1)  PC6(TIM8_CH1)  PC7(TIM8_CH2)
 *   Encoder:PA6/PA7(TIM3) PB6/PB7(TIM4) PA15/PB3(TIM2_Remap)
 *   Dir:    PB0/1  PB5/PB12  PB13/PB14
 *   LED:    PE2~5   BTN:PE0/1   DIP:PC0~3
 *   SWD:    PA13/PA14  (禁用 JTAG, PA15/PB3 释放给 TIM2)
 ******************************************************************************
 */

#ifndef __RST_CONFIG_H
#define __RST_CONFIG_H

#ifdef __cplusplus
extern "C" {
#endif

#include "stm32f1xx_hal.h"
#include <stdbool.h>
#include <stdint.h>

/*===========================================================================
 * 系统参数
 *===========================================================================*/
#define SYSTEM_CLOCK_HZ         72000000U
#define CONTROL_LOOP_FREQ_HZ    20000U
#define CONTROL_LOOP_PERIOD_US  50U

/*===========================================================================
 * UART 调试串口 (USART1 — 板载 CH340/CP2102 直连)
 * PA9  = TX,  PA10 = RX
 *===========================================================================*/
#define DBG_UART                USART1
#define DBG_UART_BAUD           115200U

/*===========================================================================
 * CAN 总线 (CAN1 — 默认引脚, 无需 Remap)
 * PA11 = RX,  PA12 = TX
 *===========================================================================*/
#define CANx                    CAN1
#define CAN_BAUD_RATE           1000000U    /* 1Mbps */
#define CAN_NODE_ID_DEFAULT     8U

/*===========================================================================
 * PWM 输出
 *
 * PA8  = TIM1_CH1  → TB6612#1 CH1 (Pitch 电机)
 * PC6  = TIM8_CH1  → TB6612#1 CH2 (上夹 电机)
 * PC7  = TIM8_CH2  → TB6612#2 CH1 (下夹 电机)
 *
 * 方向脚 (GPIO 推挽输出):
 * PB0  = Pitch  IN1     PB1  = Pitch  IN2
 * PB5  = 上夹   IN1     PB12 = 上夹   IN2
 * PB13 = 下夹   IN1     PB14 = 下夹   IN2
 *===========================================================================*/
#define PWM_ARR                 999U
#define PWM_MAX_DUTY            1000

/* --- PWM 通道参数 (供驱动层使用) --- */
/* Pitch: TIM1_CH1 */
#define PWM_PITCH_TIM           htim1
#define PWM_PITCH_CHANNEL       TIM_CHANNEL_1
/* 上夹: TIM8_CH1 */
#define PWM_JAWU_TIM            htim8
#define PWM_JAWU_CHANNEL        TIM_CHANNEL_1
/* 下夹: TIM8_CH2 */
#define PWM_JAWL_TIM            htim8
#define PWM_JAWL_CHANNEL        TIM_CHANNEL_2

/* 方向脚 */
#define DIR_P_IN1_PORT          GPIOB
#define DIR_P_IN1_PIN           GPIO_PIN_0
#define DIR_P_IN2_PORT          GPIOB
#define DIR_P_IN2_PIN           GPIO_PIN_1

#define DIR_U_IN1_PORT          GPIOB
#define DIR_U_IN1_PIN           GPIO_PIN_5
#define DIR_U_IN2_PORT          GPIOB
#define DIR_U_IN2_PIN           GPIO_PIN_12

#define DIR_L_IN1_PORT          GPIOB
#define DIR_L_IN1_PIN           GPIO_PIN_13
#define DIR_L_IN2_PORT          GPIOB
#define DIR_L_IN2_PIN           GPIO_PIN_14

/*===========================================================================
 * 编码器输入 (定时器编码器模式, 4 倍频)
 *
 * TIM3: PA6=CH1, PA7=CH2  → GMR0 (Pitch 电机编码器)
 * TIM4: PB6=CH1, PB7=CH2  → GMR1 (上夹 电机编码器)
 * TIM2: PA15=CH1, PB3=CH2 → GMR2 (下夹 电机编码器)
 *        ▲ TIM2 部分重映射 (Remap=Partial)
 *        ⚠️ 需禁用 JTAG, 仅保留 SWD (PA13/PA14)
 *===========================================================================*/
/* Pitch 编码器 */
#define ENC_PITCH_TIM           TIM3

/* 上夹 编码器 */
#define ENC_JAWU_TIM            TIM4

/* 下夹 编码器 (TIM2 Partial Remap → PA15/PB3) */
#define ENC_JAWL_TIM            TIM2

/* GMR 编码器参数 (MG310L + 减速比 1:50 + 12 线) */
#define ENC_CPR                 12U
#define ENC_REDUCTION           50U
#define ENC_COUNTS_PER_REV      ((int32_t)(ENC_CPR) * 4 * (int32_t)(ENC_REDUCTION))

/*===========================================================================
 * 电流检测 ADC (ADC1, 3 通道)
 * PA4 = ADC1_CH4  → Pitch 电流 (INA180A1, 0.1Ω, 增益 20)
 * PA5 = ADC1_CH5  → 上夹 电流
 * PA3 = ADC1_CH3  → 下夹 电流
 *===========================================================================*/
#define ADC_CUR                  ADC1
#define ADC_CUR_PITCH_RANK      1U
#define ADC_CUR_JAWU_RANK       2U
#define ADC_CUR_JAWL_RANK       3U

#define CUR_SHUNT_OHM           0.1f
#define CUR_AMP_GAIN            20.0f
#define CUR_ADC_VREF            3.3f
#define CUR_ADC_RES             4096.0f
#define CUR_SCALE               (CUR_ADC_VREF / CUR_ADC_RES / CUR_SHUNT_OHM / CUR_AMP_GAIN)
/* CUR_SCALE ≈ 0.00403 A/bit ≈ 4mA/bit */

/*===========================================================================
 * 拨码开关 (4pin → CAN Node ID 0~15)
 * PC0~PC3 = DIP1~DIP4  (上拉输入, ON=闭合=低电平)
 *===========================================================================*/
#define DIP_PORT                GPIOC
#define DIP_PIN_0               GPIO_PIN_0
#define DIP_PIN_1               GPIO_PIN_1
#define DIP_PIN_2               GPIO_PIN_2
#define DIP_PIN_3               GPIO_PIN_3
#define DIP_MASK                (DIP_PIN_0 | DIP_PIN_1 | DIP_PIN_2 | DIP_PIN_3)

/*===========================================================================
 * 按键 (2个, 上拉输入)
 * PE0 = BTN1 (短按=启停, 长按 2s=编码器校准)
 * PE1 = BTN2 (短按=清 STALL, 长按=归零)
 *===========================================================================*/
#define BTN1_PORT               GPIOE
#define BTN1_PIN                GPIO_PIN_0
#define BTN2_PORT               GPIOE
#define BTN2_PIN                GPIO_PIN_1

/*===========================================================================
 * LED 指示灯 (4个, 推挽输出, 低电平亮)
 * PE2 = Pitch 状态   PE3 = 上夹 状态
 * PE4 = 下夹 状态    PE5 = 系统心跳
 *===========================================================================*/
#define LED_ALL_PORT            GPIOE
#define LED_P_PIN               GPIO_PIN_2
#define LED_U_PIN               GPIO_PIN_3
#define LED_L_PIN               GPIO_PIN_4
#define LED_SYS_PIN             GPIO_PIN_5
#define LED_ALL_PINS            (LED_P_PIN|LED_U_PIN|LED_L_PIN|LED_SYS_PIN)

#define LED_ON(pin)             HAL_GPIO_WritePin(LED_ALL_PORT, (pin), GPIO_PIN_RESET)
#define LED_OFF(pin)            HAL_GPIO_WritePin(LED_ALL_PORT, (pin), GPIO_PIN_SET)
#define LED_TOGGLE(pin)         HAL_GPIO_TogglePin(LED_ALL_PORT, (pin))

/*===========================================================================
 * 电机编号
 *===========================================================================*/
typedef enum {
    MOTOR_PITCH = 0,
    MOTOR_JAW_UPPER = 1,
    MOTOR_JAW_LOWER = 2,
    MOTOR_COUNT = 3
} MotorIndex_t;

/*===========================================================================
 * 电机状态和控制模式
 *===========================================================================*/
typedef enum {
    STATE_STOP = 0,
    STATE_RUNNING,
    STATE_FINISH,
    STATE_STALL,
    STATE_NO_CALIB,
    STATE_ERROR
} MotorState_t;

typedef enum {
    MODE_STOP = 0,
    MODE_POSITION,
    MODE_VELOCITY,
    MODE_CURRENT
} MotorMode_t;

/*===========================================================================
 * PID 参数
 *===========================================================================*/
typedef struct {
    float kp;
    float ki;
    float kd;
    float integral_limit;
    float output_limit;
} PID_Params_t;

/*===========================================================================
 * 单电机运行时数据
 *===========================================================================*/
typedef struct {
    MotorMode_t    mode;
    MotorState_t   state;
    bool           enabled;
    bool           stalled;
    bool           calibrated;

    float          goal_angle;       /* 度 */
    float          goal_current_ma;  /* mA */
    float          current_angle;    /* 度 */
    float          current_velocity; /* 度/秒 */
    float          current_ma;       /* mA */

    PID_Params_t   pid;
    float          pid_integral;
    float          pid_last_error;
    int16_t        pwm_output;       /* -1000 ~ +1000 */

    bool           homing;
    uint8_t        homing_step;
    uint32_t       homing_stall_cnt;
} Motor_t;

/*===========================================================================
 * 全局系统
 *===========================================================================*/
typedef struct {
    Motor_t    motor[MOTOR_COUNT];
    uint8_t    can_node_id;
    uint32_t   system_tick_ms;
    uint32_t   loop_count;
} RST_System_t;

extern RST_System_t g_rst;

/*===========================================================================
 * 外部句柄 (CubeMX 在 tim.c / can.c / adc.c 中定义)
 *===========================================================================*/
extern TIM_HandleTypeDef  htim1;
extern TIM_HandleTypeDef  htim2;
extern TIM_HandleTypeDef  htim3;
extern TIM_HandleTypeDef  htim4;
extern TIM_HandleTypeDef  htim8;
extern CAN_HandleTypeDef  hcan;
extern ADC_HandleTypeDef  hadc1;
extern UART_HandleTypeDef huart1;

/*===========================================================================
 * API
 *===========================================================================*/
void RST_Loop1kHz(void);
void RST_ControlLoop20kHz(void);
void Console_RxCallback(void);

/* 方向/PWM 辅助 — 接好 TB6612 后展开 */
void Motor_SetDirection(MotorIndex_t ch, bool forward);
void Motor_SetPWM(MotorIndex_t ch, int16_t duty);
void Motor_Sleep(MotorIndex_t ch);
void Motor_Brake(MotorIndex_t ch);

#ifdef __cplusplus
}
#endif
#endif /* __RST_CONFIG_H */
