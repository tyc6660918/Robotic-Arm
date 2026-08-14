/**
 ******************************************************************************
 * @file    control_loop.c
 * @brief   RST 20kHz 实时控制循环 - 编码器/PID/电流采样
 *
 * 控制流程:
 *   1. 读编码器 → 计算角度和速度
 *   2. ADC DMA → 读取三路电流
 *   3. 归零状态机 (Homing)
 *   4. PID 位置/速度/力矩控制
 *   5. 堵转检测
 *   6. PWM 输出
 *
 * TIM6 中断频率: 20kHz (50us)
 ******************************************************************************
 */

#include "control_loop.h"
#include "tim.h"
#include "adc.h"
#include <math.h>

/* 全局 RST 系统实例（定义） */
RST_System_t g_rst = {0};

/* ADC DMA 缓冲 (连续采样 3 通道) */
static volatile uint16_t adc_buffer[3];

/* 上次编码器计数 (用于计算速度) */
static int32_t last_enc_cnt[MOTOR_COUNT] = {0};

/*===========================================================================
 * 初始化 - 在 main.c 中调用
 *===========================================================================*/

void RST_SafeStartup(void)
{
    /* 初始化 g_rst 结构体 */
    g_rst.can_node_id = 0;
    g_rst.system_tick_ms = 0;
    g_rst.loop_count = 0;

    for (int i = 0; i < MOTOR_COUNT; i++) {
        /* 清空电机状态 */
        g_rst.motor[i].mode = MODE_STOP;
        g_rst.motor[i].state = STATE_STOP;
        g_rst.motor[i].enabled = false;
        g_rst.motor[i].stalled = false;
        g_rst.motor[i].calibrated = false;
        g_rst.motor[i].goal_angle = 0.0f;
        g_rst.motor[i].goal_current_ma = 0.0f;
        g_rst.motor[i].current_angle = 0.0f;
        g_rst.motor[i].current_velocity = 0.0f;
        g_rst.motor[i].current_ma = 0.0f;
        g_rst.motor[i].pid_integral = 0.0f;
        g_rst.motor[i].pid_last_error = 0.0f;
        g_rst.motor[i].pwm_output = 0;
        g_rst.motor[i].homing = false;
        g_rst.motor[i].homing_step = 0;
        g_rst.motor[i].homing_stall_cnt = 0;
    }

    /* 编码器计数器初值设为中间值, 避免立即溢出 */
    __HAL_TIM_SET_COUNTER(&htim2, 32768);
    __HAL_TIM_SET_COUNTER(&htim3, 32768);
    __HAL_TIM_SET_COUNTER(&htim4, 32768);

    last_enc_cnt[0] = 32768;
    last_enc_cnt[1] = 32768;
    last_enc_cnt[2] = 32768;

    /* 启动 ADC DMA 连续转换 */
    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)adc_buffer, 3);
}

void RST_StartControlLoop(void)
{
    /* 启动 TIM6 20kHz 中断 */
    HAL_TIM_Base_Start_IT(&htim6);
}

/*===========================================================================
 * 编码器读取
 *===========================================================================*/

static void ReadEncoders(void)
{
    TIM_TypeDef *tims[3] = {ENC_PITCH_TIM, ENC_JAWU_TIM, ENC_JAWL_TIM};

    for (int i = 0; i < MOTOR_COUNT; i++) {
        int32_t cnt_now = (int32_t)(tims[i]->CNT);
        int32_t delta = cnt_now - last_enc_cnt[i];

        /* 处理 16 位溢出 */
        if (delta > 32768)  delta -= 65536;
        if (delta < -32768) delta += 65536;

        last_enc_cnt[i] = cnt_now;

        /* 计算角度（度） */
        g_rst.motor[i].current_angle = (float)cnt_now * 360.0f / ENC_COUNTS_PER_REV;

        /* 速度（度/秒） */
        g_rst.motor[i].current_velocity = (float)delta * CONTROL_LOOP_FREQ_HZ * 360.0f / ENC_COUNTS_PER_REV;
    }
}

/*===========================================================================
 * 电流读取 (ADC DMA)
 *===========================================================================*/

static void ReadCurrents(void)
{
    for (int i = 0; i < MOTOR_COUNT; i++) {
        g_rst.motor[i].current_ma = (float)adc_buffer[i] * CUR_SCALE * 1000.0f;
    }
}

/*===========================================================================
 * 20kHz 主控制循环 (在 TIM6 中断中调用)
 *===========================================================================*/

void RST_ControlLoop20kHz(void)
{
    /* 1. 读编码器 */
    ReadEncoders();

    /* 2. 读电流 */
    ReadCurrents();

    /* 3. 简单的位置控制 (TODO: 实现完整的 PID) */
    for (int i = 0; i < MOTOR_COUNT; i++) {
        if (!g_rst.motor[i].enabled) {
            // 禁用状态，刹车
            g_rst.motor[i].pwm_output = 0;
        } else {
            // 完整实现需要 PID 控制器
            g_rst.motor[i].pwm_output = 0;
        }
    }
}
