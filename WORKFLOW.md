# 🔄 嵌入式开发工作流

**目标:** 用 VSCode + OpenOCD + GDB 替代 Keil，实现完整的开发-调试循环

---

## 📋 完整工作流

```
┌─────────────────────────────────────────────────────────────┐
│                     1. 图形化配置                              │
│  CubeMX GUI → 配置外设 → Generate Code → 生成初始化代码        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     2. 编写业务代码                            │
│  VSCode → 编辑 main.c → 实现功能逻辑                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     3. 编译固件                               │
│  arm-none-eabi-gcc → 编译 → 生成 .elf/.bin                   │
│  (自动或手动: make / cmake --build build)                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     4. 烧录固件                               │
│  OpenOCD + 调试器 → 下载到 Flash                              │
│  (VSCode F5 自动烧录，或命令行 openocd + gdb load)            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     5. 调试运行                               │
│  GDB → 断点/单步/监视 → 分析问题                              │
│  Claude 远程协助 → 读寄存器 → 诊断故障                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
                   [问题修复]
                      │
                      └──────> 回到步骤 2
```

---

## 🎯 三种启动方式

### 方式 A: VSCode 一键调试（推荐）

```bash
1. 在 VSCode 中打开项目
2. 按 F5（或点击调试面板的绿色三角）
3. 选择调试配置（如 "Debug rst-control (DAP)"）
4. 等待编译 → 烧录 → 启动调试
```

**优点:**
- ✅ 最简单，一键完成
- ✅ 自动编译 + 烧录 + 调试
- ✅ 图形化界面，容易上手

### 方式 B: 命令行手动调试

```bash
# 1. 编译
cd rst-control-fw/control
make  # 或 cmake --build build

# 2. 启动 OpenOCD（保持运行）
openocd -f ../../openocd-configs/cmsis-dap-f103.cfg

# 3. 在另一个终端启动 GDB
arm-none-eabi-gdb build/control.elf
(gdb) target remote :3333
(gdb) load
(gdb) monitor reset halt
(gdb) continue
```

**优点:**
- ✅ 更灵活，可以看到详细输出
- ✅ 方便调试 OpenOCD 配置问题
- ✅ 适合远程协助场景

### 方式 C: 只烧录不调试

```bash
# 使用 OpenOCD 烧录固件
openocd -f openocd-configs/cmsis-dap-f103.cfg \
        -c "program rst-control-fw/control/build/control.elf verify reset exit"
```

**优点:**
- ✅ 快速烧录
- ✅ 不需要保持连接
- ✅ 适合量产烧录

---

## 🛠️ 各工具的角色

| 工具 | 作用 | 何时使用 |
|------|------|---------|
| **CubeMX** | 图形化配置外设，生成初始化代码 | 需要启用新外设或修改时钟时 |
| **VSCode** | 代码编辑器 + 调试前端 | 日常编写代码和调试 |
| **arm-none-eabi-gcc** | 交叉编译器 | 每次修改代码后编译 |
| **OpenOCD** | 调试服务器，连接调试器和 GDB | 烧录固件和调试时 |
| **GDB** | 调试器 | 设置断点、单步执行、查看变量 |
| **调试器硬件** | DAP/ST-Link/J-Link | 连接 PC 和开发板 |

---

## 🔧 修改外设配置的流程

```
需要添加新外设（如 SPI、UART）
         ↓
打开 CubeMX，加载 .ioc 文件
         ↓
图形化配置外设（引脚、参数、中断等）
         ↓
点击 "Generate Code"
         ↓
⚠️ 注意：CubeMX 会重新生成初始化代码
   用户代码要放在 USER CODE BEGIN/END 注释之间
         ↓
回到 VSCode，检查生成的代码
         ↓
在 main.c 中的 USER CODE 区域编写业务逻辑
         ↓
编译 → 烧录 → 测试
```

**重要提示:**
```c
/* USER CODE BEGIN 0 */
// 你的代码放这里，CubeMX 重新生成时不会被覆盖
/* USER CODE END 0 */

// CubeMX 生成的代码（会被覆盖，不要修改）
MX_GPIO_Init();
MX_SPI1_Init();
```

---

## 🐛 调试技巧

### 1. 快速定位问题

```c
// 在关键位置打断点
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin) {
    if (GPIO_Pin == BUTTON_Pin) {
        // <- 在这里打断点
        button_pressed = 1;
    }
}
```

### 2. 监视变量变化

```bash
(gdb) watch motor_speed
# 当 motor_speed 变化时自动停止
```

### 3. 查看外设寄存器

```bash
# 查看 GPIOA 配置
(gdb) p/x *((GPIO_TypeDef*)0x40010800)

# 查看 RCC 时钟配置
(gdb) p/x *((RCC_TypeDef*)0x40021000)
```

### 4. 实时修改变量

```bash
# 强制修改变量值来测试不同场景
(gdb) set motor_speed = 100
(gdb) continue
```

### 5. 远程协助（让 Claude 帮忙）

```
你: "电机不转，不知道哪里有问题"
我: 让我看看外设配置...
    [执行 GDB 命令检查]
    问题找到了：TIM2 的时钟没有使能
    请在 main.c 中添加: __HAL_RCC_TIM2_CLK_ENABLE();
```

---

## 📊 故障排查清单

### 硬件连接问题
- [ ] 调试器连接到 PC USB 口
- [ ] SWD 线连接到开发板（SWDIO、SWCLK、GND）
- [ ] 开发板已上电
- [ ] 调试器驱动已安装

### 软件配置问题
- [ ] OpenOCD 配置文件选择正确
- [ ] VSCode launch.json 中的路径正确
- [ ] arm-none-eabi-gcc 在 PATH 中
- [ ] .elf 文件已生成（编译成功）

### 固件运行问题
- [ ] main() 函数中的循环没有被阻塞
- [ ] 外设时钟已使能
- [ ] 引脚配置正确（复用功能、上下拉等）
- [ ] 中断优先级配置合理

---

## 🚀 下一步

1. **阅读快速开始:** `QUICK_START_DEBUG.md`（5 分钟）
2. **测试硬件连接:** `openocd-configs/test-connection.sh`
3. **尝试第一次调试:** VSCode 按 F5
4. **遇到问题:** 查看 `docs/DEBUGGING_GUIDE.md`
5. **需要远程帮助:** 告诉我错误信息，我来协助

---

**工作流已就绪，开始你的嵌入式项目吧！** 🎉
