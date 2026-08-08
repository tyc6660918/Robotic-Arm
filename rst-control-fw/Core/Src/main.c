/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file           : main.c
  * @brief          : Main program body
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2026 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "main.h"
#include "adc.h"
#include "can.h"
#include "dma.h"
#include "tim.h"
#include "usart.h"
#include "gpio.h"

/* Private includes ----------------------------------------------------------*/
/* USER CODE BEGIN Includes */
#include "rst_config.h"
#include "debug_console.h"
#include <string.h>
#include <stdio.h>
/* USER CODE END Includes */

/* Private typedef -----------------------------------------------------------*/
/* USER CODE BEGIN PTD */

/* USER CODE END PTD */

/* Private define ------------------------------------------------------------*/
/* USER CODE BEGIN PD */

/* USER CODE END PD */

/* Private macro -------------------------------------------------------------*/
/* USER CODE BEGIN PM */

/* USER CODE END PM */

/* Private variables ---------------------------------------------------------*/

/* USER CODE BEGIN PV */
RST_System_t g_rst;
static uint8_t btn1_last = 1, btn2_last = 1;
/* USER CODE END PV */

/* Private function prototypes -----------------------------------------------*/
void SystemClock_Config(void);
/* USER CODE BEGIN PFP */
static void MotorDefaults_Init(void);
static void LED_StartupBlink(void);
static uint8_t DIP_Read(void);
void RST_Loop1kHz(void);
void RST_ControlLoop20kHz(void);
/* USER CODE END PFP */

/* Private user code ---------------------------------------------------------*/
/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

/**
  * @brief  The application entry point.
  * @retval int
  */
int main(void)
{

  /* USER CODE BEGIN 1 */

  /* USER CODE END 1 */

  /* MCU Configuration--------------------------------------------------------*/

  /* Reset of all peripherals, Initializes the Flash interface and the Systick. */
  HAL_Init();

  /* USER CODE BEGIN Init */

  /* USER CODE END Init */

  /* Configure the system clock */
  SystemClock_Config();

  /* USER CODE BEGIN SysInit */

  /* USER CODE END SysInit */

  /* Initialize all configured peripherals */
  MX_GPIO_Init();
  MX_DMA_Init();
  MX_ADC1_Init();
  MX_CAN_Init();
  MX_TIM1_Init();
  MX_TIM2_Init();
  MX_TIM3_Init();
  MX_TIM4_Init();
  MX_TIM8_Init();
  MX_USART1_UART_Init();
  /* USER CODE BEGIN 2 */
  MotorDefaults_Init();

  /* Read DIP switch */
  uint8_t dip = DIP_Read();
  g_rst.can_node_id = (dip == 0) ? CAN_NODE_ID_DEFAULT : dip;

  /* Start PWM (must be after timer init) */
  HAL_TIM_PWM_Start(&PWM_PITCH_TIM, PWM_PITCH_CHANNEL);
  HAL_TIM_PWM_Start(&PWM_JAWU_TIM,  PWM_JAWU_CHANNEL);
  HAL_TIM_PWM_Start(&PWM_JAWL_TIM,  PWM_JAWL_CHANNEL);

  /* Start encoder timers */
  HAL_TIM_Encoder_Start(&htim2, TIM_CHANNEL_ALL);
  HAL_TIM_Encoder_Start(&htim3, TIM_CHANNEL_ALL);
  HAL_TIM_Encoder_Start(&htim4, TIM_CHANNEL_ALL);

  /* Start CAN */
  HAL_CAN_Start(&hcan);

  /* LED self-test */
  LED_StartupBlink();

  /* Init debug console */
  Console_Init();
  /* USER CODE END 2 */

  /* Infinite loop */
  /* USER CODE BEGIN WHILE */
  uint32_t last_1khz_tick = 0;
  uint32_t last_led_toggle = 0;

  while (1)
  {
    uint32_t now = HAL_GetTick();

    /* ---- 1kHz slow tasks ---- */
    if (now - last_1khz_tick >= 1) {
      last_1khz_tick = now;
      g_rst.system_tick_ms++;

      if (now - last_led_toggle >= 500) {
        last_led_toggle = now;
        LED_TOGGLE(LED_SYS_PIN);
      }

      /* Button scan (falling edge) */
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
}

/**
  * @brief System Clock Configuration
  * @retval None
  */
void SystemClock_Config(void)
{
  RCC_OscInitTypeDef RCC_OscInitStruct = {0};
  RCC_ClkInitTypeDef RCC_ClkInitStruct = {0};
  RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

  /** Initializes the RCC Oscillators according to the specified parameters
  * in the RCC_OscInitTypeDef structure.
  */
  RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE;
  RCC_OscInitStruct.HSEState = RCC_HSE_ON;
  RCC_OscInitStruct.HSEPredivValue = RCC_HSE_PREDIV_DIV1;
  RCC_OscInitStruct.HSIState = RCC_HSI_ON;
  RCC_OscInitStruct.PLL.PLLState = RCC_PLL_ON;
  RCC_OscInitStruct.PLL.PLLSource = RCC_PLLSOURCE_HSE;
  RCC_OscInitStruct.PLL.PLLMUL = RCC_PLL_MUL9;
  if (HAL_RCC_OscConfig(&RCC_OscInitStruct) != HAL_OK)
  {
    Error_Handler();
  }

  /** Initializes the CPU, AHB and APB buses clocks
  */
  RCC_ClkInitStruct.ClockType = RCC_CLOCKTYPE_HCLK|RCC_CLOCKTYPE_SYSCLK
                              |RCC_CLOCKTYPE_PCLK1|RCC_CLOCKTYPE_PCLK2;
  RCC_ClkInitStruct.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
  RCC_ClkInitStruct.AHBCLKDivider = RCC_SYSCLK_DIV1;
  RCC_ClkInitStruct.APB1CLKDivider = RCC_HCLK_DIV2;
  RCC_ClkInitStruct.APB2CLKDivider = RCC_HCLK_DIV1;

  if (HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_2) != HAL_OK)
  {
    Error_Handler();
  }
  PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_ADC;
  PeriphClkInit.AdcClockSelection = RCC_ADCPCLK2_DIV6;
  if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit) != HAL_OK)
  {
    Error_Handler();
  }
}

/* USER CODE BEGIN 4 */

static void MotorDefaults_Init(void)
{
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
 * @brief  Read 4-bit DIP switch
 * @return 0~15 (closed=1, open=0)
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

void RST_Loop1kHz(void)
{
    /* Placeholder: EEPROM / CAN heartbeat / status report */
}

void RST_ControlLoop20kHz(void)
{
    for (int i = 0; i < MOTOR_COUNT; i++) {
        Motor_t *m = &g_rst.motor[i];
        (void)m;
        /*
         * TODO: Full control chain:
         * 1. Read TIMx->CNT, angle = CNT*360/ENC_COUNTS_PER_REV
         * 2. Velocity = (angle - last_angle) * CONTROL_LOOP_FREQ_HZ
         * 3. ADC DMA buffer -> current mA
         * 4. Homing state machine
         * 5. PID: err = goal - angle; out = kp*err + ki*integral_err + kd*d(err)/dt
         * 6. Motor_SetPWM(i, out)
         * 7. Stall detection
         */
    }
}
/* USER CODE END 4 */

/**
  * @brief  This function is executed in case of error occurrence.
  * @retval None
  */
void Error_Handler(void)
{
  /* USER CODE BEGIN Error_Handler_Debug */
  /* User can add his own implementation to report the HAL error return state */
  __disable_irq();
  while (1)
  {
  }
  /* USER CODE END Error_Handler_Debug */
}

#ifdef  USE_FULL_ASSERT
/**
  * @brief  Reports the name of the source file and the source line number
  *         where the assert_param error has occurred.
  * @param  file: pointer to the source file name
  * @param  line: assert_param error line source number
  * @retval None
  */
void assert_failed(uint8_t *file, uint32_t line)
{
  /* USER CODE BEGIN 6 */
  /* User can add his own implementation to report the file name and line number,
     ex: printf("Wrong parameters value: file %s on line %d\r\n", file, line) */
  /* USER CODE END 6 */
}
#endif /* USE_FULL_ASSERT */
