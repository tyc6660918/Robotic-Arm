# Claude AI 远程调试接入技术指南

本文档规定 Claude AI 接入开发板进行远程调试与问题排查的技术流程。

---

## 一、工作目标

实现 Claude AI 具备以下诊断能力：
1. 读取开发板实时状态（寄存器、内存、外设寄存器）
2. 设置断点并查看函数调用栈
3. 分析 HardFault 与其他异常触发原因
4. 验证外设配置正确性（GPIO、USART、DMA、SPI 等）
5. 执行测试代码并获取运行结果

---

## 二、工作原理

```
目标开发板 <--SWD 协议--> 硬件调试器 <--USB--> 上位机 <--OpenOCD--> GDB 服务器
                                                                    |
                                                                    v
                                            操作人员将命令输出提交至 Claude AI
                                                                    |
                                                                    v
                                            Claude AI 执行分析并生成下一步诊断命令
```

---

## 三、快速配置规程

### 步骤 1：启动 OpenOCD 服务

在专用终端中保持以下进程运行：

```bash
cd /e/Robotic-Arm

# 根据调试器类型选择对应配置文件
openocd -f debug/openocd-configs/stlink-f103.cfg        # ST-Link 调试器
# 或
openocd -f debug/openocd-configs/cmsis-dap-f103.cfg     # CMSIS-DAP 调试器
# 或
openocd -f debug/openocd-configs/wch-link-f103.cfg      # WCH-Link 调试器
```

**启动成功标志：**
```
Info : Listening on port 3333 for gdb connections
Info : Listening on port 6666 for tcl connections
Info : Listening on port 4444 for telnet connections
```

该终端进程需持续保持运行状态。

### 步骤 2：连接 GDB 客户端

在另一终端中执行：

```bash
cd robots/Dummy-Arm/firmware/stm32-control/control
arm-none-eabi-gdb MDK-ARM/control/control.axf

# 在 GDB 交互提示符下执行
(gdb) target extended-remote localhost:3333
(gdb) monitor reset halt
```

---

## 四、调试命令模板

向 Claude AI 请求协助时，按以下模板执行命令并完整提交输出结果。

### 基础信息采集模板

```bash
# 1. 当前程序运行状态
(gdb) info program
(gdb) print $pc
(gdb) print $sp

# 2. 函数调用栈
(gdb) backtrace

# 3. 核心寄存器状态
(gdb) info registers

# 4. 局部变量列表
(gdb) info locals

# 5. 断点配置列表
(gdb) info breakpoints
```

将以上全部命令输出完整提交至 Claude AI。

### HardFault 异常分析模板

当程序执行流进入 HardFault 异常处理时，执行以下诊断：

```bash
# 1. 查看调用栈
(gdb) backtrace

# 2. 读取故障状态寄存器
(gdb) x/1xw 0xE000ED28    # CFSR（可配置故障状态寄存器）
(gdb) x/1xw 0xE000ED2C    # HFSR（硬故障状态寄存器）
(gdb) x/1xw 0xE000ED34    # BFAR（总线故障地址寄存器）
(gdb) x/1xw 0xE000ED38    # AFSR（辅助故障状态寄存器）

# 3. 故障时刻寄存器组
(gdb) info registers

# 4. 故障点前后反汇编
(gdb) disassemble $pc-16,$pc+16
```

将以上全部输出提交至 Claude AI，将返回根因分析与修复方案。

### GPIO 状态检查模板

```bash
# GPIOA 寄存器组（CRL、CRH、IDR、ODR、BSRR、BRR、LCKR）
(gdb) x/8xw 0x40010800

# GPIOB 寄存器组
(gdb) x/8xw 0x40010C00

# GPIOC 寄存器组
(gdb) x/8xw 0x40011000
```

### USART 状态检查模板

```bash
# USART1 寄存器组（SR、DR、BRR、CR1、CR2、CR3、GTPR）
(gdb) x/7xw 0x40013800

# 检查波特率配置寄存器
(gdb) print/x *(uint32_t*)0x40013808
```

### DMA 状态检查模板

```bash
# DMA1 全局中断状态寄存器
(gdb) x/1xw 0x40020000    # ISR

# DMA1 通道 1 配置寄存器组（CCR、CNDTR、CPAR、CMAR）
(gdb) x/5xw 0x40020008

# DMA1 通道 4 配置（USART1_TX 通道）
(gdb) x/5xw 0x40020044

# DMA1 通道 5 配置（USART1_RX 通道）
(gdb) x/5xw 0x40020058
```

### SPI 状态检查模板

```bash
# SPI1 寄存器组（CR1、CR2、SR、DR、CRCPR、RXCRCR、TXCRCR）
(gdb) x/6xw 0x40013000

# SPI2 寄存器组
(gdb) x/6xw 0x40003800
```

### RCC 时钟配置检查模板

```bash
# RCC 寄存器组（CR、CFGR、CIR、APB2RSTR、APB1RSTR、AHBENR、APB2ENR、APB1ENR）
(gdb) x/8xw 0x40021000

# 读取系统核心时钟频率
(gdb) print SystemCoreClock
```

### 内存转储模板

```bash
# 以十六进制转储指定地址起 16 字节内存
(gdb) x/16xb 0x20000000

# 以 ASCII 字符串格式转储
(gdb) x/s 0x20000100

# 转储结构体（假设结构体长度 40 字节）
(gdb) x/40xb &my_struct
```

---

## 五、典型应用场景

### 场景一：程序未启动运行

**操作人员执行：**
```bash
(gdb) monitor reset halt
(gdb) print $pc
(gdb) backtrace
(gdb) info registers
```

**提交内容：**完整命令输出。

**AI 返回内容：**
- 程序计数器当前指向的代码位置
- 是否进入异常处理函数
- 可能原因与修复建议

### 场景二：USART 无数据输出

**操作人员执行：**
```bash
# 检查 GPIO 配置（PA9=TX、PA10=RX）
(gdb) x/8xw 0x40010800

# 检查 USART1 配置
(gdb) x/7xw 0x40013800

# 检查 RCC 时钟使能状态
(gdb) x/1xw 0x40021018    # APB2ENR
```

**提交内容：**完整命令输出。

**AI 返回内容：**
- GPIO 是否已配置为复用功能模式
- 波特率配置正确性判定
- 外设时钟使能状态
- 具体修改建议

### 场景三：DMA 传输失败

**操作人员执行：**
```bash
# DMA 中断状态寄存器
(gdb) x/1xw 0x40020000

# DMA 通道配置
(gdb) x/5xw 0x40020044    # 通道 4

# USART 状态寄存器
(gdb) x/7xw 0x40013800
```

**提交内容：**完整命令输出。

**AI 返回内容：**
- DMA 配置正确性判定
- 传输错误标志分析
- 通道优先级冲突检测
- 修复方案

### 场景四：程序执行流异常跳转

**操作人员执行：**
```bash
(gdb) monitor halt
(gdb) print $pc
(gdb) backtrace
(gdb) disassemble $pc-32,$pc+32
```

**提交内容：**完整命令输出。

**AI 返回内容：**
- PC 寄存器指向地址的有效性判定
- 栈溢出可能性分析
- 野指针访问可能性分析
- 问题代码定位方法

---

## 六、完整诊断示例：USART 调试

**问题描述：** USART1 数据发送功能异常，无输出信号。

**AI 请求诊断命令：**

```bash
(gdb) monitor reset halt
(gdb) x/8xw 0x40010800    # GPIOA 配置
(gdb) x/7xw 0x40013800    # USART1 配置
(gdb) x/1xw 0x40021018    # RCC APB2ENR
```

**诊断命令输出：**
```
(gdb) x/8xw 0x40010800
0x40010800:     0x44444444      0x444444B4      0x00000000      0x00000000
0x40010810:     0x00000000      0x00000000      0x00000000      0x00000000

(gdb) x/7xw 0x40013800
0x40013800:     0x000000C0      0x00000000      0x00000271      0x0000200C
0x40013810:     0x00000000      0x00000000      0x00000000

(gdb) x/1xw 0x40021018
0x40021018:     0x00004005
```

**AI 分析结论：**

1. **GPIOA 配置错误**：`0x444444B4` 表明 PA9（USART1_TX）当前配置为推挽输出模式，正确配置应为复用推挽输出模式（`0xB`）
2. **USART1 已使能**：CR1=0x200C 配置正确（UE=1，TE=1）
3. **时钟已使能**：APB2ENR 第 14 位=1，USART1 时钟正常

**修复方案：**

在 `usart.c` 初始化代码中，确保 GPIO 配置为复用功能：

```c
// PA9 = USART1_TX（复用推挽输出，50 MHz）
GPIOA->CRH &= ~(0xF << 4);
GPIOA->CRH |= (0xB << 4);  // CNF=10b（复用推挽），MODE=11b（50 MHz）
```

或通过 STM32CubeMX 重新配置 PA9 为 USART1_TX 功能。

---

## 七、标准工作流程

### 常规调试流程

1. 操作人员启动 OpenOCD 服务与 GDB 客户端
2. 遇到问题时，执行对应诊断命令模板
3. 将全部命令输出提交至 Claude AI
4. Claude AI 执行分析并返回具体修复步骤
5. 操作人员按建议修改代码
6. 重新执行编译与烧录流程
7. 验证问题是否已解决

### 复杂问题诊断流程

1. Claude AI 生成多组诊断命令序列
2. 操作人员依次执行并提交各组输出
3. Claude AI 逐步缩小问题范围
4. Claude AI 可能请求设置断点或监视点
5. 操作人员运行程序至断点后再次提交状态
6. Claude AI 确定根本原因
7. Claude AI 生成完整修复方案

---

## 八、高效提交规范

### 提交原则

1. **一次性完整提交**——避免分段提交，确保 Claude AI 可获取全部上下文
2. **包含完整输出**——不得省略任何"看似不重要"的输出内容
3. **明确说明目标**——例如"需实现 LED 闪烁功能"而非"GPIO 不工作"
4. **说明已尝试措施**——避免重复建议
5. **准确描述现象**——例如"无输出"、"输出乱码"、"执行卡死"之间存在本质差异

### 提交规范示例

不规范示例："帮我看看这个项目"

规范示例："USART1 发送数据时程序执行卡死，以下为 GDB 诊断输出：[完整粘贴]"

不规范示例："DMA 不工作"

规范示例："DMA1 通道 4 配置为 USART1_TX，但 ISR 寄存器显示 TEIF4=1（传输错误标志置位），以下为完整寄存器状态：[完整粘贴]"

---

## 九、辅助诊断工具

### 自动采集脚本

创建 GDB 脚本文件 `gdb-diagnostic.txt`：

```gdb
echo \n=== Program Status ===\n
info program
print $pc
print $sp

echo \n=== Backtrace ===\n
backtrace

echo \n=== Registers ===\n
info registers

echo \n=== Local Variables ===\n
info locals

echo \n=== GPIOA ===\n
x/8xw 0x40010800

echo \n=== USART1 ===\n
x/7xw 0x40013800

echo \n=== DMA1 ISR ===\n
x/1xw 0x40020000

echo \n=== RCC ===\n
x/8xw 0x40021000
```

使用方法：
```bash
(gdb) source gdb-diagnostic.txt > diagnostic_output.txt
```

将生成的 `diagnostic_output.txt` 提交至 Claude AI。

---

## 十、适用范围判定

### 建议提交 AI 诊断的情形

- 程序执行卡死或异常跳转
- HardFault 或其他异常触发
- 外设功能异常（USART、SPI、DMA、GPIO 等）
- 寄存器值含义不明
- 复杂时序问题分析
- 配置正确性验证需求

### 建议自行解决的情形

- 简单编译错误（先阅读错误信息）
- 明显语法错误
- 已知且已记录的 Bug（先查阅代码注释与文档）

---

## 十一、相关文档

- 完整调试技术教程 → [`完整调试技术教程.md`](完整调试技术教程.md)
- OpenOCD 配置说明 → [`../../debug/openocd-configs/配置文件使用说明.md`](../../debug/openocd-configs/配置文件使用说明.md)
- Visual Studio Code 调试配置 → [`../../.vscode/launch.json`](../../.vscode/launch.json)
- 硬件连接指南 → [`硬件连接与配置指南.md`](硬件连接与配置指南.md)
