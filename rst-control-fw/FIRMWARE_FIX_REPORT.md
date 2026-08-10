# RST 固件重构说明（已按代码实测修正）

> **本文档曾声称实现了 PID、归零状态机、堵转保护、三种控制模式。经逐行核对，这四项在代码中均不存在。**
> 原始声明已在下方标注为「未实现」。完整的实测结论见 `固件真实状态.md`（权威文档）。

日期：2026-08-09
适用：`rst-control-fw/control/`（STM32F103ZET6，MDK-ARM）

---

## 一、本次重构实际做了什么

### 1.1 已确认完成的改动

| 改动 | 证据 | 评价 |
|---|---|---|
| 删除 `app_main.c` | 文件已不存在 | ✅ 真实修复。该文件曾是 `main.c` 的旧副本，引用了不存在的 `hcan1`，加入编译即报错 |
| 控制台改为「ISR 入队 + 主循环解析」 | `main.c:130` 调 `Console_Process()`；`Console_RxCallback()` 只做回显和入队 | ✅ 真实修复。消除了旧版在 USART1 ISR 里调 `HAL_Delay()` 导致的死锁 |
| 新增 `control_loop.c` | 141 行 | ⚠️ 仅传感器读取骨架，无控制算法 |
| 新增 `tim6.c` | 60 行，TIM6 @ 20kHz 参数正确 | ⚠️ `MX_TIM6_Init()` 从未被调用 |
| TIM6 中断链路 | `stm32f1xx_it.c:247` `TIM6_IRQHandler` → `:268` `HAL_TIM_PeriodElapsedCallback` → `RST_ControlLoop20kHz()` | ✅ 接线正确 |
| 调用 `HAL_ADC_Start_DMA` | `control_loop.c:73` | ⚠️ 已调用，但 ADC 配置为非连续模式，只会转换一轮 |
| 编译状态 | `Code=28156 RO-data=1484 RW-data=24 ZI-data=2768`，0 Error 0 Warning | ✅ 干净通过 |

### 1.2 原文档声称「已实现」但代码中不存在的功能

以下五项，我在 `control/` 全目录检索后确认**零实现**：

| 原声明 | 实际情况 |
|---|---|
| ~~PID 控制器（带积分限幅和微分滤波）~~ | **未实现。** `control_loop.c:131-140` 唯一的"控制"是把 `pwm_output` 无条件写 0。`pid_integral` / `pid_last_error` 除清零外从未被读写 |
| ~~归零状态机（堵转检测自动寻零）~~ | **未实现。** `homing_step` / `homing_stall_cnt` 全仓库仅在 `RST_SafeStartup()` 中被清零，无任何状态机 |
| ~~三种控制模式 MODE_POSITION / VELOCITY / CURRENT~~ | **未实现。** 枚举存在于 `rst_config.h:193-198`，但代码中没有任何 `switch(mode)` 分支 |
| ~~堵转保护（电流+速度双重判断）~~ | **未实现。** `stalled` / `STATE_STALL` 从未被置位。文档提到的 `STALL_CURRENT_MA`、`STALL_VELOCITY_LIMIT` 两个宏在代码中**根本没有定义** |
| ~~控制循环 241 行完整实现~~ | 实际 `control_loop.c` 共 **141 行**，其中控制部分 10 行且是空操作 |

---

## 二、当前最关键的三个阻塞问题

### 2.1 🔴 20kHz 控制环一次都不会执行

`MX_TIM6_Init()` 在整个工程里只有 `tim6.c:22` 的定义，**没有任何调用点** —— `main.c:95-104` 的外设初始化列表里没有它：

```c
  MX_GPIO_Init();  MX_DMA_Init();  MX_ADC1_Init();  MX_CAN_Init();
  MX_TIM1_Init();  MX_TIM2_Init();  MX_TIM3_Init();  MX_TIM4_Init();
  MX_TIM8_Init();  MX_USART1_UART_Init();
  /* ← 缺 MX_TIM6_Init(); */
```

因此 `htim6.State` 停在 `HAL_TIM_STATE_RESET`，而 `control_loop.c:79` 调用的 `HAL_TIM_Base_Start_IT()` 首行就是：

```c
  if (htim->State != HAL_TIM_STATE_READY) { return HAL_ERROR; }
```

直接返回错误，定时器从未使能。返回值未被检查，所以是**静默失败**，而串口仍会打印 "Control loop started at 20kHz"（`main.c:117`）。

**后果**：`info` 命令里的 `Loop Cnt` 永远是 0。多份文档（`01-傻瓜式操作手册.md:521`、`control/编译烧录指南.md:215`）把"Loop Cnt 增加"列为成功标志 —— 按当前代码这个标志**必然无法达成**，不是硬件问题。

**修复**：在 `main.c:104` 后加一行 `MX_TIM6_Init();`，并在 `tim.h` 中声明。

### 2.2 🔴 `gpio.c` 被 CubeMX 重新生成，所有手写引脚配置已丢失

当前 `gpio.c:42-50` 的 `MX_GPIO_Init()` 全文只有三行时钟使能：

```c
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
```

**GPIOB 和 GPIOE 的时钟从未使能**，而且没有任何 `HAL_GPIO_Init()` 调用。这意味着：

- **6 个电机方向脚全部失效**（PB0/PB1/PB5/PB12/PB13/PB14 在 GPIOB）→ `Motor_SetDirection()` 写寄存器无效果 → **电机无法换向**
- **4 个 LED 全部失效**（PE2~PE5 在 GPIOE）→ `led` 命令无反应
- **2 个按键失效**（PE0/PE1）→ `btn` 恒显示 UP
- **4 位拨码开关失效**（PC0~PC3，GPIOC 时钟有使能但引脚未配置为上拉输入）→ `dip` 读数不可信

旧版这段配置是手写在 `MX_GPIO_Init()` 函数体内（生成区），`.ioc` 里 `ProjectManager.DeletePrevious=true`，所以一次 Generate Code 就被清空了。这正是旧版分析里预警过的陷阱，现已实际发生。

**修复**：把引脚配置写成独立函数 `RST_GPIO_Init()` 放在 `/* USER CODE BEGIN 2 */` 之后，在 `main.c` 里显式调用。不要再写回生成区。

### 2.3 🔴 PWM 和编码器从未启动

全目录检索确认：

- **无任何 `HAL_TIM_PWM_Start()`** → TIM1_CH1 / TIM8_CH1 / TIM8_CH2 的比较输出通道从未使能。`Motor_SetPWM()` 里的 `__HAL_TIM_SET_COMPARE()` 只是写 CCR 寄存器，**引脚上不会有波形**。`pwm 0 500` 命令会打印成功但电机不动。
- **无任何 `HAL_TIM_Encoder_Start()`** → TIM2/TIM3/TIM4 编码器接口从未启动，`CNT` 不会计数。`enc 0/1/2` 读数恒为初值 32768。
- **无任何 `HAL_CAN_Start()` / `HAL_CAN_ConfigFilter()`** → CAN 完全不工作（旧版至少调了 `HAL_CAN_Start`，本次重构反而丢了）。

---

## 三、`control_loop.c` 内部的两个新引入 bug

### 3.1 角度计算未减零点偏置，上电即报 4915°

`RST_SafeStartup()`（`control_loop.c:64-70`）把三个编码器计数器预置为 32768 以避免回卷，但 `ReadEncoders()`（`control_loop.c:101`）用的是**绝对计数**：

```c
g_rst.motor[i].current_angle = (float)cnt_now * 360.0f / ENC_COUNTS_PER_REV;
```

32768 × 360 / 2400 = **4915.2°**。上电静止时 `info` 会显示 `ang=4915.20`。零点偏置从未被减掉。

速度计算（`control_loop.c:92-104`）的 delta 回卷处理是**正确**的，只有角度这一行有问题。

**修复**：`current_angle = (float)(cnt_now - 32768) * 360.0f / ENC_COUNTS_PER_REV;`（或引入 `zero_offset` 字段，归零时写入）。

### 3.2 `pwm_output` 算完不下发

`control_loop.c:132-140` 把结果写进 `g_rst.motor[i].pwm_output` 后，**从不调用 `Motor_SetPWM()`**。即使补上 PID，控制量也到不了硬件。控制环末尾必须有一次实际下发。

---

## 四、沿用未修的旧问题

| 问题 | 位置 | 说明 |
|---|---|---|
| ADC Rank3 通道重复 | `adc.c:79` | 只改了 Rank 没改 Channel，仍是 `ADC_CHANNEL_3`。**PA5（上夹电流）永远采不到**，PA3 被采两次 |
| ADC 非连续模式 | `adc.c:48` `ContinuousConvMode = DISABLE` + 软件触发 | 配合 DMA circular 只会转换一轮然后停住，`current_ma` 之后永远是陈旧值 |
| ADC 采样时间过短 | `adc.c:62` `ADC_SAMPLETIME_1CYCLE_5` | ADC 时钟 12MHz，采样窗 0.125µs。设计文档要求 239.5 周期。对 INA180 输出大概率不足（未经实测，标记为高风险） |
| CAN 波特率错误 | `can.c:41-45` `Prescaler=4, BS1=13, BS2=2` | CAN1 在 APB1(36MHz) → 36e6/(4×16) = **562.5kbps**，不是 1Mbps。`.ioc` 自己算出的 `CAN.CalculateBaudRate=562500` 也证实这点。而 `debug_console.c:238` 仍向用户打印 "1Mbps" —— 上位机按 1Mbps 配置会完全通不上 |
| TIM2 编码器占用 PA0 | `tim.c:325-331` | PA0 是野火板 WK_UP 按键复用脚，设计文档明令禁用。`PA15/PB3` 的部分重映射（`__HAL_AFIO_REMAP_TIM2_PARTIAL_1()`）从未应用 |
| 上夹编码器在 PD12/PD13 | `tim.c:369-377` | `rst_config.h:97` 注释仍写 PB6/PB7。硬件接线须按代码 |
| PWM 1kHz vs 控制环 20kHz | `tim.c:50-52`、`tim.c:253-255`（PSC=71, ARR=999） | f_PWM = 72e6/72/1000 = **1kHz**。控制环若真跑 20kHz，则每个 PWM 周期内更新 20 次占空比，物理上无意义。建议 PWM ≥ 16kHz，控制环 ≤ PWM/8。这是设计层的量级冲突，需重新定 PSC/ARR |
| 占空比标度 off-by-one | `rst_config.h:63-64` | `PWM_ARR=999` 但 `PWM_MAX_DUTY=1000`，CCR 可写 1000 > ARR。另 `PWM_ARR` 宏定义了却从未被 `tim.c` 使用（`tim.c:52` 硬编码 999） |
| 无看门狗 | 全工程 | `.ioc` 未启用 IWDG/WWDG，无 `HAL_IWDG_Init` |
| 无指令超时 | 全工程 | `Motor_SetPWM` 设定的占空比无限期保持。串口断线/程序跑飞时电机会持续转动 |
| 无电流限幅 | 全工程 | 没有 `CUR_LIMIT_MA` 之类常量，`Motor_SetPWM` 只有占空比限幅无电流检查。`pwm 0 1000` 可直接给 100% 占空比，堵转时不受任何软件限制 |
| 无急停 | — | 按键功能未实现；`rst_config.h:150-153` 声称 BTN1 长按校准、BTN2 长按归零，代码中无对应逻辑（且按键引脚已因 §2.2 失效） |
| `Error_Handler` 不关 PWM | `main.c:192-201` | `__disable_irq()` + 空死循环，无 LED 指示、无串口输出、不关闭 PWM、不置方向脚为 coast |
| `Console_Println` 潜在溢出 | `debug_console.c:99-102` | `vsnprintf` 返回的是未截断时的应有长度，超 254 字符时 `buf[len++]` 越界写栈。MDK 工程 `useUlib=0`（未启用 MicroLIB），C99 语义成立 |
| 空回车重放上一条命令 | `debug_console.c:210` | `cmd_line` 在执行后置 `'\0'`，此项旧 bug 已修复 ✅ |
| `g_rst` 未加 volatile | `control_loop.c:24` | 同时被主循环与 ISR 读写，编译优化 `-O3`。补上控制环后可能出现上位机改参数不生效 |
| DIP 未读取 | `control_loop.c:39` | `can_node_id` 被硬编码为 0，旧版的拨码读取逻辑丢失。`info` 显示的 CAN ID 恒为 0 |
| `RST_Loop1kHz` / `RST_ControlInit` 只有声明 | `rst_config.h:265,267` | 两个函数在 `.h` 中声明但**没有任何定义**。目前无人调用，故不报链接错误 |

---

## 五、修复优先次序

**第一批（不需要动 CubeMX，纯代码，约 1 小时）**

1. `main.c` 加 `MX_TIM6_Init();`，并检查 `HAL_TIM_Base_Start_IT` 返回值，失败时点错误 LED + 打印
2. 新写 `RST_GPIO_Init()` 放进 `USER CODE BEGIN 2` 区，恢复 GPIOB/GPIOE 时钟与全部引脚配置（含方向脚初始电平 Low = coast、LED 初始 High = 灭）
3. 补 `HAL_TIM_PWM_Start()` × 3、`HAL_TIM_Encoder_Start()` × 3
4. 修 `ReadEncoders()` 的零点偏置
5. `Error_Handler` 里先 `Motor_Sleep()` × 3

做完这五项，硬件才具备"能观测、能手动转"的基础，`pwm`/`enc`/`led`/`dip` 命令才真正有效。

**第二批（需要改 `.ioc` 并重新生成 —— 注意 §2.2，生成前务必先完成第 2 项）**

6. ADC：Rank3 改 `ADC_CHANNEL_5`；`ContinuousConvMode = ENABLE`；采样时间改 239.5 周期
7. CAN：按 APB1=36MHz 重算预分频以得到真正的 1Mbps；补 `HAL_CAN_ConfigFilter()` + `HAL_CAN_Start()` + `ActivateNotification`；`AutoBusOff` 建议改 ENABLE
8. TIM2 编码器迁到 PA15/PB3，加 `__HAL_AFIO_REMAP_TIM2_PARTIAL_1()`，释放 PA0
9. 重新核定 PWM 频率（建议 16~20kHz）与控制环频率的关系
10. 启用 IWDG

**第三批（应用层，真正的核心工作）**

11. 电流限幅 + 堵转检测 + 指令超时 —— **这三项必须先于 PID 落地**，它们是安全底线
12. 归零状态机
13. 位置环 / 速度环串级 PID
14. `P<0-255>U<0-255>L<0-255>` 串口协议解析（当前零实现，且本仓库无该协议的完整规格文档，字段单位与应答帧语义需另行确认）

---

## 六、不要照抄的旧结论

以下说法出现在本目录其他文档中，均**与代码不符**，请勿采信：

- ❌「已完全重构为生产级实时控制系统，可直接上机测试」
- ❌「硬件配置正确的话，上电就能跑」
- ❌「PID 控制器 ✅ 完整实现」「堵转检测 ✅ 双重判断」「归零功能 ✅ 状态机实现」
- ❌「堵转保护已激活（1.5A 阈值）」—— 代码中无任何电流阈值常量
- ❌「上机安全性 ✅ 多重保护」—— 无电流限幅、无超时、无看门狗、无急停
- ❌ `info` 显示 `Loop Cnt` 增加 —— 当前代码下必然为 0

真实定位：**这是一块板级 bring-up 程序，而且 bring-up 本身尚未跑通**（GPIO/PWM/编码器均未启动）。它还不是电机控制器。
