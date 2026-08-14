# CubeMX 配置指南 - RST 电机控制器

## ⚠️ 重要提醒
在 Keil 中编译前，**必须先在 CubeMX 中完成以下配置**。

---

## 第一步：打开项目

1. 启动 **STM32CubeMX**
2. 打开 `rst-control-fw.ioc` 文件（如果存在）
3. 如果没有 `.ioc` 文件，需要基于现有代码创建新项目

---

## 第二步：TIM6 配置（20kHz 控制循环）

### 1. 激活 TIM6
- **Pinout & Configuration** → **Timers** → **TIM6**
- Mode: 勾选 `Activated`

### 2. 参数配置
- **Parameter Settings**:
  ```
  Prescaler (PSC):         35
  Counter Period (ARR):    99
  auto-reload preload:     Disable
  ```
  计算: 72MHz ÷ 36 ÷ 100 = 20,000 Hz ✅

### 3. 使能中断
- **NVIC Settings**:
  - 勾选 `TIM6 global interrupt`
  - Priority: `0` (最高优先级)
  - Subpriority: `0`

---

## 第三步：ADC1 + DMA 配置

### 1. ADC1 通道配置
- **Pinout & Configuration** → **Analog** → **ADC1**
- **Mode**:
  - IN3: `ADC1_IN3` (PA3 - 下夹电流)
  - IN4: `ADC1_IN4` (PA4 - Pitch 电流)
  - IN5: `ADC1_IN5` (PA5 - 上夹电流)

### 2. ADC 参数
- **Configuration** → **Parameter Settings**:
  ```
  Clock Prescaler:         PCLK2 divided by 6
  Resolution:              12 bits
  Data Alignment:          Right alignment
  Scan Conversion Mode:    Enable
  Continuous Conversion:   Enable
  DMA Continuous Requests: Enable
  Number of Conversion:    3
  ```

- **Rank 配置**:
  ```
  Rank 1: Channel 4 (PA4 - Pitch)   Sampling Time: 55.5 Cycles
  Rank 2: Channel 5 (PA5 - 上夹)     Sampling Time: 55.5 Cycles
  Rank 3: Channel 3 (PA3 - 下夹)     Sampling Time: 55.5 Cycles
  ```

### 3. DMA 配置
- **Configuration** → **DMA Settings** → **Add**
  ```
  DMA Request:       ADC1
  Stream:            DMA1 Channel 1
  Direction:         Peripheral To Memory
  Priority:          Medium
  Mode:              Circular
  
  Increment Address:
    Peripheral:      Disable
    Memory:          Enable
    
  Data Width:
    Peripheral:      Half Word (16bit)
    Memory:          Half Word (16bit)
  ```

---

## 第四步：检查已有配置

### 1. 定时器（PWM + 编码器）
确认以下定时器已正确配置：

#### TIM1 (PWM - Pitch)
- Channel 1: PWM Generation (PA8)
- Prescaler: 71, Period: 999 (1kHz PWM)

#### TIM8 (PWM - 上夹/下夹)
- Channel 1: PWM Generation (PC6)
- Channel 2: PWM Generation (PC7)
- Prescaler: 71, Period: 999

#### TIM2 (编码器 - 下夹)
- Combined Channels: Encoder Mode
- PA15 = CH1, PB3 = CH2
- ⚠️ **需要部分重映射 (Partial Remap)**

#### TIM3 (编码器 - Pitch)
- Combined Channels: Encoder Mode
- PA6 = CH1, PA7 = CH2

#### TIM4 (编码器 - 上夹)
- Combined Channels: Encoder Mode
- PB6 = CH1, PB7 = CH2

### 2. GPIO 配置

#### 方向引脚 (所有设为 GPIO_Output)
```
PB0  = DIR_P_IN1
PB1  = DIR_P_IN2
PB5  = DIR_U_IN1
PB12 = DIR_U_IN2
PB13 = DIR_L_IN1
PB14 = DIR_L_IN2
```
- Output level: Low
- Mode: Push Pull
- Pull: No pull
- Speed: Medium

#### LED 指示灯 (GPIO_Output)
```
PE2 = LED_P    (Pitch 状态)
PE3 = LED_U    (上夹状态)
PE4 = LED_L    (下夹状态)
PE5 = LED_SYS  (系统心跳)
```

#### 按键 (GPIO_Input)
```
PE0 = BTN1
PE1 = BTN2
```
- Mode: Input
- Pull: Pull-up

#### 拨码开关 (GPIO_Input)
```
PC0 = DIP_PIN_0
PC1 = DIP_PIN_1
PC2 = DIP_PIN_2
PC3 = DIP_PIN_3
```
- Mode: Input
- Pull: Pull-up

### 3. 通信接口

#### USART1 (调试串口)
- Mode: Asynchronous
- PA9 = TX, PA10 = RX
- Baud Rate: 115200
- Word Length: 8 Bits
- Stop Bits: 1
- Parity: None
- **NVIC Settings**: 勾选 `USART1 global interrupt`

#### CAN1 (总线通信)
- Mode: Master
- PA11 = RX, PA12 = TX
- Bit Rate: 1 Mbps
- **NVIC Settings**: 勾选 `USB low priority or CAN RX0 interrupts`

---

## 第五步：时钟配置

### System Clock Configuration
- **Clock Configuration** 页面：
  ```
  Input frequency (HSE):    8 MHz (外部晶振)
  PLLMUL:                   x9
  System Clock (SYSCLK):    72 MHz
  HCLK:                     72 MHz
  APB1:                     36 MHz
  APB2:                     72 MHz
  ```

---

## 第六步：工程设置

### Project Manager
1. **Project**:
   - Project Name: `rst-control-fw`
   - Toolchain: `MDK-ARM V5`
   - MCU: `STM32F103ZETx`

2. **Code Generator**:
   - ✅ 勾选 `Generate peripheral initialization as a pair of '.c/.h' files per peripheral`
   - ✅ 勾选 `Keep user code when re-generating`
   - ✅ 勾选 `Delete previously generated files when not re-generated`

3. **Advanced Settings**:
   - 所有外设驱动使用 `HAL`

---

## 第七步：生成代码

1. 点击右上角 **GENERATE CODE**
2. 等待生成完成
3. 关闭 CubeMX

---

## 第八步：Keil 配置

### 1. 打开项目
- 双击 `MDK-ARM/rst-control-fw.uvprojx`

### 2. 添加新文件到项目
在 **Project** 窗口中：

- 右键 `Application/User/Core` → `Add Existing Files to Group`
  - 添加 `Core/Src/control_loop.c` ✅
  - 添加 `Core/Src/tim6.c` ✅

### 3. 删除旧文件（如果存在）
- 删除 `app_main.c` ❌

### 4. 编译选项
- **C/C++** 选项卡:
  - Optimization: `-O2 -Os`
  - 勾选 `Use MicroLIB`
  - Include Paths: 确保包含 `Core/Inc`

### 5. 编译
- 按 `F7` 或点击 **Build** 图标
- 检查输出：
  ```
  0 Error(s), 0 Warning(s) ✅
  ```

---

## 第九步：下载和测试

### 1. 连接硬件
- ST-Link 连接到 SWD 接口 (PA13/PA14)
- USB-UART 转换器连接到 USART1 (PA9/PA10)

### 2. 下载固件
- Keil: `F8` 或 **Download** 图标

### 3. 打开串口终端
- 波特率: 115200
- 数据位: 8
- 停止位: 1
- 校验: None

### 4. 基础测试命令
```
help          # 显示帮助
info          # 系统信息
led 1 blink   # LED 测试
dip           # 读拨码开关
enc 0         # 读编码器 (手动转电机看计数)
pwm 0 100     # 测试 PWM 输出
```

---

## 常见问题

### Q1: 编译错误 "undefined reference to TIM6_IRQHandler"
**解决**: 确保 TIM6 在 CubeMX 中已激活并重新生成代码

### Q2: 链接错误 "control_loop.c not found"
**解决**: 在 Keil 中手动添加该文件到项目

### Q3: 电机不响应控制命令
**检查**:
1. TIM6 中断是否使能
2. `HAL_TIM_Base_Start_IT(&htim6)` 是否执行
3. 用示波器检查 PWM 输出

### Q4: 编码器读数跳变
**检查**:
1. 编码器滤波参数 (IC Filter = 8)
2. 接线是否松动
3. 供电是否稳定

### Q5: ADC 读数为 0
**检查**:
1. DMA 是否启动 (`HAL_ADC_Start_DMA`)
2. INA180 供电和增益跳线
3. 分流电阻是否正确 (0.1Ω)

---

## 性能验证

> ⚠️ **以下是设计目标，不是当前固件的实测结果。**
> 截至 2026-08-09，除最后一项外没有任何一项被验证过，
> 其中前四项在当前代码下**不可能达到**（控制环未运行、编码器未启动、
> ADC 只转换一轮、PID 未实现）。详见 `固件真实状态.md`。

按本指南配置**并补齐控制环代码后**，目标指标为：

| 指标 | 目标值 | 当前状态 |
|------|--------|----------|
| 控制循环频率 | 20kHz（示波器测 GPIO 翻转） | ❌ 环未运行（TIM6 未初始化） |
| 编码器分辨率 | 2400 线/圈 | ❌ 编码器外设未 Start |
| 电流采样精度 | ±10mA | ❌ ADC 单轮转换后停止 |
| PID 阶跃响应 | <50ms | ❌ PID 未实现 |
| 串口调试 | 115200 bps 无丢包 | ✅ 已验证可用 |

注：PWM 当前是 **1kHz**（`tim.c` PSC=71/ARR=999），与 20kHz 控制环相差 20 倍，
定时器方案需要重新核算，不能只靠"填空控制环函数"收尾。

---

需要帮助？检查 `FIRMWARE_FIX_REPORT.md` 了解更多细节。
