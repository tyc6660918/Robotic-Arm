/* USER CODE BEGIN Header */
/**
  ******************************************************************************
  * @file    tim6.c
  * @brief   TIM6 初始化 - 20kHz 控制循环定时器
  * @note    TIM6 是基础定时器，用于生成精确的 20kHz 中断
  *          72MHz / 36 / 100 = 20kHz (50us)
  * @note    MspInit/MspDeInit 已在 tim.c 中统一定义，此处仅提供 Init 函数
  ******************************************************************************
  */
/* USER CODE END Header */
/* Includes ------------------------------------------------------------------*/
#include "tim.h"

/* USER CODE BEGIN 0 */

/* USER CODE END 0 */

TIM_HandleTypeDef htim6;

/* TIM6 init function */
void MX_TIM6_Init(void)
{
  /* USER CODE BEGIN TIM6_Init 0 */

  /* USER CODE END TIM6_Init 0 */

  TIM_MasterConfigTypeDef sMasterConfig = {0};

  /* USER CODE BEGIN TIM6_Init 1 */

  /* USER CODE END TIM6_Init 1 */
  htim6.Instance = TIM6;
  htim6.Init.Prescaler = 35;           /* 72MHz / 36 = 2MHz */
  htim6.Init.CounterMode = TIM_COUNTERMODE_UP;
  htim6.Init.Period = 99;              /* 2MHz / 100 = 20kHz */
  htim6.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
  if (HAL_TIM_Base_Init(&htim6) != HAL_OK)
  {
    Error_Handler();
  }
  sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
  sMasterConfig.MasterSlaveMode = TIM_MASTERSLAVEMODE_DISABLE;
  if (HAL_TIMEx_MasterConfigSynchronization(&htim6, &sMasterConfig) != HAL_OK)
  {
    Error_Handler();
  }
  /* USER CODE BEGIN TIM6_Init 2 */

  /* USER CODE END TIM6_Init 2 */

}

/* USER CODE BEGIN 1 */
/* 注意: HAL_TIM_Base_MspInit 和 HAL_TIM_Base_MspDeInit
 * 已在 tim.c 中统一实现，处理所有定时器的 Msp 初始化
 * 包括 TIM6 的时钟使能和中断配置
 */
/* USER CODE END 1 */

