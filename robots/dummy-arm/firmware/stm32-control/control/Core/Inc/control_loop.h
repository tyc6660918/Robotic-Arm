#ifndef __CONTROL_LOOP_H__
#define __CONTROL_LOOP_H__

#ifdef __cplusplus
extern "C" {
#endif

#include "main.h"
#include "rst_config.h"

/* 启动函数 */
void RST_SafeStartup(void);
void RST_StartControlLoop(void);

/* 控制循环 (20kHz, TIM6 中断调用) */
void RST_ControlLoop20kHz(void);

#ifdef __cplusplus
}
#endif

#endif /* __CONTROL_LOOP_H__ */
