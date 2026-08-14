# RST 三轴电机控制器固件 — 现状说明

> ⚠️ **本文档此前的标题与内容声称"已完全重构为生产级实时控制系统，可直接上机测试"。该说法不成立，已按代码实测重写。**
> 权威状态文档：`固件真实状态.md`。逐条差异对照：`FIRMWARE_FIX_REPORT.md`。

**工程路径**：`rst-control-fw/control/`（注意：源码已从 `rst-control-fw/Core` 下移到 `control/Core`）
**MCU**：STM32F103ZET6 @ 72MHz（野火霸道开发板）
**构建**：MDK-ARM（`control/MDK-ARM/control.uvprojx`），仅此一种，无 CMake/Makefile
**最后构建**：0 Error 0 Warning，`Code=28156 RO-data=1484 RW-data=24 ZI-data=2768`

---

## 一句话现状

**编译通过，能烧录，串口控制台可交互；但电机不会动、编码器不计数、LED 和按键无反应。**

原因不是硬件，是固件缺少若干初始化调用。详见下面的「烧录后你会看到什么」。

---

## 完成度：约 30%

| 层次 | 完成度 | 说明 |
|---|---|---|
| 工程骨架 / 时钟 / 编译 | ~95% | 能出 hex，Flash 28KB/512KB，RAM 2.7KB/64KB |
| 串口调试控制台 | ~85% | 11 条命令，架构已改为 ISR 入队 + 主循环解析（旧版 ISR 死锁已修复） |
| TB6612 驱动层函数 | ~90% | `motor_driver.c` 四个函数实现完整，但依赖的 GPIO 未初始化 |
| **外设启动（GPIO/PWM/编码器/TIM6）** | **~10%** | **本阶段最大缺口，见下** |
| 电流采样 | ~25% | `HAL_ADC_Start_DMA` 已调用，但配置为非连续模式 + Rank3 通道重复 |
| **位置/速度/电流环** | **0%** | `control_loop.c` 中控制部分是空操作 |
| **归零 / 堵转 / 电流限幅 / 超时 / 看门狗 / 急停** | **0%** | 全部缺失 |
| **`P<>U<>L<>` 串口协议** | **0%** | 关键字全仓库零命中 |
| CAN | ~10% | 仅 Init，无 Start / 无滤波器，且波特率实为 562.5kbps |

BSP 层约 60%，应用层约 0~5%。

---

## 烧录后你会看到什么

### 能正常工作 ✅
- 串口 115200 输出启动横幅（`=== RST Control Firmware ===` + Build 时间戳）
- `help`、`info` 正常打印
- `pid 0 3.0 0.05 0.5` 能改写增益（但增益无人使用）
- `can id 5` 能改 `can_node_id` 变量
- `reboot` 正常复位（旧版此命令会死锁，现已修复）

### 不会工作 ❌

| 命令 / 现象 | 原因 |
|---|---|
| `pwm 0 500` 打印成功但**电机不动** | 无 `HAL_TIM_PWM_Start()`，PWM 通道从未使能；且方向脚所在 GPIOB 时钟未开 |
| `enc 0/1/2` 读数**恒为 32768** | 无 `HAL_TIM_Encoder_Start()`，编码器接口从未启动 |
| `info` 里 `Loop Cnt` **恒为 0** | `MX_TIM6_Init()` 从未被调用 → `HAL_TIM_Base_Start_IT` 静默返回 HAL_ERROR → 20kHz 中断从未使能 |
| `info` 里 `ang=4915.20`（静止时） | 编码器计数器预置 32768，但角度换算未减零点偏置 |
| `info` 里 `mA=0` | ADC 非连续模式 + 软件触发，只转换一轮 |
| `info` 里 `CAN ID: 0 (1Mbps)` | `can_node_id` 被硬编码为 0（DIP 读取逻辑丢失）；"1Mbps" 是错的，实际 562.5kbps |
| `led 1 on` **无反应** | GPIOE 时钟未使能，引脚未配置 |
| `btn` **恒显示 UP** | 同上 |
| `dip` 读数**不可信** | PC0~PC3 未配置为上拉输入 |

> 多份操作手册把「`Loop Cnt` 在增加」列为成功标志。**按当前代码这个标志必然无法达成**，请不要据此怀疑硬件或反复重烧。

---

## 三个阻塞问题（按修复顺序）

### 1. `main.c` 缺 `MX_TIM6_Init();`

`main.c:95-104` 的外设初始化列表里没有 TIM6，导致 `htim6.State` 停在 `RESET`，而 `HAL_TIM_Base_Start_IT()` 首行检查 `State != READY` 就直接返回 `HAL_ERROR`。返回值未被检查，属静默失败。

一行修复。

### 2. `gpio.c` 被 CubeMX 重新生成，引脚配置全丢

当前 `MX_GPIO_Init()` 只剩三行时钟使能（GPIOC/A/D），**GPIOB 和 GPIOE 完全没开**，且无任何 `HAL_GPIO_Init()`。于是 6 个方向脚、4 个 LED、2 个按键、4 位拨码全部失效。

旧版这段是手写在生成区内，`.ioc` 的 `DeletePrevious=true` 一次 Generate 就清空了。

修复方式：**写成独立函数 `RST_GPIO_Init()` 放到 `USER CODE BEGIN 2` 之后**，在 `main.c` 显式调用。不要再写回生成区，否则下次生成还会丢。方向脚初始电平应为 Low（TB6612 的 IN1=IN2=L 即 coast），LED 初始为 High（低电平点亮，High=灭）。

### 3. 缺 PWM / 编码器启动调用

补 `HAL_TIM_PWM_Start(&htim1, TIM_CHANNEL_1)`、`HAL_TIM_PWM_Start(&htim8, TIM_CHANNEL_1)`、`HAL_TIM_PWM_Start(&htim8, TIM_CHANNEL_2)` 与 `HAL_TIM_Encoder_Start(&htim2/3/4, TIM_CHANNEL_ALL)`。

---

## 实测引脚映射（以代码为准，不要按注释接线）

`rst_config.h` 顶部的注释与 `tim.c` 实际生成的引脚有出入。**硬件接线请按下表**：

| 功能 | 实际引脚（代码） | `rst_config.h` 注释 | 一致？ |
|---|---|---|---|
| Pitch PWM | PA8 (TIM1_CH1) | PA8 | ✅ |
| 上夹 PWM | PC6 (TIM8_CH1) | PC6 | ✅ |
| 下夹 PWM | PC7 (TIM8_CH2) | PC7 | ✅ |
| Pitch 编码器 | PA6/PA7 (TIM3) | PA6/PA7 | ✅ |
| 上夹 编码器 | **PD12/PD13** (TIM4, remap) | PB6/PB7 | ❌ 按 PD12/PD13 接 |
| 下夹 编码器 | **PA0/PA1** (TIM2, 无 remap) | PA15/PB3 | ❌ 且 PA0 是 WK_UP 按键复用脚，冲突 |
| 方向脚 | PB0/PB1、PB5/PB12、PB13/PB14 | 同 | ✅（但 GPIOB 时钟未开） |
| 电流 ADC | PA4 / PA5 / PA3 | 同 | ✅（但 Rank3 配错，PA5 采不到） |
| LED | PE2~PE5 | 同 | ✅（但 GPIOE 时钟未开） |
| 按键 | PE0/PE1 | 同 | ✅（同上） |
| DIP | PC0~PC3 | 同 | ✅（未配置为输入） |
| USART1 | PA9/PA10 | 同 | ✅ |
| CAN1 | PA11/PA12 | 同 | ✅ |

---

## 技术参数（实测值）

| 项目 | 文档曾声称 | 实测 |
|---|---|---|
| 控制频率 | 20kHz | **0（TIM6 未启动）**；参数本身正确：72MHz/(35+1)/(99+1) = 20kHz |
| PWM 频率 | 1kHz | 1kHz（PSC=71, ARR=999）。⚠️ 与 20kHz 控制环差 20 倍，量级冲突，需重新设计 |
| CAN 波特率 | 1Mbps | **562.5kbps**（APB1=36MHz，Prescaler=4, BS1=13, BS2=2）。`.ioc` 的 `CalculateBaudRate=562500` 证实 |
| 编码器分辨率 | 2400 counts/圈 | 2400（12×4×50），配置正确（TI12 四倍频，ARR=65535，滤波 8） |
| 电流标度 | ~4mA/bit | ~4.03mA/bit，标度正确；但采样链未工作 |
| ADC 采样时间 | 239.5 周期 | **1.5 周期**（0.125µs @ 12MHz）。对 INA180 大概率不足（未实测，高风险） |

---

## 安全状态：当前无任何软件保护

**上电接电机前必须知道**：

- ❌ 无电流限幅（无 `CUR_LIMIT_MA` 之类常量；`Motor_SetPWM` 只限占空比）
- ❌ 无堵转检测（`stalled` / `STATE_STALL` 从未被置位）
- ❌ 无指令超时（占空比一旦设定无限期保持，串口断线也不停）
- ❌ 无看门狗（未启用 IWDG/WWDG）
- ❌ 无软件急停（按键逻辑未实现，且引脚已失效）
- ❌ `Error_Handler` 不关闭 PWM，仅 `__disable_irq()` + 死循环

文档里"堵转保护已激活（1.5A 阈值）"的说法**没有代码依据**，`STALL_CURRENT_MA` 这个宏在工程中根本不存在。

**因此：接电机测试时，唯一可靠的保护是你手上的物理断电开关。** 请务必串一个，并优先用限流电源。

---

## 建议的推进路线

**先做 bring-up 收尾（纯代码，不动 `.ioc`）**
1. 加 `MX_TIM6_Init()` 并检查返回值
2. 恢复 GPIO 配置到 `RST_GPIO_Init()`
3. 补 PWM / 编码器 Start
4. 修编码器零点偏置
5. `Error_Handler` 先刹车

此时才能真正验证：LED 亮、按键读到、拨码读到、手转电机计数变化、`pwm` 命令电机转动、`Loop Cnt` 递增。**这是接电机之前的必要门槛。**

**再改 `.ioc`**（改之前务必先完成第 2 项，否则又被清空）
6. ADC Rank3 → CH5、改连续模式、采样时间 239.5
7. CAN 重算波特率 + 滤波器 + Start
8. TIM2 编码器迁到 PA15/PB3
9. 重定 PWM 频率（建议 16~20kHz）
10. 启用 IWDG

**最后写应用层**
11. **电流限幅 + 堵转检测 + 指令超时（必须先于 PID）**
12. 归零状态机
13. 串级 PID
14. `P<>U<>L<>` 协议（本仓库无完整规格，需另行定义字段单位与应答帧）

---

## 文档导航

| 文档 | 可信度 |
|---|---|
| `固件真实状态.md` | ✅ 权威，实测为准 |
| `FIRMWARE_FIX_REPORT.md` | ✅ 已按实测修正 |
| 本文件 | ✅ 已按实测修正 |
| `CUBEMX_SETUP_GUIDE.md` | ⚠️ 配置步骤可参考，但"验收标准"部分含未实现功能 |
| `接线教程.md`、`00-安全第一.md`、`快速开始*.md`、`01-傻瓜式操作手册.md` | ⚠️ 硬件接线与安全流程可用；凡涉及"Loop Cnt 增加""PID""堵转保护"的成功标志均不成立 |
| `总结-修复完成.txt` | ❌ 通篇为未实现功能的完成声明，已加警示头，建议归档 |
