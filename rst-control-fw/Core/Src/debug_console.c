/**
 ******************************************************************************
 * @file    debug_console.c
 * @brief   RST 调试串口控制台 — 命令行解析和交互
 *
 * 支持的命令:
 *   help              — 显示帮助
 *   info              — 显示系统信息
 *   led <1-4> on|off  — 控制 LED
 *   led <1-4> blink   — LED 闪烁测试
 *   btn               — 读按键状态
 *   dip               — 读拨码开关
 *   pwm <0-2> <duty>  — PWM 输出测试 (duty: -1000~1000)
 *   enc <0-2>         — 读编码器计数值
 *   adc <0-2>         — 读电流 ADC (待实现)
 *   can id <new_id>   — 设 CAN Node ID
 *   can send ...      — CAN 测试 (待实现)
 *   pid <0-2> <kp> <ki> <kd> — PID 调参
 *   reboot            — 软件复位
 ******************************************************************************
 */

#include "debug_console.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <ctype.h>

#define RX_BUF_SIZE     128
#define CMD_MAX_TOKENS  12

static uint8_t  rx_buf[RX_BUF_SIZE];
static uint8_t  rx_idx;
static char     cmd_line[RX_BUF_SIZE];

/*===========================================================================
 * 命令表
 *===========================================================================*/
typedef struct {
    const char *name;
    const char *desc;
    void (*handler)(int argc, char **argv);
} Command_t;

static void Cmd_Help(int argc, char **argv);
static void Cmd_Info(int argc, char **argv);
static void Cmd_Led(int argc, char **argv);
static void Cmd_Btn(int argc, char **argv);
static void Cmd_Dip(int argc, char **argv);
static void Cmd_Pwm(int argc, char **argv);
static void Cmd_Enc(int argc, char **argv);
static void Cmd_Adc(int argc, char **argv);
static void Cmd_Can(int argc, char **argv);
static void Cmd_Pid(int argc, char **argv);
static void Cmd_Reboot(int argc, char **argv);

static const Command_t cmd_table[] = {
    {"help",   "显示帮助",                    Cmd_Help},
    {"info",   "系统信息",                    Cmd_Info},
    {"led",    "led <1-4> on|off|blink",      Cmd_Led},
    {"btn",    "读按键状态",                   Cmd_Btn},
    {"dip",    "读拨码开关",                   Cmd_Dip},
    {"pwm",    "pwm <0-2> <duty>",           Cmd_Pwm},
    {"enc",    "enc <0-2> 读编码器",           Cmd_Enc},
    {"adc",    "adc <0-2> 读电流ADC",         Cmd_Adc},
    {"can",    "can id|send  CAN测试",         Cmd_Can},
    {"pid",    "pid <0-2> <kp> <ki> <kd>",    Cmd_Pid},
    {"reboot", "软件复位",                     Cmd_Reboot},
    {NULL, NULL, NULL}
};

/*===========================================================================
 * UART 输出
 *===========================================================================*/

int _write(int file, char *ptr, int len)
{
    (void)file;
    HAL_UART_Transmit(&huart1, (uint8_t*)ptr, (uint16_t)len, 100);
    return len;
}

void Console_Print(const char *fmt, ...)
{
    char buf[256];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    HAL_UART_Transmit(&huart1, (uint8_t*)buf, (uint16_t)strlen(buf), 100);
}

void Console_Println(const char *fmt, ...)
{
    char buf[256];
    va_list args;
    va_start(args, fmt);
    int len = vsnprintf(buf, sizeof(buf) - 2, fmt, args);
    va_end(args);
    buf[len++] = '\r';
    buf[len++] = '\n';
    HAL_UART_Transmit(&huart1, (uint8_t*)buf, (uint16_t)len, 100);
}

void Console_PutByte(uint8_t ch)
{
    HAL_UART_Transmit(&huart1, &ch, 1, 10);
}

/*===========================================================================
 * 初始化
 *===========================================================================*/

void Console_Init(void)
{
    rx_idx = 0;
    memset(rx_buf, 0, sizeof(rx_buf));
    memset(cmd_line, 0, sizeof(cmd_line));

    HAL_UART_Receive_IT(&huart1, &rx_buf[rx_idx], 1);

    Console_Println("");
    Console_Println("========================================");
    Console_Println("  RST Motor Controller - Debug Console");
    Console_Println("  STM32F103ZET6  |  3-Axis DC Motor");
    Console_Println("========================================");
    Console_Println("  CAN ID=%d  |  输入 help 查看命令", g_rst.can_node_id);
    Console_Print("> ");
}

/*===========================================================================
 * RX 中断处理 — 在 HAL_UART_RxCpltCallback 中调用
 *===========================================================================*/

void Console_RxCallback(void)
{
    uint8_t ch = rx_buf[rx_idx];

    /* 回显可打印字符 */
    if (ch >= 32 && ch < 127) {
        Console_PutByte(ch);
    } else if (ch == '\r') {
        Console_PutByte('\r');
        Console_PutByte('\n');
    }

    if (ch == '\r' || ch == '\n') {
        if (rx_idx > 0) {
            rx_buf[rx_idx] = '\0';
            memcpy(cmd_line, rx_buf, rx_idx + 1);
        }
        rx_idx = 0;
        memset(rx_buf, 0, sizeof(rx_buf));

        if (cmd_line[0] != '\0') {
            Console_Process();
        }
        Console_Print("> ");
    } else if (ch == '\b' || ch == 0x7F) {
        if (rx_idx > 0) {
            rx_idx--;
        }
    } else if (ch >= 32 && ch < 127) {
        if (rx_idx < RX_BUF_SIZE - 2) {
            rx_idx++;
        }
    }

    HAL_UART_Receive_IT(&huart1, &rx_buf[rx_idx], 1);
}

/*===========================================================================
 * 命令解析
 *===========================================================================*/

void Console_Process(void)
{
    if (cmd_line[0] == '\0') return;

    char *argv[CMD_MAX_TOKENS];
    int argc = 0;

    /* 简单分词 (空格分隔) */
    char *p = cmd_line;
    while (*p && argc < CMD_MAX_TOKENS) {
        while (*p == ' ' || *p == '\t') p++;
        if (*p == '\0') break;
        argv[argc++] = p;
        while (*p && *p != ' ' && *p != '\t') p++;
        if (*p) { *p = '\0'; p++; }
    }

    if (argc == 0) return;

    /* 大小写不敏感查找 */
    for (int i = 0; cmd_table[i].name != NULL; i++) {
        /* 手动比较 (避免 strcasecmp 在 MicroLIB 中不存在) */
        const char *a = argv[0];
        const char *b = cmd_table[i].name;
        int match = 1;
        while (*a && *b) {
            if (tolower((unsigned char)*a) != tolower((unsigned char)*b)) {
                match = 0;
                break;
            }
            a++; b++;
        }
        if (match && *a == '\0' && *b == '\0') {
            cmd_table[i].handler(argc, argv);
            return;
        }
    }

    Console_Println("  未知命令: %s", argv[0]);
}

/*===========================================================================
 * 命令实现
 *===========================================================================*/

static void Cmd_Help(int argc, char **argv)
{
    (void)argc; (void)argv;
    Console_Println("  --- 可用命令 ---");
    for (int i = 0; cmd_table[i].name != NULL; i++) {
        Console_Println("  %-8s — %s", cmd_table[i].name, cmd_table[i].desc);
    }
}

static void Cmd_Info(int argc, char **argv)
{
    (void)argc; (void)argv;
    Console_Println("  --- 系统信息 ---");
    Console_Println("  MCU:       STM32F103ZET6 @ 72MHz");
    Console_Println("  UART:      USART1 @ %lu bps", (unsigned long)DBG_UART_BAUD);
    Console_Println("  CAN ID:    %d (1Mbps)", g_rst.can_node_id);
    Console_Println("  Loop Cnt:  %lu", (unsigned long)g_rst.loop_count);
    Console_Println("  Motors:    %d (0=Pitch 1=UpperJaw 2=LowerJaw)", MOTOR_COUNT);

    Console_Println("");
    Console_Println("  --- 电机状态 ---");
    const char *names[] = {"Pitch", "UpJaw", "LoJaw"};
    const char *states[] = {"STOP","RUN","FINISH","STALL","NOCAL","ERR"};
    for (int i = 0; i < MOTOR_COUNT; i++) {
        Motor_t *m = &g_rst.motor[i];
        Console_Println("  [%d] %-6s: mode=%d st=%s ang=%.2f mA=%.0f pwm=%d",
            i, names[i], (int)m->mode, states[m->state],
            (double)m->current_angle, (double)m->current_ma, m->pwm_output);
    }
}

static void Cmd_Led(int argc, char **argv)
{
    if (argc < 2) {
        Console_Println("  用法: led <1-4> on|off|blink");
        return;
    }
    int led = atoi(argv[1]);
    if (led < 1 || led > 4) { Console_Println("  LED 编号 1~4"); return; }

    uint16_t pin;
    switch (led) {
        case 1: pin = LED_P_PIN;   break;
        case 2: pin = LED_U_PIN;   break;
        case 3: pin = LED_L_PIN;   break;
        case 4: pin = LED_SYS_PIN; break;
        default: return;
    }

    if (argc >= 3 && strcmp(argv[2], "on") == 0) {
        LED_ON(pin);
        Console_Println("  LED%d = ON", led);
    } else if (argc >= 3 && strcmp(argv[2], "off") == 0) {
        LED_OFF(pin);
        Console_Println("  LED%d = OFF", led);
    } else if (argc >= 3 && strcmp(argv[2], "blink") == 0) {
        for (int i = 0; i < 5; i++) {
            LED_ON(pin);  HAL_Delay(150);
            LED_OFF(pin); HAL_Delay(150);
        }
        Console_Println("  LED%d 闪烁 5 次完成", led);
    } else {
        GPIO_PinState st = HAL_GPIO_ReadPin(LED_ALL_PORT, pin);
        Console_Println("  LED%d = %s", led, (st == GPIO_PIN_RESET) ? "ON" : "OFF");
    }
}

static void Cmd_Btn(int argc, char **argv)
{
    (void)argc; (void)argv;
    int b1 = (HAL_GPIO_ReadPin(BTN1_PORT, BTN1_PIN) == GPIO_PIN_RESET) ? 1 : 0;
    int b2 = (HAL_GPIO_ReadPin(BTN2_PORT, BTN2_PIN) == GPIO_PIN_RESET) ? 1 : 0;
    Console_Println("  BTN1=%s  BTN2=%s",
        b1 ? "PRESSED" : "UP",
        b2 ? "PRESSED" : "UP");
}

static void Cmd_Dip(int argc, char **argv)
{
    (void)argc; (void)argv;
    /* 上拉输入: 闭合=低电平=1, 断开=高电平=0 */
    uint8_t dip = 0;
    if (HAL_GPIO_ReadPin(DIP_PORT, DIP_PIN_0) == GPIO_PIN_RESET) dip |= 1;
    if (HAL_GPIO_ReadPin(DIP_PORT, DIP_PIN_1) == GPIO_PIN_RESET) dip |= 2;
    if (HAL_GPIO_ReadPin(DIP_PORT, DIP_PIN_2) == GPIO_PIN_RESET) dip |= 4;
    if (HAL_GPIO_ReadPin(DIP_PORT, DIP_PIN_3) == GPIO_PIN_RESET) dip |= 8;
    Console_Println("  DIP = %d (0x%02X)", dip, dip);
}

static void Cmd_Pwm(int argc, char **argv)
{
    if (argc < 3) {
        Console_Println("  用法: pwm <0-2> <duty>  (duty: -1000 ~ +1000)");
        Console_Println("  0=Pitch  1=上夹  2=下夹");
        return;
    }
    int ch = atoi(argv[1]);
    int duty = atoi(argv[2]);

    if (ch < 0 || ch > 2) { Console_Println("  通道 0/1/2"); return; }

    Motor_SetPWM((MotorIndex_t)ch, (int16_t)duty);
    Console_Println("  PWM[%d] = %d", ch, g_rst.motor[ch].pwm_output);
}

static void Cmd_Enc(int argc, char **argv)
{
    if (argc < 2) {
        Console_Println("  用法: enc <0-2>  (0=Pitch 1=上夹 2=下夹)");
        return;
    }
    int ch = atoi(argv[1]);
    if (ch < 0 || ch > 2) return;

    TIM_TypeDef *tim;
    switch (ch) {
        case 0: tim = ENC_PITCH_TIM; break;
        case 1: tim = ENC_JAWU_TIM;  break;
        case 2: tim = ENC_JAWL_TIM;  break;
        default: return;
    }

    int32_t cnt = (int32_t)(tim->CNT);
    float angle = (float)cnt * 360.0f / (float)ENC_COUNTS_PER_REV;

    Console_Println("  Enc[%d] CNT=%ld  Angle=%.2f deg", ch, (long)cnt, (double)angle);
}

static void Cmd_Adc(int argc, char **argv)
{
    (void)argc; (void)argv;
    Console_Println("  [ADC] 待实现 — 连好 INA180 后通过 DMA 读取");
    Console_Println("  当前 CUR_SCALE = %.4f A/bit", (double)CUR_SCALE);
}

static void Cmd_Can(int argc, char **argv)
{
    if (argc < 2) {
        Console_Println("  用法:");
        Console_Println("    can id <0-15>         — 设 CAN Node ID");
        Console_Println("    can send <id> <d0..d7> — 发送 CAN 帧 (待实现)");
        return;
    }

    if (strcmp(argv[1], "id") == 0 && argc >= 3) {
        int id = atoi(argv[2]);
        if (id < 0 || id > 15) { Console_Println("  ID 范围 0~15"); return; }
        g_rst.can_node_id = (uint8_t)id;
        Console_Println("  CAN Node ID → %d", id);
    } else if (strcmp(argv[1], "send") == 0) {
        Console_Println("  [CAN] 发送功能待实现");
    } else {
        Console_Println("  未知子命令: %s", argv[1]);
    }
}

static void Cmd_Pid(int argc, char **argv)
{
    if (argc < 5) {
        Console_Println("  用法: pid <0-2> <kp> <ki> <kd>");
        return;
    }
    int ch = atoi(argv[1]);
    if (ch < 0 || ch > 2) return;

    g_rst.motor[ch].pid.kp = (float)atof(argv[2]);
    g_rst.motor[ch].pid.ki = (float)atof(argv[3]);
    g_rst.motor[ch].pid.kd = (float)atof(argv[4]);
    g_rst.motor[ch].pid_integral = 0.0f;

    Console_Println("  Motor[%d] PID: kp=%.2f ki=%.4f kd=%.2f",
        ch,
        (double)g_rst.motor[ch].pid.kp,
        (double)g_rst.motor[ch].pid.ki,
        (double)g_rst.motor[ch].pid.kd);
}

static void Cmd_Reboot(int argc, char **argv)
{
    (void)argc; (void)argv;
    Console_Println("  软件复位...");
    HAL_Delay(100);
    NVIC_SystemReset();
}
