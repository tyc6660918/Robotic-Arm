# 快速启动规程（DAP 下载器 + CH340 串口版本）

---

## 区域用途

本规程用于指导使用 CMSIS-DAP 下载器与 CH340 USB-UART 转换器的操作人员完成 STM32 固件的首次编译、烧录与基础测试，验证 MCU 最小系统与串口通信功能。本阶段不连接电机与驱动板，仅执行基础功能验证。

---

## 关键文件

| 文件路径 | 说明 |
|---------|------|
| `CubeMX工程配置指南.md` | CubeMX 外设配置详细说明 |
| `固件真实状态.md` | 固件实际状态核实报告，含已知问题说明 |
| `接线教程.md` | 硬件接线操作规程 |
| `00-安全第一.md` | 安全操作规范 |
| `设备识别检查.md` | 设备识别检查操作规程 |

---

## 当前进展

（本章节用于记录启动流程的执行进展）

---

## 已完成功能

（本章节用于记录已完成的验证项目）

---

## 未完成工作

（本章节用于记录待执行的验证项目）

---

## 使用说明

### 硬件配置要求
- CMSIS-DAP 下载器
- CH340 USB-UART 转换器
- 野火霸道开发板（STM32F103ZET6）

---

### 第一步：硬件连接（预计 5 分钟）

#### 1. DAP 下载器连接

| DAP 引脚 | 野火板 SWD 接口 | 说明 |
|---------|---------------|------|
| SWDIO | SWDIO | 数据线 |
| SWCLK | SWCLK | 时钟线 |
| GND | GND | 地线 |
| 3.3V | 3.3V（可选） | 供电引脚 |

**说明：**
- 野火板设有专用 SWD 接口（通常为 4pin 或 5pin 排针）
- DAP 设备可直接插接，注意接口防呆方向
- 若开发板采用独立供电方案（USB 或 12V），则 DAP 的 3.3V 引脚可不予连接

#### 2. CH340 串口连接

| CH340 引脚 | 野火板引脚 | 说明 |
|-----------|-----------|------|
| TXD | PA10 (RX1) | 交叉连接 |
| RXD | PA9 (TX1) | 交叉连接 |
| GND | GND | 公共地 |
| VCC | 不连接 | CH340 通过 USB 端口供电 |

**说明：**
- TXD 与 RXD 需交叉连接（发送端接接收端）
- 野火板通常标注 USART1 接口位置
- CH340 红色指示灯点亮表明供电正常

#### 3. 供电方案

**方案 1：USB 供电（推荐用于测试场景）**
```
电脑 USB 端口 → 野火板 USB 接口
```
- 仅为 MCU 提供工作电源
- **不可用于驱动电机负载**

**方案 2：12V 外部电源（实际运行场景）**
```
12V DC 电源 → 野火板电源接口（接入前确认正负极）
```

#### 4. 连接状态检查清单
```
□ DAP 已插入野火板 SWD 接口
□ DAP 已通过 USB 连接电脑（DAP 指示灯应点亮）
□ CH340 已连接 PA9/PA10（TX 与 RX 交叉连接）
□ CH340 已通过 USB 连接电脑（CH340 红色指示灯应点亮）
□ 野火板已通过 USB 或 12V 外部电源供电
□ 电机、驱动板、编码器暂不连接
```

---

### 第二步：驱动程序安装（预计 5 分钟）

#### 1. DAP 驱动程序（Windows 环境）
- 多数 DAP 设备免驱动（操作系统内置 WinUSB 支持）
- 若需手动安装，使用 **Zadig** 工具执行以下操作：
  1. 下载 Zadig 工具：访问 https://zadig.akeo.ie/
  2. 插入 DAP 设备，运行 Zadig 程序
  3. 选择 CMSIS-DAP 设备
  4. 驱动选择 WinUSB
  5. 点击 "Install Driver" 按钮

#### 2. CH340 驱动程序
驱动程序归档位置：
```
docs/WHEELTEC 直流电机附送资料/编码器测试教程/2.软件工具/3.常见串口驱动程序/
1.CH340驱动(USB串口驱动)_XP_WIN7_WIN8_WIN10共用.rar
```

安装完成后验证：
- 打开 Windows **设备管理器**
- 进入 **端口(COM 和 LPT)** 分类
- 应显示 `USB-SERIAL CH340 (COMx)` 条目
- 记录实际端口号（示例：COM3）

---

### 第三步：Keil DAP 配置（预计 3 分钟）

#### 1. 打开工程文件
```
双击打开：MDK-ARM/rst-control-fw.uvprojx
```

#### 2. 配置下载器参数
- 点击工具栏 **Options for Target** 按钮（魔术棒图标）
- 切换至 **Debug** 选项卡
- 下拉菜单选择：**CMSIS-DAP Debugger**
- 点击右侧 **Settings** 按钮
  - **Debug** 选项卡：
    - Port：选择 **SW**（非 JTAG 模式）
    - Max Clock：保持默认 10MHz 或调整为 4MHz
  - **Flash Download** 选项卡：
    - 勾选 **Reset and Run**
    - 勾选 **Erase Full Chip**（首次烧录场景）
- 点击 **OK** → **OK** 确认配置

---

### 第四步：CubeMX 工程配置（预计 10 分钟）

**注意：** TIM6 与 ADC 配置为必需操作项。

#### 1. 打开工程文件
```
双击打开：rst-control-fw.ioc
```

#### 2. 配置 TIM6 定时器（20kHz 控制循环）
- 左侧导航栏 **Timers** → 选择 **TIM6**
- 勾选 `Activated` 选项
- **Parameter Settings** 配置：
  - Prescaler：`35`
  - Counter Period：`99`
- **NVIC Settings** 配置：
  - 勾选 `TIM6 global interrupt`
  - Priority：`0`（最高优先级）

#### 3. 配置 ADC1 与 DMA（电流采样）
- 左侧导航栏 **Analog** → 选择 **ADC1**
- **Mode** 设置：勾选 IN3、IN4、IN5
- **Parameter Settings** 配置：
  - Scan Conversion：`Enable`
  - Continuous Conversion：`Enable`
  - DMA Continuous Requests：`Enable`
  - Number of Conversion：`3`
- **DMA Settings** → 点击 **Add** 按钮：
  - DMA Request：`ADC1`
  - Mode：`Circular`
  - Data Width：`Half Word`（两项均为此配置）

#### 4. 生成工程代码
- 点击右上角 **GENERATE CODE** 按钮
- 等待代码生成完成

---

### 第五步：Keil 工程编译（预计 5 分钟）

#### 1. 添加源文件至工程
- 在左侧 **Project** 窗口中
- 右键点击 `Application/User/Core` → 选择 `Add Existing Files to Group`
- 选择并添加以下文件：
  - `Core/Src/control_loop.c`
  - `Core/Src/tim6.c`

#### 2. 执行编译
```
按 F7 键或点击工具栏 Build 图标
```

编译通过判定标准：
```
0 Error(s), 0 Warning(s)
Program Size: Code=xxxxx RO-data=xxx RW-data=xxx ZI-data=xxx
```

---

### 第六步：固件烧录（预计 2 分钟）

#### 1. 确认连接状态
- DAP 已连接野火板 SWD 接口
- 野火板已上电
- Keil 已识别 DAP 设备（设备管理器显示 CMSIS-DAP）

#### 2. 执行下载
```
按 F8 键或点击工具栏 Download 图标
```

烧录通过判定标准：
```
Load "...\rst-control-fw.axf"
Erase Done
Programming Done
Verify OK
Application running ...
```

#### 3. 烧录异常处置
| 错误信息 | 处置方法 |
|---------|---------|
| No CMSIS-DAP device found | 重新插拔 DAP 设备，检查驱动状态 |
| Flash Download failed | 执行 Erase Full Chip 后重试 |
| RDDI-DAP Error | 将 Max Clock 参数降至 1MHz 后重试 |

---

### 第七步：串口通信测试（预计 2 分钟）

#### 1. 启动串口终端工具
推荐工具（任选其一）：
- SSCOM（串口调试助手）
- Tera Term
- MobaXterm
- PuTTY

#### 2. 串口参数配置
```
端口号：COMx（使用实际分配的端口号）
波特率：115200
数据位：8
停止位：1
校验位：None
流控：None
```

#### 3. 建立连接并复位
- 点击 **打开串口** 按钮
- 按下野火板上的 **RESET** 按钮复位 MCU

---

### 验证通过判定标准

串口终端应显示以下启动信息：
```
========================================
  RST Motor Controller - Debug Console
  STM32F103ZET6  |  3-Axis DC Motor
========================================
  CAN ID=8  |  输入 help 查看命令
>
```

#### 功能测试命令
```
> help
  --- 可用命令 ---
  help     — 显示帮助
  info     — 系统信息
  led      — led <1-4> on|off|blink
  ...

> info
  --- 系统信息 ---
  MCU:       STM32F103ZET6 @ 72MHz
  UART:      USART1 @ 115200 bps
  CAN ID:    8 (1Mbps)   <- 注意：该行打印信息有误，CAN 实际波特率为 562.5kbps
  Loop Cnt:  0      ← 恒为 0，属预期状态（参见下方说明）
  Motors:    3 (0=Pitch 1=UpperJaw 2=LowerJaw)
  ...

> led 1 blink
  LED1 闪烁 5 次完成  ← 若板载对应 LED 已连接则会闪烁
```

**说明：** `Loop Cnt` 字段恒为 0 属于当前固件已知状态，非烧录或接线故障。
`loop_count` 变量在代码中未执行自增操作，且 20kHz 控制循环未实际启动。
详细说明参见 `固件真实状态.md`。烧录成功的判据为启动横幅正常显示且 `help` 命令有响应。

---

### 常见异常处置

#### 1. DAP 无法识别
处置流程：
1. 重新插拔 DAP 设备 USB 接口
2. 使用 Zadig 工具安装 WinUSB 驱动
3. 更换 USB 线缆或 USB 接口重试

#### 2. 串口无输出
排查顺序：
1. 确认 CH340 驱动程序已正确安装
2. 确认波特率配置为 115200
3. 确认 TX/RX 已正确交叉连接
4. 按下 RESET 按钮重启 MCU

#### 3. 编译错误
```
错误信息：undefined reference to TIM6_IRQHandler
处置方法：返回第四步，重新在 CubeMX 中配置 TIM6
```

#### 4. 烧录过程卡顿
处置流程：
1. 在 Keil Debug 设置中将时钟频率降至 1MHz
2. 检查 SWD 接线是否牢固
3. 尝试执行 Erase Full Chip 操作

---

## 风险与局限

- 当前固件处于开发阶段，Loop Cnt 恒为 0 为预期状态，不可作为控制环运行判据
- 阶段 1 通过仅表明 MCU 与串口链路正常，不可直接推断电机、编码器等外围功能可用
- 完成阶段 1 验证后，不可直接进入电机连接测试，需先按 `固件真实状态.md` 修复阻塞性问题

---

## 依赖关系

| 依赖项目 | 版本要求 |
|---------|---------|
| STM32CubeMX | 6.x 及以上版本 |
| Keil MDK-ARM | 5.x 及以上版本，含 STM32F1xx 器件支持包 |
| Zadig 工具 | 用于 DAP WinUSB 驱动安装（可选） |
| 串口终端工具 | SSCOM / Tera Term / MobaXterm / PuTTY 任选 |

---

## 后续建议

阶段 1 验证通过后，建议按以下顺序执行后续操作：
1. 接入编码器并执行编码器读数测试
2. 接入电机驱动板并执行 PWM 输出测试
3. 连接电机并执行电机转动测试
4. 建议对各阶段执行结果进行截图存档
