/* USER CODE BEGIN Includes */
#include "rst_config.h"
#include "debug_console.h"
#include <string.h>
#include <stdio.h>
/* USER CODE END Includes */

/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* USER CODE BEGIN PV */
RST_System_t g_rst;
static uint8_t btn1_last = 1, btn2_last = 1;
/* USER CODE END PV */

/* USER CODE BEGIN PFP */
static void MotorDefaults_Init(void);
static void LED_StartupBlink(void);
static uint8_t DIP_Read(void);
/* USER CODE END PFP */

/* USER CODE BEGIN 0 */

static void MotorDefaults_Init(void)
{
    memset(&g_rst, 0, sizeof(g_rst));

    for (int i = 0; i < MOTOR_COUNT; i++) {
        Motor_t *m = &g_rst.motor[i];
        m->mode = MODE_STOP;
        m->state = STATE_NO_CALIB;
        m->enabled = false;
        m->stalled = false;
        m->calibrated = false;
        m->goal_angle = 0.0f;
        m->goal_current_ma = 0.0f;
        m->current_angle = 0.0f;
        m->current_velocity = 0.0f;
        m->pwm_output = 0;
        m->homing = true;

        m->pid.kp = 3.0f;
        m->pid.ki = 0.05f;
        m->pid.kd = 0.5f;
        m->pid.integral_limit = 300.0f;
        m->pid.output_limit = 1000.0f;
        m->pid_integral = 0.0f;
        m->pid_last_error = 0.0f;
    }
}

static void LED_StartupBlink(void)
{
    LED_ON(LED_P_PIN); LED_ON(LED_U_PIN);
    LED_ON(LED_L_PIN); LED_ON(LED_SYS_PIN);
    HAL_Delay(300);
    LED_OFF(LED_P_PIN); LED_OFF(LED_U_PIN);
    LED_OFF(LED_L_PIN); LED_OFF(LED_SYS_PIN);
}

/**
 * @brief  读 4 位拨码开关
 * @return 0~15 (闭合=1, 断开=0)
 */
static uint8_t DIP_Read(void)
{
    uint8_t val = 0;
    if (HAL_GPIO_ReadPin(DIP_PORT, DIP_PIN_0) == GPIO_PIN_RESET) val |= 1;
    if (HAL_GPIO_ReadPin(DIP_PORT, DIP_PIN_1) == GPIO_PIN_RESET) val |= 2;
    if (HAL_GPIO_ReadPin(DIP_PORT, DIP_PIN_2) == GPIO_PIN_RESET) val |= 4;
    if (HAL_GPIO_ReadPin(DIP_PORT, DIP_PIN_3) == GPIO_PIN_RESET) val |= 8;
    return val;
}
/* USER CODE END 0 */

/* USER CODE BEGIN 1 */
/* (HAL_Init 之前的初始化 — 留空) */
/* USER CODE END 1 */

/* USER CODE BEGIN Init */
/* (HAL_Init 之后, 时钟配置之前 — 留空) */
/* USER CODE END Init */

/* USER CODE BEGIN SysInit */
/* (时钟配置之后, 外设初始化之前 — 留空) */
/* USER CODE END SysInit */

/* USER CODE BEGIN 2 */
  MotorDefaults_Init();

  /* 读拨码开关 */
  uint8_t dip = DIP_Read();
  g_rst.can_node_id = (dip == 0) ? CAN_NODE_ID_DEFAULT : dip;

  /* 启动 PWM (在定时器初始化后才能输出) */
  HAL_TIM_PWM_Start(&PWM_PITCH_TIM, PWM_PITCH_CHANNEL);
  HAL_TIM_PWM_Start(&PWM_JAWU_TIM,  PWM_JAWU_CHANNEL);
  HAL_TIM_PWM_Start(&PWM_JAWL_TIM,  PWM_JAWL_CHANNEL);

  /* 编码器启动 */
  HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
  HAL_TIM_Encoder_Start(&htim3, TIM_CHANNEL_ALL);
  HAL_TIM_Encoder_Start(&htim4, TIM_CHANNEL_ALL);

  /* CAN 启动 */
  HAL_CAN_Start(&hcan1);

  /* LED 自检 */
  LED_StartupBlink();

  /* 控制台 */
  Console_Init();
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
  uint32_t last_1khz_tick = 0;
  uint32_t last_led_toggle = 0;

  while (1)
  {
    uint32_t now = HAL_GetTick();

    /* ---- 1kHz 慢速任务 ---- */
    if (now - last_1khz_tick >= 1) {
      last_1khz_tick = now;
      g_rst.system_tick_ms++;

      if (now - last_led_toggle >= 500) {
        last_led_toggle = now;
        LED_TOGGLE(LED_SYS_PIN);
      }

      /* 按键扫描 (下降沿) */
      uint8_t b1 = (HAL_GPIO_ReadPin(BTN1_PORT, BTN1_PIN) == GPIO_PIN_RESET) ? 0 : 1;
      uint8_t b2 = (HAL_GPIO_ReadPin(BTN2_PORT, BTN2_PIN) == GPIO_PIN_RESET) ? 0 : 1;

      if (b1 == 0 && btn1_last == 1) Console_Println("[BTN1]");
      if (b2 == 0 && btn2_last == 1) Console_Println("[BTN2]");
      btn1_last = b1; btn2_last = b2;

      RST_Loop1kHz();
    }

    g_rst.loop_count++;
    /* USER CODE END WHILE */

    /* USER CODE BEGIN 3 */
  }
  /* USER CODE END 3 */

/* USER CODE BEGIN 4 */

void RST_Loop1kHz(void)
{
    /* 占位: EEPROM / CAN 心跳 / 状态上报 */
}

void RST_ControlLoop20kHz(void)
{
    for (int i = 0; i < MOTOR_COUNT; i++) {
        Motor_t *m = &g_rst.motor[i];
        (void)m;
        /*
         * TODO 完整控制链:
         * 1. 读 TIMx->CNT → angle = CNT×360/ENC_COUNTS_PER_REV
         * 2. 速度 = (angle - last_angle) × CONTROL_LOOP_FREQ_HZ
         * 3. ADC DMA 缓冲 → 电流 mA
         * 4. 归零状态机
         * 5. PID: err = goal - angle; out = kp*err + ki*∫err + kd*d(err)/dt
         * 6. Motor_SetPWM(i, out)
         * 7. 堵转/STALL 检测
         */
    }
}
/* USER CODE END 4 */

/* USER CODE BEGIN Error_Handler_Debug */
/* (Error_Handler — 编译时填入或留空) */
/* USER CODE END Error_Handler_Debug */
