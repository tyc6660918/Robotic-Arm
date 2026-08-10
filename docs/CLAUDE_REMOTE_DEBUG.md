# Claude 远程调试接入指南

本文档说明如何让 Claude 能够接入你的开发板进行远程调试和问题排查。

---

## 🎯 目标

让 Claude 能够：
1. ✅ 读取开发板的实时状态（寄存器、内存、外设）
2. ✅ 设置断点并查看调用栈
3. ✅ 分析 HardFault 和其他错误
4. ✅ 验证外设配置（GPIO, USART, DMA 等）
5. ✅ 执行测试代码并获取结果

---

## 📋 工作原理

```
你的开发板 <--SWD--> 调试器 <--USB--> 你的电脑 <--OpenOCD--> GDB 服务器
                                                              |
                                                              v
                                            你把命令输出发给 Claude
                                                              |
                                                              v
                                            Claude 分析并给出下一步命令
```

---

## 🚀 快速设置

### 第 1 步：启动 OpenOCD 服务器

在一个终端中保持运行：

```bash
cd /e/Robotic-Arm

# 根据你的调试器选择配置
openocd -f openocd-configs/stlink-f103.cfg        # ST-Link
# 或
openocd -f openocd-configs/cmsis-dap-f103.cfg     # CMSIS-DAP
# 或
openocd -f openocd-configs/wch-link-f103.cfg      # WCH-Link
```

**成功标志：**
```
Info : Listening on port 3333 for gdb connections
Info : Listening on port 6666 for tcl connections
Info : Listening on port 4444 for telnet connections
```

保持这个终端运行！

### 第 2 步：连接 GDB

在另一个终端：

```bash
cd rst-control-fw/control/build
arm-none-eabi-gdb control.elf

# 在 GDB 提示符下
(gdb) target extended-remote localhost:3333
(gdb) monitor reset halt
```

---

## 🔧 调试命令模板

当你向 Claude 求助时，运行这些命令并把输出发给我：

### 基础信息收集

```bash
# 1. 当前程序状态
(gdb) info program
(gdb) print $pc
(gdb) print $sp

# 2. 调用栈
(gdb) backtrace

# 3. 寄存器状态
(gdb) info registers

# 4. 局部变量
(gdb) info locals

# 5. 断点列表
(gdb) info breakpoints
```

**把以上所有输出复制粘贴发给 Claude。**

### HardFault 分析

如果程序卡在 HardFault：

```bash
# 1. 查看调用栈
(gdb) backtrace

# 2. 查看出错原因
(gdb) x/1xw 0xE000ED28    # CFSR
(gdb) x/1xw 0xE000ED2C    # HFSR
(gdb) x/1xw 0xE000ED34    # BFAR (Bus Fault Address)
(gdb) x/1xw 0xE000ED38    # AFSR

# 3. 查看出错时的寄存器
(gdb) info registers

# 4. 反汇编出错位置
(gdb) disassemble $pc-16,$pc+16
```

**把以上所有输出发给 Claude，我会告诉你问题原因和修复方法。**

### GPIO 状态检查

```bash
# GPIOA 状态
(gdb) x/8xw 0x40010800    # CRL, CRH, IDR, ODR, BSRR, BRR, LCKR

# GPIOB 状态
(gdb) x/8xw 0x40010C00

# GPIOC 状态
(gdb) x/8xw 0x40011000
```

### USART 状态检查

```bash
# USART1 寄存器
(gdb) x/7xw 0x40013800    # SR, DR, BRR, CR1, CR2, CR3, GTPR

# 检查波特率配置
(gdb) print/x *(uint32_t*)0x40013808
```

### DMA 状态检查

```bash
# DMA1 全局状态
(gdb) x/1xw 0x40020000    # ISR

# DMA1 Channel 1 配置
(gdb) x/5xw 0x40020008    # CCR, CNDTR, CPAR, CMAR

# DMA1 Channel 4 配置 (USART1_TX)
(gdb) x/5xw 0x40020044

# DMA1 Channel 5 配置 (USART1_RX)
(gdb) x/5xw 0x40020058
```

### SPI 状态检查

```bash
# SPI1 寄存器
(gdb) x/6xw 0x40013000    # CR1, CR2, SR, DR, CRCPR, RXCRCR, TXCRCR

# SPI2 寄存器
(gdb) x/6xw 0x40003800
```

### RCC 时钟配置检查

```bash
# RCC 寄存器
(gdb) x/8xw 0x40021000    # CR, CFGR, CIR, APB2RSTR, APB1RSTR, AHBENR, APB2ENR, APB1ENR

# 系统时钟频率
(gdb) print SystemCoreClock
```

### 内存转储

```bash
# 转储指定地址的内存（16 字节，十六进制）
(gdb) x/16xb 0x20000000

# 转储字符串
(gdb) x/s 0x20000100

# 转储结构体（假设 40 字节）
(gdb) x/40xb &my_struct
```

---

## 📸 使用场景

### 场景 1: 程序不运行

**你做：**
```bash
(gdb) monitor reset halt
(gdb) print $pc
(gdb) backtrace
(gdb) info registers
```

**发给 Claude：** 完整输出

**Claude 会告诉你：**
- 程序卡在哪里
- 是否进入了错误处理函数
- 可能的原因和修复方法

### 场景 2: USART 没有输出

**你做：**
```bash
# 检查 GPIO 配置（PA9=TX, PA10=RX）
(gdb) x/8xw 0x40010800

# 检查 USART1 配置
(gdb) x/7xw 0x40013800

# 检查 RCC 时钟使能
(gdb) x/1xw 0x40021018    # APB2ENR
```

**发给 Claude：** 完整输出

**Claude 会告诉你：**
- GPIO 是否配置为复用功能
- 波特率是否正确
- 时钟是否使能
- 需要修改什么

### 场景 3: DMA 传输失败

**你做：**
```bash
# DMA 中断状态
(gdb) x/1xw 0x40020000

# DMA 通道配置
(gdb) x/5xw 0x40020044    # Channel 4

# USART 状态
(gdb) x/7xw 0x40013800
```

**发给 Claude：** 完整输出

**Claude 会告诉你：**
- DMA 是否正确配置
- 是否有传输错误
- 通道优先级是否冲突
- 如何修复

### 场景 4: 程序跑飞了

**你做：**
```bash
(gdb) monitor halt
(gdb) print $pc
(gdb) backtrace
(gdb) disassemble $pc-32,$pc+32
```

**发给 Claude：** 完整输出

**Claude 会告诉你：**
- PC 是否指向有效地址
- 是否栈溢出
- 是否有野指针
- 如何定位问题代码

---

## 🎓 示例对话

### 完整示例：USART 调试

**你：** "我的 USART1 发送数据没反应，帮我看看"

**Claude：** "请运行以下命令并把输出发给我："
```bash
(gdb) monitor reset halt
(gdb) x/8xw 0x40010800    # GPIOA
(gdb) x/7xw 0x40013800    # USART1
(gdb) x/1xw 0x40021018    # RCC APB2ENR
```

**你：** [粘贴输出]
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

**Claude：** "找到问题了！

1. **GPIOA 配置错误**: `0x444444B4` 说明 PA9 (USART1_TX) 配置为推挽输出，但应该配置为复用推挽输出（`0xB`）

2. **USART1 已使能**: CR1=0x200C 正确（UE=1, TE=1）

3. **时钟已使能**: APB2ENR bit 14=1，USART1 时钟正常

**修复方法：**

在 `usart.c` 的初始化代码中，确保 GPIO 配置为复用功能：

```c
// PA9 = USART1_TX (复用推挽输出, 50MHz)
GPIOA->CRH &= ~(0xF << 4);
GPIOA->CRH |= (0xB << 4);  // CNF=10b (复用推挽), MODE=11b (50MHz)
```

或者在 CubeMX 中重新配置 PA9 为 USART1_TX。"

---

## 🔄 工作流程

### 正常调试流程

1. **你启动 OpenOCD 和 GDB**
2. **遇到问题时，运行诊断命令**
3. **把命令输出发给 Claude**
4. **Claude 分析并给出具体修复步骤**
5. **你修改代码**
6. **重新编译和烧录**
7. **验证问题是否解决**

### 复杂问题流程

1. **Claude 给你一系列诊断命令**
2. **你依次执行并发送输出**
3. **Claude 缩小问题范围**
4. **Claude 可能要求你设置断点或监视点**
5. **你运行程序到断点，再发送状态**
6. **Claude 确定根本原因**
7. **Claude 给出完整修复方案**

---

## 💡 提示

### 为了更高效，请：

1. **一次性发送所有输出** - 不要分段发送，这样 Claude 能一次看全
2. **包含完整输出** - 不要省略"看起来不重要"的部分
3. **说明你的目标** - 比如"我想让 LED 闪烁"而不是"GPIO 不工作"
4. **说明你已经尝试过什么** - 避免重复建议
5. **提供错误现象** - 比如"没有输出" vs "输出乱码" vs "卡死"

### 常见误区

❌ **不好：** "帮我看看这个项目"  
✅ **好的：** "USART1 发送数据时程序卡死，这是 GDB 的输出：[粘贴]"

❌ **不好：** "DMA 不工作"  
✅ **好的：** "DMA1 Channel 4 配置了 USART1_TX，但是 ISR 寄存器显示 TEIF4=1（传输错误），这是完整寄存器状态：[粘贴]"

❌ **不好：** 只发送部分输出  
✅ **好的：** 发送完整的寄存器转储、调用栈、和错误信息

---

## 🛠️ 辅助工具

### 自动收集诊断信息脚本

创建文件 `gdb-diagnostic.txt`:

```gdb
# 基础信息
echo \n=== Program Status ===\n
info program
print $pc
print $sp

# 调用栈
echo \n=== Backtrace ===\n
backtrace

# 寄存器
echo \n=== Registers ===\n
info registers

# 局部变量
echo \n=== Local Variables ===\n
info locals

# GPIO 状态
echo \n=== GPIOA ===\n
x/8xw 0x40010800

# USART1 状态
echo \n=== USART1 ===\n
x/7xw 0x40013800

# DMA1 状态
echo \n=== DMA1 ISR ===\n
x/1xw 0x40020000

# RCC 状态
echo \n=== RCC ===\n
x/8xw 0x40021000
```

使用方法:
```bash
(gdb) source gdb-diagnostic.txt > diagnostic_output.txt
```

然后把 `diagnostic_output.txt` 发给 Claude。

---

## 📞 何时向 Claude 求助

### 应该求助的情况

✅ 程序卡死或跑飞  
✅ HardFault 或其他异常  
✅ 外设不工作（USART, SPI, DMA, GPIO 等）  
✅ 看到奇怪的寄存器值不知道含义  
✅ 需要分析复杂的时序问题  
✅ 需要验证配置是否正确  

### 可以自己解决的情况

🔧 简单的编译错误（先尝试理解错误信息）  
🔧 明显的语法错误  
🔧 已知的 bug（先查看代码注释和文档）  

---

## 🎯 预期效果

设置完成后，当你遇到问题时：

**以前:**
1. 盲目尝试修改代码
2. 重新编译、烧录
3. 还是不工作
4. 重复数十次...

**现在:**
1. 运行 GDB 诊断命令（30 秒）
2. 把输出发给 Claude（10 秒）
3. Claude 精确告诉你问题在哪（1 分钟内）
4. 按照建议修改（5 分钟）
5. 一次性解决问题 ✅

**时间节省:** 从数小时缩短到几分钟！

---

## 📚 相关文档

- `docs/DEBUGGING_GUIDE.md` - 完整调试指南
- `openocd-configs/README.md` - OpenOCD 配置说明
- `.vscode/launch.json` - VSCode 调试配置
- `cubemx-validation-test/VSCODE_SETUP_GUIDE.md` - 开发环境设置

---

**准备好了吗？** 启动 OpenOCD，连接 GDB，开始调试！

有问题随时把 GDB 输出发给我！
