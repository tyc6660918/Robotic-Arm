# 快速开始 - 使用 DAP 下载器 + CH340 串口

## 🔌 你的硬件配置

- ✅ DAP 下载器（CMSIS-DAP）
- ✅ CH340 USB-UART 转换器
- ✅ 野火霸道开发板（STM32F103ZET6）

---

## 第一步：硬件连接（5分钟）

### 1. DAP 下载器连接

| DAP 引脚 | 野火板 SWD 接口 | 说明 |
|---------|---------------|------|
| SWDIO | SWDIO | 数据线 |
| SWCLK | SWCLK | 时钟线 |
| GND | GND | 地线 |
| 3.3V | 3.3V (可选) | 供电 |

💡 **提示**：
- 野火板上有专门的 SWD 接口，通常是 4pin 或 5pin 排针
- DAP 直接插上去即可，注意防呆设计
- 如果板子有独立供电（USB 或 12V），DAP 的 3.3V 可以不接

### 2. CH340 串口连接

| CH340 引脚 | 野火板引脚 | 说明 |
|-----------|-----------|------|
| TXD | PA10 (RX1) | 交叉连接 |
| RXD | PA9 (TX1) | 交叉连接 |
| GND | GND | 公共地 |
| VCC | 不接 | CH340 从 USB 取电 |

💡 **提示**：
- **TX 接 RX，RX 接 TX**（交叉连接）
- 野火板上通常有标注 USART1 的接口
- CH340 红色灯亮表示供电正常

### 3. 供电

#### 方式 1：USB 供电（推荐用于测试）
```
电脑 USB → 野火板 USB 接口
```
- 仅供 MCU 工作
- **不能带电机负载**

#### 方式 2：12V 外部电源（实际使用）
```
12V DC 电源 → 野火板电源接口（注意正负极）
```

### 4. 连接检查清单
```
□ DAP 插入野火板 SWD 接口
□ DAP 通过 USB 连接电脑（DAP 上 LED 应该亮）
□ CH340 连接 PA9/PA10（TX↔RX 交叉）
□ CH340 通过 USB 连接电脑（CH340 上红灯亮）
□ 野火板 USB 供电 或 12V 外部电源
□ 暂时不接电机、驱动板、编码器
```

---

## 第二步：安装驱动（5分钟）

### 1. DAP 驱动（Windows）
- DAP 通常免驱动（使用 WinUSB）
- 如需手动安装，使用 **Zadig** 工具
  1. 下载 Zadig: https://zadig.akeo.ie/
  2. 插入 DAP，打开 Zadig
  3. 选择 CMSIS-DAP 设备
  4. 选择 WinUSB 驱动
  5. 点击 "Install Driver"

### 2. CH340 驱动
在你的文档中有驱动：
```
docs/WHEELTEC 直流电机附送资料/编码器测试教程/2.软件工具/3.常见串口驱动程序/
1.CH340驱动(USB串口驱动)_XP_WIN7_WIN8_WIN10共用.rar
```

安装完成后：
- 打开 **设备管理器**
- **端口(COM 和 LPT)** 下应该看到：
  ```
  USB-SERIAL CH340 (COMx)
  ```
- 记住端口号，比如 **COM3**

---

## 第三步：Keil 配置 DAP（3分钟）

### 1. 打开项目
```
双击: MDK-ARM/rst-control-fw.uvprojx
```

### 2. 配置下载器
- 点击工具栏 **Options for Target** 按钮（魔术棒图标）
- 切换到 **Debug** 选项卡
- 下拉菜单选择：**CMSIS-DAP Debugger**
- 点击右侧 **Settings** 按钮
- **Debug** 选项卡：
  - Port: 选择 **SW**（不是 JTAG）
  - Max Clock: 保持默认 10MHz 或改为 4MHz
- **Flash Download** 选项卡：
  - 勾选 **Reset and Run**
  - 勾选 **Erase Full Chip**（首次烧录）
- 点击 **OK** → **OK**

---

## 第四步：CubeMX 配置（10分钟）

### ⚠️ 重要：必须先配置 TIM6 和 ADC

1. 打开项目：
```
双击: rst-control-fw.ioc
```

2. 配置 **TIM6**（20kHz 控制循环）：
   - 左侧 **Timers** → **TIM6**
   - 勾选 `Activated`
   - **Parameter Settings**:
     - Prescaler: `35`
     - Counter Period: `99`
   - **NVIC Settings**:
     - 勾选 `TIM6 global interrupt`
     - Priority: `0`

3. 配置 **ADC1 + DMA**（电流采样）：
   - 左侧 **Analog** → **ADC1**
   - **Mode**: 勾选 IN3, IN4, IN5
   - **Parameter Settings**:
     - Scan Conversion: `Enable`
     - Continuous Conversion: `Enable`
     - DMA Continuous Requests: `Enable`
     - Number of Conversion: `3`
   - **DMA Settings** → **Add**:
     - DMA Request: `ADC1`
     - Mode: `Circular`
     - Data Width: `Half Word` (两个都选)

4. 生成代码：
   - 点击右上角 **GENERATE CODE**
   - 等待完成

---

## 第五步：Keil 编译（5分钟）

### 1. 添加新文件
- 左侧 **Project** 窗口
- 右键 `Application/User/Core` → `Add Existing Files to Group`
- 选择并添加：
  - `Core/Src/control_loop.c` ✅
  - `Core/Src/tim6.c` ✅

### 2. 编译
```
按 F7 或点击 Build 图标
```

应该看到：
```
0 Error(s), 0 Warning(s)
Program Size: Code=xxxxx RO-data=xxx RW-data=xxx ZI-data=xxx
```

---

## 第六步：烧录固件（2分钟）

### 1. 检查连接
- DAP 连接到野火板 SWD
- 野火板已通电
- Keil 已识别 DAP（设备管理器中看到 CMSIS-DAP）

### 2. 下载
```
按 F8 或点击 Download 图标
```

应该看到：
```
Load "...\rst-control-fw.axf"
Erase Done
Programming Done
Verify OK
Application running ...
```

### 3. 如果失败
| 错误 | 解决 |
|------|------|
| No CMSIS-DAP device found | 重新插拔 DAP，检查驱动 |
| Flash Download failed | 点击 Erase Full Chip 再试 |
| RDDI-DAP Error | 降低 Max Clock 到 1MHz |

---

## 第七步：串口测试（2分钟）

### 1. 打开串口工具
推荐：
- **SSCOM** (串口调试助手)
- **Tera Term**
- **MobaXterm**
- **PuTTY**

### 2. 配置串口
```
端口：COM3 (你的实际端口号)
波特率：115200
数据位：8
停止位：1
校验：None
流控：None
```

### 3. 连接并复位
- 点击 **打开串口**
- 按野火板上的 **RESET** 按钮

---

## 🎉 成功标志

### 你应该看到：
```
========================================
  RST Motor Controller - Debug Console
  STM32F103ZET6  |  3-Axis DC Motor
========================================
  CAN ID=8  |  输入 help 查看命令
>
```

### 测试命令
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
  CAN ID:    8 (1Mbps)   <- 注意: 这行打印是错的, CAN 实测 562.5kbps
  Loop Cnt:  0      ← 恒为 0，这是正常的（见下方说明）
  Motors:    3 (0=Pitch 1=UpperJaw 2=LowerJaw)
  ...

> led 1 blink
  LED1 闪烁 5 次完成  ← 如果板上有 LED 会闪烁
```

---

## ❌ 常见问题

### 1. DAP 无法识别
```
解决：
1. 重新插拔 DAP USB
2. 使用 Zadig 安装 WinUSB 驱动
3. 更换 USB 线或 USB 口
```

### 2. 串口无输出
```
检查：
1. CH340 驱动是否安装
2. 波特率是否 115200
3. TX/RX 是否交叉连接
4. 按 RESET 按钮重启 MCU
```

### 3. 编译错误
```
错误: undefined reference to TIM6_IRQHandler
解决: 回到第四步，重新在 CubeMX 中配置 TIM6
```

### 4. 烧录卡住
```
解决：
1. Keil Debug 设置中降低时钟到 1MHz
2. 检查 SWD 接线是否牢固
3. 尝试 Erase Full Chip
```

---

## ✅ 测试完成后告诉我

格式：
```
✅ DAP 已连接，Keil 识别正常
✅ CH340 已连接（COM端口: COM3）
✅ 野火板已通电
✅ CubeMX 配置完成（TIM6 + ADC）
✅ Keil 编译成功 (0 Error)
✅ 固件烧录成功
✅ 串口连接成功 (115200)
✅ 收到启动信息
✅ help 命令正常
✅ info 命令正常（Loop Cnt 恒为 0 属预期，不是故障）
```

⚠️ **注意**：`Loop Cnt` 恒为 0 是当前固件的已知状态，不代表烧录或接线失败。
`loop_count` 在代码里从未被累加，而且 20kHz 控制循环本身也没有启动。
详见 `固件真实状态.md`。烧录成功的判据是能看到启动横幅并且 `help` 有响应。

然后我会指导你：
1. 接入编码器测试
2. 接入电机驱动
3. 进行电机测试

---

**现在开始吧！接好 DAP 和 CH340，按步骤来！** 🚀
