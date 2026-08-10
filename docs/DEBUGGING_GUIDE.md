# STM32 调试完全指南

本指南将教你如何使用 VSCode + OpenOCD + GDB 调试 STM32 固件。

---

## 📋 目录

1. [硬件准备](#硬件准备)
2. [软件准备](#软件准备)
3. [快速开始](#快速开始)
4. [调试方法](#调试方法)
5. [高级功能](#高级功能)
6. [故障排除](#故障排除)
7. [调试技巧](#调试技巧)

---

## 🔌 硬件准备

### 调试器连接

#### 最小连接（4 线 SWD）
```
调试器          STM32 开发板
-------         -----------
SWDIO    <-->   SWDIO (PA13)
SWCLK    <-->   SWCLK (PA14)
GND      <-->   GND
VCC      <-->   3.3V (可选，用于供电检测)
```

#### 完整连接（带复位和串口）
```
调试器          STM32 开发板
-------         -----------
SWDIO    <-->   SWDIO (PA13)
SWCLK    <-->   SWCLK (PA14)
NRST     <-->   NRST (复位引脚)
GND      <-->   GND
VCC      <-->   3.3V
SWO      <-->   PB3 (可选，用于 ITM 跟踪)
TX       <-->   RX (可选，用于串口输出)
RX       <-->   TX (可选，用于串口输入)
```

### 注意事项

1. **必须共地**: 调试器和开发板的 GND 必须连接
2. **电压匹配**: 确保调试器和开发板都是 3.3V
3. **线长限制**: SWD 线不宜太长（建议 < 30cm），否则会影响稳定性
4. **干扰**: 远离高压、高频设备

---

## 💻 软件准备

### 已安装的工具

✅ **OpenOCD** - `C:/Users/TYC/.embedded-tools/openocd/xpack-openocd-0.12.0-7/`  
✅ **ARM GCC** - 交叉编译工具链  
✅ **VSCode** - 代码编辑器  
✅ **Cortex-Debug** - VSCode 调试扩展

### 验证安装

```bash
# 检查 OpenOCD
openocd --version

# 检查 GCC
arm-none-eabi-gcc --version

# 检查 GDB
arm-none-eabi-gdb --version
```

---

## 🚀 快速开始

### 步骤 1: 连接硬件

1. 用 SWD 线连接调试器和开发板（至少连接 SWDIO, SWCLK, GND）
2. 给开发板上电
3. 将调试器插入电脑 USB 口

### 步骤 2: 测试连接

```bash
# 进入项目目录
cd /e/Robotic-Arm

# 运行测试脚本
bash openocd-configs/test-connection.sh
```

如果看到 "✅ 成功连接"，说明硬件配置正确！

### 步骤 3: 在 VSCode 中调试

1. 打开 VSCode，打开项目目录
2. 在 `main.c` 的 `main()` 函数里设置断点（点击行号左侧）
3. 按 `F5` 或点击"运行和调试"面板
4. 选择对应的调试配置（例如 "🐛 rst-control-fw (CMSIS-DAP)"）
5. 程序会自动编译、烧录、启动，并停在断点处

---

## 🐛 调试方法

### 方法 1: VSCode 图形化调试（推荐）

**优点:**
- 最直观，图形化界面
- 可以查看变量、寄存器、内存
- 支持条件断点、监视点
- 集成编译和烧录

**使用步骤:**

1. **设置断点**: 在代码行号左侧点击，出现红点
2. **启动调试**: 按 `F5`，选择配置
3. **控制执行**:
   - `F5` - 继续运行
   - `F10` - 单步跳过（不进入函数）
   - `F11` - 单步进入（进入函数内部）
   - `Shift+F11` - 单步跳出（退出当前函数）
   - `Ctrl+Shift+F5` - 重启调试
   - `Shift+F5` - 停止调试

4. **查看变量**:
   - 鼠标悬停在变量上查看值
   - 左侧"变量"面板查看所有局部变量
   - 右键变量 → "添加到监视" 持续监视

5. **查看外设寄存器**:
   - 左侧"外设"面板（需要 SVD 文件）
   - 可以展开查看 USART, GPIO, DMA 等外设的寄存器值

### 方法 2: 命令行调试

**优点:**
- 灵活，可以执行任意 GDB 命令
- 适合自动化脚本
- 远程调试

**终端 1: 启动 OpenOCD 服务器**
```bash
cd /e/Robotic-Arm
openocd -f openocd-configs/stlink-f103.cfg
```

保持这个终端运行。

**终端 2: 启动 GDB**
```bash
cd rst-control-fw/control/build
arm-none-eabi-gdb control.elf

# 在 GDB 提示符下
(gdb) target extended-remote localhost:3333
(gdb) monitor reset halt
(gdb) load                    # 烧录固件
(gdb) break main              # 在 main 设置断点
(gdb) continue                # 运行到断点
(gdb) next                    # 单步执行
(gdb) print my_variable       # 查看变量
(gdb) info registers          # 查看寄存器
(gdb) backtrace               # 查看调用栈
```

### 方法 3: 仅烧录，不调试

```bash
# 使用 OpenOCD 烧录
openocd -f openocd-configs/stlink-f103.cfg \
  -c "program rst-control-fw/control/build/control.elf verify reset exit"
```

或使用 VSCode 任务:
- 按 `Ctrl+Shift+P`
- 输入 "Tasks: Run Task"
- 选择 "📥 Flash ..." 对应的任务

---

## 🔬 高级功能

### 条件断点

在断点上右键 → "编辑断点" → 输入条件

```c
// 示例：只有当 count > 10 时才触发断点
count > 10
```

### 监视点（Watchpoint）

当变量值改变时自动暂停：

```bash
# 在 GDB 中
(gdb) watch my_variable
```

### 内存查看

```bash
# 查看内存（16 进制）
(gdb) x/16xw 0x20000000

# 查看内存（ASCII 字符串）
(gdb) x/s 0x20000000
```

### 寄存器查看

```bash
# 查看所有寄存器
(gdb) info registers

# 查看特定寄存器
(gdb) print $r0
(gdb) print $pc
(gdb) print $sp
```

### ITM 跟踪输出

ITM (Instrumentation Trace Macrocell) 允许你从固件发送调试信息到 OpenOCD。

**固件端（在 main.c 中）:**

```c
// 初始化 ITM
void ITM_SendChar(char ch) {
    while (ITM->PORT[0].u32 == 0);  // 等待就绪
    ITM->PORT[0].u8 = (uint8_t)ch;  // 发送字符
}

// 使用
ITM_SendChar('H');
ITM_SendChar('i');
ITM_SendChar('\n');
```

**OpenOCD 端:**

在配置文件中启用 SWO，VSCode 会自动显示在"输出"面板。

### 硬件断点 vs 软件断点

STM32F1 有 **6 个硬件断点**, STM32F4 也是 6 个。

- **硬件断点**: 在 Flash 中执行代码时使用，不修改代码
- **软件断点**: 在 RAM 中执行代码时使用，需要修改代码

GDB 会自动选择，但如果硬件断点用完，会提示错误。

### Flash 下载加速

修改 OpenOCD 配置文件，增加 SWD 速度：

```tcl
adapter speed 4000  # 4 MHz（如果硬件支持）
```

---

## ❌ 故障排除

### 问题 1: OpenOCD 无法连接到调试器

**症状:**
```
Error: unable to find a matching CMSIS-DAP device
```

**解决方法:**
1. 检查 USB 连接
2. 确认设备管理器中识别了调试器
3. 尝试不同的 USB 口
4. 检查 VID/PID 是否正确
5. 安装调试器官方驱动

### 问题 2: OpenOCD 无法连接到目标芯片

**症状:**
```
Error: init mode failed (unable to connect to the target)
```

**解决方法:**
1. 检查 SWD 连接（SWDIO, SWCLK, GND）
2. 确认开发板已上电
3. 降低 SWD 速度（在配置文件中改为 500 kHz）
4. 检查 BOOT0/BOOT1 引脚设置
5. 尝试断电重启开发板
6. 检查芯片是否启用了读保护（RDP）

### 问题 3: VSCode 调试器找不到符号

**症状:**
```
Cannot find source file ...
```

**解决方法:**
1. 确保使用 `-g` 选项编译（包含调试信息）
2. 检查 `.elf` 文件路径是否正确
3. 确保源文件没有移动位置

### 问题 4: 烧录后程序不运行

**可能原因:**
1. BOOT0 引脚设置不正确（应该接 GND）
2. 看门狗复位（需要在代码中喂狗）
3. 时钟配置错误
4. 硬件故障（HardFault）

**调试方法:**
```bash
# 连接后读取 PC 寄存器
(gdb) monitor reset halt
(gdb) print $pc

# 如果 PC 在 HardFault_Handler，说明发生了硬件错误
(gdb) backtrace  # 查看调用栈
```

### 问题 5: 单步调试时代码跳来跳去

**原因:** 编译器优化导致

**解决方法:**
在 CMakeLists.txt 中使用 `-O0` 关闭优化：

```cmake
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -O0 -g3")
```

### 问题 6: WCH-Link 无法工作

**解决方法:**
1. 确认安装了 WCH 官方驱动
2. 检查 WCH-Link 固件版本是否支持 ARM（部分只支持 RISC-V）
3. 使用 WCH-LinkUtility 测试连接
4. 考虑改用 ST-Link（兼容性更好）

---

## 💡 调试技巧

### 技巧 1: 查找 HardFault 原因

当程序进入 HardFault 时：

```bash
(gdb) monitor reset halt
(gdb) backtrace         # 查看调用栈
(gdb) info registers    # 查看寄存器
(gdb) print $lr         # 查看返回地址

# 查看 CFSR (Configurable Fault Status Register)
(gdb) x/1xw 0xE000ED28

# 查看 HFSR (HardFault Status Register)
(gdb) x/1xw 0xE000ED2C

# 查看出错地址
(gdb) x/1xw 0xE000ED34
```

常见 HardFault 原因:
- 访问未对齐的地址
- 访问未映射的内存
- 除零错误
- 栈溢出

### 技巧 2: 实时查看 GPIO 状态

```bash
# 查看 GPIOA 的 IDR (Input Data Register)
(gdb) x/1xw 0x40010808

# 查看 GPIOA 的 ODR (Output Data Register)
(gdb) x/1xw 0x4001080C
```

### 技巧 3: 强制修改变量

```bash
# 修改变量值
(gdb) set variable my_counter = 100

# 修改寄存器
(gdb) set $r0 = 0x12345678

# 修改内存
(gdb) set {int}0x20000000 = 42
```

### 技巧 4: 反汇编查看代码

```bash
# 反汇编当前函数
(gdb) disassemble

# 反汇编指定函数
(gdb) disassemble main

# 显示源代码和汇编混合
(gdb) set disassemble-next-line on
```

### 技巧 5: 保存和恢复调试会话

**保存断点和监视点:**
```bash
(gdb) save breakpoints breakpoints.txt
```

**恢复:**
```bash
(gdb) source breakpoints.txt
```

### 技巧 6: 远程调试

如果 OpenOCD 运行在另一台机器上：

```bash
# 在 GDB 中连接到远程 OpenOCD
(gdb) target extended-remote 192.168.1.100:3333
```

### 技巧 7: 批量测试

创建 GDB 脚本文件 `test.gdb`:

```gdb
target extended-remote localhost:3333
monitor reset halt
load
break main
continue
next 10
info locals
quit
```

运行:
```bash
arm-none-eabi-gdb control.elf -x test.gdb
```

---

## 📚 参考资料

### GDB 常用命令

| 命令 | 说明 |
|------|------|
| `run` / `r` | 运行程序 |
| `continue` / `c` | 继续运行 |
| `next` / `n` | 单步跳过 |
| `step` / `s` | 单步进入 |
| `finish` | 跳出当前函数 |
| `break` / `b` | 设置断点 |
| `watch` | 设置监视点 |
| `print` / `p` | 打印变量 |
| `info` / `i` | 查看信息 |
| `backtrace` / `bt` | 查看调用栈 |
| `quit` / `q` | 退出 GDB |

### OpenOCD 常用命令

在 GDB 中使用 `monitor <命令>` 执行 OpenOCD 命令：

| 命令 | 说明 |
|------|------|
| `monitor reset halt` | 复位并停止 |
| `monitor reset run` | 复位并运行 |
| `monitor halt` | 停止 CPU |
| `monitor resume` | 继续运行 |
| `monitor flash info 0` | 查看 Flash 信息 |
| `monitor reg` | 查看寄存器 |

### VSCode 快捷键

| 快捷键 | 功能 |
|--------|------|
| `F5` | 启动调试 / 继续 |
| `F9` | 设置/取消断点 |
| `F10` | 单步跳过 |
| `F11` | 单步进入 |
| `Shift+F11` | 单步跳出 |
| `Shift+F5` | 停止调试 |
| `Ctrl+Shift+F5` | 重启调试 |

---

## 🎯 下一步

1. **学习使用断点和监视点**
2. **练习 GDB 命令行调试**
3. **学习如何分析 HardFault**
4. **学习使用 ITM 跟踪输出**
5. **阅读 ARM Cortex-M 调试文档**

---

**文档版本:** 1.0  
**最后更新:** 2026-08-10  
**作者:** Claude  
**反馈:** 如有问题，请在项目 Issue 中提出
