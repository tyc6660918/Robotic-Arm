# 🔧 硬件连接详细步骤

本文档提供详细的硬件连接和驱动安装步骤。

---

## 📦 所需硬件清单

### 必需硬件
- [ ] STM32 开发板（F103ZET6 或 F405RG）
- [ ] 调试器（CMSIS-DAP / ST-Link V2 / WCH-Link 三选一）
- [ ] USB 数据线（连接调试器到电脑）
- [ ] SWD 排线（连接调试器到开发板）

### 可选硬件
- [ ] USB 转串口模块（查看调试日志）
- [ ] 杜邦线（串口连接）
- [ ] 外部电源（如果 USB 供电不足）

---

## 1️⃣ 安装调试器驱动

### CMSIS-DAP（野火 DAP 小智款）

**驱动位置:**
```
D:\BaiduNetdiskDownload\野火【DAP小智款下载器】
```

**安装步骤:**
1. 将 DAP 调试器插入电脑 USB 口
2. 打开设备管理器，查看是否识别为 "CMSIS-DAP"
3. 如果显示黄色感叹号，右键 → 更新驱动程序
4. 选择 "浏览我的电脑以查找驱动程序"
5. 指向驱动文件夹

**验证安装:**
```bash
# Windows PowerShell
Get-PnpDevice | Select-String "CMSIS-DAP"

# 预期输出
OK    USB    CMSIS-DAP v2 Interface
```

**参考文档:**
- `1-DAP小智款使用说明.pdf`
- `2-DAP下载器通用使用说明.pdf`

### ST-Link V2/V2.1

**驱动下载:**
- 官方网站: https://www.st.com/en/development-tools/stsw-link009.html
- 或搜索 "ST-Link USB driver"

**安装步骤:**
1. 下载并安装 ST-Link 驱动
2. 插入 ST-Link 到 USB 口
3. 设备管理器中应显示 "STMicroelectronics STLink dongle"

### WCH-Link

**驱动下载:**
- WCH 官网: https://www.wch.cn/downloads/WCH-LinkUtility_ZIP.html

**安装步骤:**
1. 下载 WCH-Link 工具
2. 运行安装程序
3. 插入 WCH-Link，驱动会自动安装

---

## 2️⃣ SWD 接口连接

### 标准 SWD 4线连接

```
调试器端          开发板端
---------        ----------
SWDIO    ----→   SWDIO (PA13)
SWCLK    ----→   SWCLK (PA14)
GND      ----→   GND
3V3      ----→   3V3 (可选，为目标板供电)
```

### 引脚定义

| 信号 | 功能 | 说明 |
|------|------|------|
| SWDIO | 数据线 | 串行数据输入/输出 |
| SWCLK | 时钟线 | 串行时钟 |
| GND | 地线 | **必须连接**，提供公共地 |
| 3V3 | 电源 | 可选，为目标板供电（如果目标板已有电源则不需要） |

### ⚠️ 常见错误

**错误 1: 忘记连接 GND**
- 现象：OpenOCD 报告 "Error: DAP init failed"
- 解决：务必连接 GND 线

**错误 2: SWDIO/SWCLK 接反**
- 现象：OpenOCD 报告 "Error: Could not find MEM-AP"
- 解决：检查 SWDIO 和 SWCLK 是否接对

**错误 3: 目标板未上电**
- 现象：OpenOCD 卡在 "Listening on port 3333"
- 解决：给目标板接上 USB 或外部电源

---

## 3️⃣ 开发板供电

### 方式 1: USB 供电（推荐）
```
USB 线 → 开发板 USB 口
```
✅ 优点：简单、方便
⚠️ 注意：USB 最大 500mA，驱动电机时可能不足

### 方式 2: 外部电源供电
```
外部电源（5V/12V）→ 开发板电源接口
```
✅ 优点：电流充足，适合带负载测试
⚠️ 注意：检查电压和极性，避免烧坏开发板

### 方式 3: 调试器供电（仅用于调试）
```
调试器 3V3 → 开发板 3V3
```
⚠️ 仅用于无负载的程序调试，电流很小（<100mA）

---

## 4️⃣ 串口连接（可选，用于查看日志）

### 硬件连接
```
USB转串口模块     开发板 UART1
-----------      ------------
RX       ----→   TX (PA9)
TX       ----→   RX (PA10)
GND      ----→   GND
```

### 串口参数
```
波特率: 115200
数据位: 8
停止位: 1
校验位: None
流控: None
```

### 打开串口（Windows）
```powershell
# PowerShell
$port = new-Object System.IO.Ports.SerialPort COM5,115200,None,8,one
$port.Open()
$port.ReadExisting()
```

### 打开串口（Linux/Mac）
```bash
screen /dev/ttyUSB0 115200
```

---

## 5️⃣ 连接测试

### 测试脚本
```bash
cd debug/openocd-configs
bash test-connection.sh
```

### 预期输出（成功）
```
✓ Found CMSIS-DAP device
✓ OpenOCD started successfully
✓ Target: stm32f1x.cpu
✓ Target voltage: 3.30V
✓ Connection test PASSED
```

### 常见错误排查

**错误: "Error: unable to find CMSIS-DAP device"**
```bash
# 检查 USB 设备
lsusb | grep -i "dap"

# Windows PowerShell
Get-PnpDevice | Select-String "CMSIS-DAP"
```
解决：
1. 重新插拔 USB
2. 检查驱动是否正确安装
3. 尝试其他 USB 口

**错误: "Error: init mode failed (unable to connect to the target)"**
```
解决清单：
□ SWD 线是否连接正确？
□ SWDIO/SWCLK 是否接反？
□ GND 是否连接？
□ 目标板是否上电？
□ BOOT0 跳线是否正确？（应该接 GND）
□ 目标板是否有硬件故障？
```

**错误: "Error: Target voltage is 0.00V"**
```
原因：目标板未上电
解决：给开发板接上电源（USB 或外部电源）
```

---

## 6️⃣ BOOT 模式配置

### STM32 启动模式

| BOOT1 | BOOT0 | 启动模式 | 用途 |
|-------|-------|----------|------|
| x | 0 | 主闪存 | **正常运行模式**（推荐） |
| 0 | 1 | 系统存储器 | DFU 模式（用于 USB 烧录） |
| 1 | 1 | 内置 SRAM | 调试模式（程序在 RAM 运行） |

### 推荐配置
```
BOOT0 → GND (跳线帽短接到 GND 侧)
BOOT1 → 任意（通常也接 GND）
```

---

## 7️⃣ 多调试器切换

本项目支持 3 种调试器，无需修改代码即可切换。

### 切换方法（VSCode）
```
1. 按 F5 或点击调试按钮
2. 在下拉菜单中选择对应的配置
   - Debug xxx (DAP)      ← 使用 CMSIS-DAP
   - Debug xxx (ST-Link)  ← 使用 ST-Link
   - Debug xxx (WCH-Link) ← 使用 WCH-Link
```

### 切换方法（命令行）
```bash
# CMSIS-DAP
openocd -f debug/openocd-configs/cmsis-dap-f103.cfg

# ST-Link
openocd -f debug/openocd-configs/stlink-f103.cfg

# WCH-Link
openocd -f debug/openocd-configs/wch-link-f103.cfg
```

---

## 8️⃣ 硬件故障排除

### LED 不亮
```
□ 检查电源指示灯是否亮
□ 测量 3.3V 和 5V 引脚电压
□ 检查 USB 线是否损坏
□ 尝试外部电源供电
```

### 无法烧录
```
□ BOOT0 是否接 GND？
□ SWD 连接是否正确？
□ 芯片是否被锁定？（尝试 Mass Erase）
□ 芯片是否损坏？（用万用表测量引脚）
```

### 程序烧录后不运行
```
□ 复位后是否正常启动？
□ 查看串口是否有 HardFault 信息
□ 晶振是否起振？（用示波器测量 OSC_IN）
□ 电源是否稳定？（测量 VDD 电压波动）
```

---

## 📚 参考资料

- [STM32F103 数据手册](https://www.st.com/resource/en/datasheet/stm32f103ze.pdf)
- [CMSIS-DAP 规范](https://arm-software.github.io/CMSIS_5/DAP/html/index.html)
- [OpenOCD 用户手册](https://openocd.org/doc/html/index.html)

---

## 下一步

✅ 硬件连接完成后：
1. 返回 [`../getting-started/debugging.md`](../getting-started/debugging.md) 继续快速上手
2. 或查看 [`debugging-complete.md`](debugging-complete.md) 了解完整调试流程

---

**硬件连接有问题？把现象告诉我，我帮你分析！** 💬
