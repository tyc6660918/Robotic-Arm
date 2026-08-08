# CubeMX 配置指南 v2 — RST 三电机控制板 (STM32F103ZET6)

---

## Pin 总览

```
      PA0  ══ (禁用 — WK_UP 按键)
      PA1  ══ (保留)
      PA3  ══ ADC1_IN3 — 下夹 电流
      PA4  ══ ADC1_IN4 — Pitch 电流
      PA5  ══ ADC1_IN5 — 上夹 电流
      PA6  ══ TIM3_CH1 — Pitch 编码器 A
      PA7  ══ TIM3_CH2 — Pitch 编码器 B
      PA8  ══ TIM1_CH1 — Pitch PWM
      PA9  ══ USART1_TX — 调试串口
      PA10 ══ USART1_RX — 调试串口
      PA11 ══ CAN1_RX
      PA12 ══ CAN1_TX
      PA13 ══ SWDIO
      PA14 ══ SWCLK
      PA15 ══ TIM2_CH1 — 下夹 编码器 A (Remap)

      PB0  ══ GPIO_OUT — Pitch IN1 (方向)
      PB1  ══ GPIO_OUT — Pitch IN2 (方向)
      PB3  ══ TIM2_CH2 — 下夹 编码器 B (Remap)
      PB5  ══ GPIO_OUT — 上夹 IN1 (方向)
      PB6  ══ TIM4_CH1 — 上夹 编码器 A
      PB7  ══ TIM4_CH2 — 上夹 编码器 B
      PB12 ══ GPIO_OUT — 上夹 IN2 (方向)
      PB13 ══ GPIO_OUT — 下夹 IN1 (方向)
      PB14 ══ GPIO_OUT — 下夹 IN2 (方向)

      PC0~3 ══ GPIO_IN — 拨码开关 DIP1~4
      PC6    ══ TIM8_CH1 — 上夹 PWM
      PC7    ══ TIM8_CH2 — 下夹 PWM

      PE0  ══ GPIO_IN  — BTN1
      PE1  ══ GPIO_IN  — BTN2
      PE2  ══ GPIO_OUT — LED1 (Pitch 状态)
      PE3  ══ GPIO_OUT — LED2 (上夹 状态)
      PE4  ══ GPIO_OUT — LED3 (下夹 状态)
      PE5  ══ GPIO_OUT — LED4 (系统心跳)
```

---

## Step 1: 新建工程

```
File → New Project → 选 STM32F103ZETx → Start Project
```

---

## Step 2: Pinout 配置

### 2.1 System Core → SYS

| 参数 | 值 |
|------|-----|
| Debug | **Serial Wire** |
| ⚠️ 重要 | ❌ 不选 JTAG (5-pin), 选 SWD (2-pin) |
| 原因 | 释放 PA15 和 PB3 给 TIM2 编码器 |

### 2.2 System Core → RCC

| 参数 | 值 |
|------|-----|
| High Speed Clock | **Crystal/Ceramic Resonator** |
| Low Speed Clock | Disable |

### 2.3 Connectivity → USART1

| 参数 | 值 |
|------|-----|
| Mode | **Asynchronous** |
| Baud Rate | 115200 Bit/s |
| Word Length | 8 Bits |
| Parity | None |
| Stop Bits | 1 |

```
Pin: PA9=TX, PA10=RX
NVIC → USART1 global interrupt: ✅
```

### 2.4 Connectivity → CAN

| 参数 | 值 |
|------|-----|
| Master Mode | ✅ Enable |
| Prescaler | **4** |
| Time Quanta (BS1) | **13** |
| Time Quanta (BS2) | **2** |
| SJW | 1 |
| 计算公式 | 72MHz / (4 × 16) = **1.125 Mbps ≈ 1M** |

```
Pin: PA11=CAN_RX, PA12=CAN_TX  
NVIC → CAN1 RX0 interrupt: ✅
```

### 2.5 Timers → TIM1 (PWM — Pitch 电机)

| 参数 | 值 |
|------|-----|
| Clock Source | Internal Clock |
| Channel1 | **PWM Generation CH1** |
| Prescaler (PSC) | **71** |
| Counter Period (ARR) | **999** |
| CH1 Pulse | 0 |
| CH Polarity | High |

```
Pin: PE9 = TIM1_CH1
```

### 2.6 Timers → TIM8 (PWM — 上夹 + 下夹 电机)

| 参数 | 值 |
|------|-----|
| Clock Source | Internal Clock |
| Channel1 | **PWM Generation CH1** |
| Channel2 | **PWM Generation CH2** |
| Prescaler (PSC) | **71** |
| Counter Period (ARR) | **999** |
| CH1 Pulse / CH2 Pulse | 0 |
| CH Polarity | High |

```
Pin: PC6 = TIM8_CH1, PC7 = TIM8_CH2
```

### 2.7 Timers → TIM2 (编码器 — 下夹, 需 Remap)

| 参数 | 值 |
|------|-----|
| Combined Channels | **Encoder Mode** |
| Polarity | Rising Edge (CH1+CH2) |
| Prescaler | 0 |
| Counter Period | **65535** |
| Input Filter | 8 |

```
▶ 这一步配置完成后 Pin 可能显示在 PA0/PA1
▶ 下面 Step 2.12 会做 Remap 映射到 PA15/PB3
```

### 2.8 Timers → TIM3 (编码器 — Pitch)

| 参数 | 值 |
|------|-----|
| Combined Channels | **Encoder Mode** |
| Polarity | Rising Edge |
| Prescaler | 0 |
| Counter Period | 65535 |
| Input Filter | 8 |

```
Pin: PA6 = TIM3_CH1, PA7 = TIM3_CH2
```

### 2.9 Timers → TIM4 (编码器 — 上夹)

| 参数 | 值 |
|------|-----|
| Combined Channels | **Encoder Mode** |
| Polarity | Rising Edge |
| Prescaler | 0 |
| Counter Period | 65535 |
| Input Filter | 8 |

```
Pin: PB6 = TIM4_CH1, PB7 = TIM4_CH2
```

### 2.10 Analog → ADC1

| 参数 | 值 |
|------|-----|
| Mode | Independent mode |
| IN3 (PA3) | ✅ Single-ended |
| IN4 (PA4) | ✅ Single-ended |
| IN5 (PA5) | ✅ Single-ended |
| Scan Conversion Mode | **Enable** |
| Number of Conversion | **3** |
| Rank 1/2/3 Sampling Time | **239.5 Cycles** |

```
▶ DMA Settings 选项卡: 添加 DMA, ADC1, Direction=Peripheral to Memory, Circular, Half Word
```

### 2.11 GPIO 配置

逐个在 Pinout 视图右键 → GPIO_Output 或 GPIO_Input:

| Pin | 模式 | Pull | Label | 用途 |
|-----|------|------|-------|------|
| PB0 | Output PP | NoPull | DIR_P_IN1 | Pitch 方向1 |
| PB1 | Output PP | NoPull | DIR_P_IN2 | Pitch 方向2 |
| PB5 | Output PP | NoPull | DIR_U_IN1 | 上夹 方向1 |
| PB12 | Output PP | NoPull | DIR_U_IN2 | 上夹 方向2 |
| PB13 | Output PP | NoPull | DIR_L_IN1 | 下夹 方向1 |
| PB14 | Output PP | NoPull | DIR_L_IN2 | 下夹 方向2 |
| PE2 | Output PP | NoPull | LED_P | Pitch LED |
| PE3 | Output PP | NoPull | LED_U | 上夹 LED |
| PE4 | Output PP | NoPull | LED_L | 下夹 LED |
| PE5 | Output PP | NoPull | LED_SYS | 心跳 LED |
| PE0 | Input | Pull-up | BTN1 | 按键1 |
| PE1 | Input | Pull-up | BTN2 | 按键2 |
| PC0 | Input | Pull-up | DIP1 | 拨码1 |
| PC1 | Input | Pull-up | DIP2 | 拨码2 |
| PC2 | Input | Pull-up | DIP3 | 拨码3 |
| PC3 | Input | Pull-up | DIP4 | 拨码4 |

所有 LED 的初始输出电平设为 **High** (灭)。
所有方向脚的初始输出电平设为 **Low**。

> ⚠️ PA0 不分配任何外设 — 它是 WK_UP 按键复用脚

### 2.12 ⚠️ 关键：TIM2 重映射

CubeMX 默认把 TIM2_CH1/CH2 放在 PA0/PA1。但 PA0 不能用。

**操作步骤：**

1. 菜单 Pinout → 或 Ctrl+K 搜索 `TIM2`
2. 在 TIM2 的配置中找到 **"Remap"** 或 **"Alternate Function"**
3. 某些 CubeMX 版本需要在 **Pinout view 中按住 Ctrl 拖动 TIM2_CH1 到 PA15**
4. 另一种方法：在左侧 `Connectivity → TIM2` 中把引脚手动改到 PA15/PB3

> 如果 CubeMX 版本不支持直接在 GUI 中 Remap TIM2：
> 照常用 PA0/PA1 配置 TIM2 编码器模式生成代码，
> 然后手动在代码中加上：
> ```c
> __HAL_AFIO_REMAP_TIM2_PARTIAL_1();  // 或直接操作 AFIO 寄存器
> // AFIO->MAPR |= AFIO_MAPR_TIM2_REMAP_PARTIALREMAP1;
> ```

---

## Step 3: Clock Configuration

```
HSE: 8 MHz
PLL Source: HSE
PLL Mul: ×9
System Clock: 72 MHz
APB1: 36 MHz (÷2)
APB2: 72 MHz (÷1)
```

---

## Step 4: Project Manager

| 设置 | 值 |
|------|-----|
| Project Name | `rst-control-fw` |
| Project Location | `E:\Robotic-Arm\rst-control-fw` |
| Toolchain | MDK-ARM |
| ✅ Generate Under Root | |
| ✅ Copy only necessary library | |
| ✅ Generate .c/.h pairs | |

Code Generator tab:

| 设置 | 值 |
|------|-----|
| Delete previously generated | ✅ |
| Set free pins as analog | ✅ |

---

## Step 5: 生成后步骤

### 5.1 文件替换

用仓库中的文件覆盖 CubeMX 生成的文件：

| 仓库文件 | 覆盖 CubeMX 的 | 说明 |
|---------|---------------|------|
| `Core/Src/main.c` | `Core/Src/main.c` | 主程序 |
| `Core/Src/debug_console.c` | 新增 | 调试控制台 |
| `Core/Inc/rst_config.h` | 新增 | Pin 定义 |
| `Core/Inc/debug_console.h` | 新增 | 控制台头文件 |

### 5.2 Keil → Include Paths

```
Options for Target → C/C++ → Include Paths:
  添加: ..\Core\Inc
```

### 5.3 Keil → Use MicroLIB

```
Options for Target → Target → ✅ Use MicroLIB
```

### 5.4 TIM2 Remap 补丁 (如果 CubeMX 没生成)

在 `gpio.c` 或 `main.c` 的 `MX_GPIO_Init()` 末尾添加：

```c
/* TIM2 Partial Remap: CH1→PA15, CH2→PB3 */
__HAL_AFIO_REMAP_TIM2_PARTIAL_1();
```

同时确保 PA15 和 PB3 的 GPIO 复用功能被正确配置为 TIM2 编码器输入：

```c
/* 在 MX_GPIO_Init() 中 */
GPIO_InitTypeDef GPIO_InitStruct = {0};

/* PA15 = TIM2_CH1 */
GPIO_InitStruct.Pin = GPIO_PIN_15;
GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
GPIO_InitStruct.Pull = GPIO_PULLUP;
HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

/* PB3 = TIM2_CH2 */  
GPIO_InitStruct.Pin = GPIO_PIN_3;
GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
GPIO_InitStruct.Pull = GPIO_PULLUP;
HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
```

### 5.5 编译

F7 (Build) → 应 0 Error 0 Warning。

---

## Step 6: 验证

```
烧录 → 串口助手 115200bps 8N1 → 应看到控制台 > 提示符
```

```
> help    — 命令列表
> led 1 on  — PE2 亮
> led 1 off — PE2 灭
> btn      — 按 PE0/PE1 看变化
> dip      — 拨码开关读数
> info     — 系统信息
```
