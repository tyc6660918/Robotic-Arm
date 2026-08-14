# 🚀 新用户快速上手指南

欢迎使用 Robotic-Arm 项目！这是一个低成本主从式机器人平台。

---

## 📖 我该从哪里开始？

### 第一次使用？按这个顺序 👇

1. **了解项目** - 阅读根目录 `README.md`
2. **硬件准备** - 参考 [`hardware-setup.md`](../guides/hardware-setup.md)
3. **快速调试** - 查看 [`debugging.md`](debugging.md)（5分钟上手）
4. **开发工作流** - 阅读 [`workflow.md`](workflow.md)

---

## 🎯 快速场景

### 场景 1: 我刚拿到开发板，想开始调试

```bash
# 1. 连接硬件
#    - DAP 调试器 → USB → PC
#    - DAP → SWD 线 → 开发板 (SWDIO, SWCLK, GND)
#    - 开发板上电

# 2. 测试连接
cd debug/openocd-configs
bash test-connection.sh

# 3. VSCode 按 F5 开始调试
```

### 场景 2: 我想运行仿真

```bash
# Windows 仿真环境（无需硬件）
python tools/windows_sim/run_sim.py

# 运行测试
python -m unittest discover -s tools/windows_sim/tests -v
```

### 场景 3: 我想控制机械臂

```bash
# 命令行控制（需要硬件连接）
python tools/simple-cli/simple-cli.py -l    # 列出端口
python tools/simple-cli/streaming_control.py -p COM5
```

---

## 📂 项目结构速览

```
Robotic-Arm/
├── robots/              # 三大机器人组件
│   ├── dummy-arm/       # Dummy机械从臂（固件、硬件、3D、ROS2）
│   ├── openrst-gripper/ # OpenRST夹取端
│   └── u-arm/           # U-Arm主臂
│
├── tools/               # 开发工具
│   ├── simple-cli/      # 命令行控制
│   ├── robot-viewer/    # 可视化工具
│   ├── windows_sim/     # Windows仿真（★ 推荐先从这里开始）
│   └── esp32-iot/       # ESP32支持
│
├── debug/               # 调试配置
│   ├── openocd-configs/ # OpenOCD配置
│   └── .vscode/         # VSCode调试配置
│
└── docs/                # 文档
    ├── getting-started/ # ← 你在这里
    ├── guides/          # 详细指南
    └── technical/       # 技术文档
```

---

## 🛠️ 所需工具

### 硬件（可选，仿真不需要）
- STM32 开发板（F103ZE / F405RG）
- 调试器：CMSIS-DAP / ST-Link V2 / WCH-Link
- USB 数据线 + SWD 连接线

### 软件
- **Python 3.13+** - 仿真和上位机工具
- **VSCode** - 代码编辑和调试
- **arm-none-eabi-gcc** - 交叉编译工具链（固件开发需要）
- **OpenOCD** - 调试服务器（硬件调试需要）

### 安装 Python 依赖
```bash
pip install numpy scipy matplotlib pyserial
```

---

## 📚 文档导航

| 我想... | 看这个文档 |
|---------|-----------|
| 快速上手调试 | [`debugging.md`](debugging.md) |
| 了解开发工作流 | [`workflow.md`](workflow.md) |
| 深入学习调试 | [`../guides/debugging-complete.md`](../guides/debugging-complete.md) |
| 硬件连接详细步骤 | [`../guides/hardware-setup.md`](../guides/hardware-setup.md) |
| 让 Claude AI 协助 | [`../guides/claude-debug.md`](../guides/claude-debug.md) |
| 了解项目架构 | [`../technical/architecture.md`](../technical/architecture.md) |

---

## 🤖 Claude AI 能帮我做什么？

当硬件连接成功后，Claude 可以：

1. **读取寄存器** - 查看 GPIO、定时器、时钟等配置
2. **分析外设** - 诊断为什么外设不工作
3. **监控变量** - 实时查看变量变化
4. **故障诊断** - HardFault 分析、死锁检测
5. **远程指导** - 一步步帮你解决问题

详见: [`../guides/claude-debug.md`](../guides/claude-debug.md)

---

## ✅ 推荐学习路径

### 路径 1: 仿真开发（无需硬件）
```
1. 阅读本文档 → 
2. 运行 windows_sim 仿真 → 
3. 阅读 docs/technical/simulation.md → 
4. 修改仿真场景参数
```

### 路径 2: 固件开发（需要硬件）
```
1. 阅读本文档 → 
2. 按照 debugging.md 连接硬件 → 
3. VSCode F5 开始调试 → 
4. 阅读 workflow.md 学习完整流程
```

### 路径 3: 上位机开发
```
1. 阅读本文档 → 
2. 运行 simple-cli 工具 → 
3. 阅读 docs/technical/architecture.md → 
4. 开发自己的控制程序
```

---

## 💬 需要帮助？

- 📖 **查看文档** - docs/ 目录下有详细的技术文档
- 🔍 **搜索代码** - 使用 CodeGraph 索引快速查找
- 🤖 **问 Claude** - Claude AI 可以帮你分析代码和调试问题

---

**准备好了就开始吧！** 🚀
