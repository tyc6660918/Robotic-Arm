# 📖 STM32 调试环境 - 快速导航

**环境状态:** ✅ 配置完成，等待硬件测试

---

## 🚀 我该从哪里开始？

### 第一次使用？从这里开始 👇

```
📄 QUICK_START_DEBUG.md
   ↓
   5 分钟快速上手
   连接硬件 → 测试 → 开始调试
```

### 需要完整教程？看这里 👇

```
📄 WORKFLOW.md
   ↓
   完整开发工作流
   CubeMX → 编写代码 → 编译 → 调试
```

### 想了解所有功能？这里有详细说明 👇

```
📄 SETUP_COMPLETE.md
   ↓
   完整配置报告
   交付清单 + 功能说明 + 下一步
```

---

## 📂 文档目录树

```
E:\Robotic-Arm\
│
├── 📄 START_HERE.md              ⭐ 你在这里
│
├── 📄 QUICK_START_DEBUG.md       🚀 5 分钟快速上手
├── 📄 WORKFLOW.md                🔄 完整开发工作流
├── 📄 SETUP_COMPLETE.md          ✅ 配置完成报告
│
├── 📁 openocd-configs/           🔧 OpenOCD 配置
│   ├── cmsis-dap-f103.cfg       (野火 DAP)
│   ├── stlink-f103.cfg          (ST-Link)
│   ├── test-connection.sh       (硬件测试脚本)
│   └── README.md
│
├── 📁 .vscode/                   🐛 VSCode 调试配置
│   └── launch.json              (8 个一键调试配置)
│
└── 📁 docs/                      📚 详细文档
    ├── DEBUGGING_GUIDE.md       (完整调试教程 1,500 字)
    ├── CLAUDE_REMOTE_DEBUG.md   (Claude 远程协助指南)
    ├── REMOTE_DEBUG_READY.md    (就绪状态报告)
    ├── DEBUG_SETUP_COMPLETE.md  (配置完成总结)
    └── INDEX.md                 (文档索引)
```

---

## 🎯 常见场景

### 场景 1: 我刚拿到开发板，想开始调试

```bash
# 1. 阅读快速开始（5 分钟）
cat QUICK_START_DEBUG.md

# 2. 连接硬件
#    - DAP 调试器 → USB → PC
#    - DAP → SWD 线 → 开发板 (SWDIO, SWCLK, GND)
#    - 开发板上电

# 3. 测试连接
cd openocd-configs
bash test-connection.sh

# 4. VSCode 按 F5 开始调试
```

### 场景 2: 我想用命令行调试

```bash
# 1. 启动 OpenOCD
openocd -f openocd-configs/cmsis-dap-f103.cfg

# 2. 在另一个终端启动 GDB
cd rst-control-fw/control
arm-none-eabi-gdb build/control.elf
(gdb) target remote :3333
(gdb) load
(gdb) continue
```

### 场景 3: 我遇到问题了

```bash
# 1. 查看故障排查指南
cat WORKFLOW.md  # 看"故障排查清单"部分

# 2. 查看完整调试教程
cat docs/DEBUGGING_GUIDE.md

# 3. 让 Claude 帮忙
"把错误信息给我，我帮你分析"
```

### 场景 4: 我想添加新外设

```bash
# 1. 打开 CubeMX
# 2. 加载 .ioc 文件
# 3. 图形化配置外设
# 4. 生成代码
# 5. 回到 VSCode 编写逻辑
# 6. 按 F5 调试

# 详见: WORKFLOW.md 中的"修改外设配置的流程"
```

---

## 🔗 快速链接

| 我想... | 看这个文档 | 位置 |
|---------|-----------|------|
| 快速上手 | `QUICK_START_DEBUG.md` | 项目根目录 |
| 了解工作流 | `WORKFLOW.md` | 项目根目录 |
| 查看完整报告 | `SETUP_COMPLETE.md` | 项目根目录 |
| 深入学习调试 | `docs/DEBUGGING_GUIDE.md` | docs/ |
| 配置 OpenOCD | `openocd-configs/README.md` | openocd-configs/ |
| 让 Claude 协助 | `docs/CLAUDE_REMOTE_DEBUG.md` | docs/ |
| 查看就绪状态 | `docs/REMOTE_DEBUG_READY.md` | docs/ |

---

## 🛠️ 我有的工具

### 硬件
- ✅ CMSIS-DAP (野火 DAP 小智款)
- ✅ ST-Link V2/V2.1
- ✅ WCH-Link
- 🔄 一键切换调试器

### 软件
- ✅ VSCode 调试配置（8 个）
- ✅ OpenOCD 配置（5 个）
- ✅ GDB 命令模板
- ✅ 硬件测试脚本

### 文档
- ✅ 4,200+ 字文档
- ✅ 7 个文档文件
- ✅ 故障排查清单
- ✅ Claude 远程协助指南

---

## 🤖 Claude 能帮我做什么？

当硬件连接成功后，我可以：

1. **读取寄存器** - 查看 GPIO、定时器、时钟等配置
2. **分析外设** - 诊断为什么外设不工作
3. **监控变量** - 实时查看变量变化
4. **故障诊断** - HardFault 分析、死锁检测
5. **远程指导** - 一步步帮你解决问题

详见: `docs/CLAUDE_REMOTE_DEBUG.md`

---

## ✅ 下一步

### 立即行动
1. **安装 DAP 驱动** (如果还没装)
   ```
   位置: D:\BaiduNetdiskDownload\野火【DAP小智款下载器】
   ```

2. **连接硬件**
   ```
   DAP → USB → PC
   DAP → SWD → 开发板
   开发板上电
   ```

3. **测试连接**
   ```bash
   cd openocd-configs
   bash test-connection.sh
   ```

4. **报告结果给我**
   ```
   "连接成功了" 或 "出现了这个错误: xxx"
   ```

---

## 📞 需要帮助？

- 💬 **有问题随时问我**
- 📋 **把错误信息给我，我帮你分析**
- 🔧 **我可以远程协助你调试硬件**

---

**准备好了就告诉我，我们开始调试！** 🚀
