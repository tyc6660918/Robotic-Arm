# OpenOCD 调试配置文件

这个目录包含了用于 OpenOCD 调试和烧录的配置文件。

---

## 📁 配置文件列表

| 文件 | 调试器 | 目标芯片 | 适用项目 |
|------|--------|----------|----------|
| `stlink-f103.cfg` | ST-Link V2/V2.1/V3 | STM32F103ZE | rst-control-fw |
| `cmsis-dap-f103.cfg` | CMSIS-DAP / DAPLink | STM32F103ZE | rst-control-fw |
| `wch-link-f103.cfg` | WCH-Link / WCH-LinkE | STM32F103ZE | rst-control-fw |
| `stlink-f405.cfg` | ST-Link V2/V2.1/V3 | STM32F405RG | dummy-ref-core-fw |

---

## 🚀 快速开始

### 1. 测试连接

```bash
# 进入项目目录
cd /e/Robotic-Arm

# 使用对应的配置文件测试连接
openocd -f openocd-configs/stlink-f103.cfg
```

如果连接成功，你会看到：
```
Info : STLINK V2J37S7 (API v2) VID:PID 0483:3748
Info : Target voltage: 3.245V
Info : stm32f1x.cpu: hardware has 6 breakpoints, 4 watchpoints
```

按 `Ctrl+C` 退出。

### 2. 烧录固件

#### 方法 A: 使用 OpenOCD 命令行

```bash
# 烧录 rst-control-fw (ST-Link)
openocd -f openocd-configs/stlink-f103.cfg \
  -c init \
  -c "reset halt" \
  -c "flash write_image erase rst-control-fw/control/build/control.elf" \
  -c "verify_image rst-control-fw/control/build/control.elf" \
  -c "reset run" \
  -c exit
```

#### 方法 B: 使用 VSCode 任务

在 VSCode 中按 `Ctrl+Shift+P`，选择 `Tasks: Run Task`，然后选择对应的烧录任务。

### 3. 启动 GDB 调试

#### 终端 1: 启动 OpenOCD 服务器

```bash
openocd -f openocd-configs/stlink-f103.cfg
```

保持这个终端运行，OpenOCD 会监听 GDB 连接（默认端口 3333）。

#### 终端 2: 启动 GDB

```bash
# 进入固件目录
cd rst-control-fw/control/build

# 启动 GDB 并连接到 OpenOCD
arm-none-eabi-gdb control.elf \
  -ex "target extended-remote localhost:3333" \
  -ex "monitor reset halt" \
  -ex "load" \
  -ex "monitor reset init"
```

#### 方法 C: 使用 VSCode 调试器（推荐）

1. 在 VSCode 中打开项目
2. 按 `F5` 或点击调试面板的 "Start Debugging"
3. 选择对应的调试配置（已在 `.vscode/launch.json` 中配置）

---

## 🔧 配置文件说明

### stlink-f103.cfg

适用于 ST-Link 调试器 + STM32F103ZE。

**特点:**
- 使用 HLA (High Level Adapter) 接口
- SWD 速度: 1.8 MHz
- 包含烧录和验证辅助函数

**修改选项:**
```tcl
# 调整 SWD 速度 (如果连接不稳定，可以降低)
adapter speed 1000  # 降低到 1 MHz

# 如果需要使用 JTAG 而不是 SWD
transport select hla_jtag
```

### cmsis-dap-f103.cfg

适用于 CMSIS-DAP / DAPLink 调试器 + STM32F103ZE。

**特点:**
- 标准 CMSIS-DAP 协议
- 兼容多种开源调试器
- SWD 速度: 1 MHz

**指定设备 VID/PID:**
```tcl
# 取消注释并填入你的设备 ID
cmsis_dap vid_pid 0x0d28 0x0204

# 常见 CMSIS-DAP 设备:
# DAPLink:      0x0d28:0x0204
# Keil ULINK2:  0xc251:0x2750
# LPC-Link2:    0x1fc9:0x0090
```

**指定设备序列号:**
```tcl
# 如果有多个 CMSIS-DAP 设备连接
cmsis_dap serial 123456789
```

### wch-link-f103.cfg

适用于 WCH-Link / WCH-LinkE 调试器 + STM32F103ZE。

**特点:**
- 国产调试器，价格便宜
- 使用 CMSIS-DAP 协议
- VID/PID: 0x0416:0x5021

**注意事项:**
1. 需要安装 WCH 官方驱动
2. OpenOCD 可能需要较新版本才能完全支持
3. 如果 OpenOCD 无法识别，可以尝试使用 WCH-LinkUtility

**检查设备 VID/PID:**
```bash
# 在 Windows PowerShell 中
Get-PnpDevice | Where-Object {$_.FriendlyName -like "*WCH*"}
```

### stlink-f405.cfg

适用于 ST-Link 调试器 + STM32F405RG。

配置与 `stlink-f103.cfg` 类似，但使用 `stm32f4x.cfg` 目标配置。

---

## 📝 自定义配置

### 修改 SWD 速度

```tcl
# 在配置文件中修改
adapter speed 1000  # 单位: kHz
```

常见速度设置:
- **500 kHz**: 最稳定，用于长杜邦线或干扰环境
- **1000 kHz**: 标准速度
- **1800 kHz**: 快速，用于短距离连接
- **4000 kHz**: 最快（需要调试器和芯片支持）

### 添加自定义烧录函数

在配置文件末尾添加：

```tcl
proc my_flash {bin_file address} {
    reset halt
    flash write_image erase $bin_file $address bin
    verify_image $bin_file $address bin
    reset run
}
```

使用方法:
```bash
openocd -f openocd-configs/stlink-f103.cfg \
  -c init \
  -c "my_flash firmware.bin 0x08000000" \
  -c exit
```

### 启用 SWO (Serial Wire Output) 跟踪

在配置文件中添加：

```tcl
# 启用 ITM (Instrumentation Trace Macrocell)
$_TARGETNAME configure -event reset-init {
    # 设置 TPIU 时钟
    mmw 0xE0042004 0x00000027 0
    
    # 设置 ITM 通道
    mww 0xE0000E80 0x00000001
    mww 0xE0000E00 0x00000001
    mww 0xE0000FB0 0xC5ACCE55
}

# 启动 SWO 跟踪
tpiu config internal swo.log uart off 72000000
```

---

## 🐛 故障排除

### 问题 1: `Error: unable to find a matching CMSIS-DAP device`

**原因:** OpenOCD 找不到 CMSIS-DAP 设备

**解决方法:**
1. 检查 USB 连接
2. 确认设备管理器中识别了调试器
3. 指定正确的 VID/PID:
   ```tcl
   cmsis_dap vid_pid 0x0416 0x5021
   ```
4. 尝试不同的 USB 端口

### 问题 2: `Error: could not get configuration descriptor`

**原因:** USB 驱动问题

**解决方法:**
1. 安装调试器的官方驱动
2. 对于 WCH-Link，安装 WCH 官方驱动
3. 使用 Zadig 工具安装 WinUSB 驱动（适用于 CMSIS-DAP）

### 问题 3: `Error: init mode failed`

**原因:** 无法连接到目标芯片

**解决方法:**
1. 检查 SWD 连接（SWDIO, SWCLK, GND, VCC）
2. 确认目标板已上电
3. 降低 SWD 速度:
   ```tcl
   adapter speed 500
   ```
4. 检查目标板的 BOOT0/BOOT1 引脚设置

### 问题 4: `Error: Target not halted`

**原因:** 芯片正在运行，无法烧录

**解决方法:**
1. 使用 `reset halt` 停止芯片
2. 检查是否启用了读保护（RDP）
3. 尝试断电重启后立即连接

### 问题 5: WCH-Link 无法在 OpenOCD 中使用

**解决方法:**
1. 使用 WCH 官方工具 WCH-LinkUtility
2. 或者使用 WCH 提供的修改版 OpenOCD
3. 确认 WCH-Link 固件版本是否支持 ARM 芯片（部分仅支持 RISC-V）

---

## 📚 更多资源

### OpenOCD 官方文档
- 官网: http://openocd.org/
- 用户手册: http://openocd.org/doc/html/index.html
- GitHub: https://github.com/openocd-org/openocd

### 调试器资源
- **ST-Link**: https://www.st.com/en/development-tools/st-link-v2.html
- **CMSIS-DAP**: https://arm-software.github.io/CMSIS_5/DAP/html/index.html
- **WCH-Link**: https://www.wch.cn/products/WCH-Link.html

### 相关文档
- `.vscode/launch.json` - VSCode 调试配置
- `.vscode/tasks.json` - 编译和烧录任务
- `cubemx-validation-test/VSCODE_SETUP_GUIDE.md` - 完整开发环境指南

---

## 💡 使用技巧

### 快速烧录（不启动调试）

```bash
# 创建别名（在 ~/.bashrc 或 ~/.bash_profile 中）
alias flash-f103='openocd -f openocd-configs/stlink-f103.cfg -c "program rst-control-fw/control/build/control.elf verify reset exit"'

# 使用
flash-f103
```

### 读取芯片信息

```bash
openocd -f openocd-configs/stlink-f103.cfg \
  -c init \
  -c "flash info 0" \
  -c exit
```

### 擦除整个 Flash

```bash
openocd -f openocd-configs/stlink-f103.cfg \
  -c init \
  -c "reset halt" \
  -c "stm32f1x mass_erase 0" \
  -c "reset run" \
  -c exit
```

### 读取 Flash 内容到文件

```bash
openocd -f openocd-configs/stlink-f103.cfg \
  -c init \
  -c "reset halt" \
  -c "dump_image firmware_backup.bin 0x08000000 0x10000" \
  -c exit
```

---

**最后更新:** 2026-08-10  
**维护者:** Claude (Robotic-Arm 项目)
