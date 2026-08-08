/**
 ******************************************************************************
 * @file    debug_console.h
 * @brief   RST 调试串口控制台
 ******************************************************************************
 */

#ifndef __DEBUG_CONSOLE_H
#define __DEBUG_CONSOLE_H

#include "rst_config.h"

void Console_Init(void);
void Console_Process(void);         /* 主循环中调用, 处理输入 */
void Console_Print(const char *fmt, ...);
void Console_Println(const char *fmt, ...);
void Console_PutByte(uint8_t ch);

#endif /* __DEBUG_CONSOLE_H */
