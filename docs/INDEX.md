# 📚 STM32 调试环境 - 文档索引

**快速找到你需要的文档**

---

## 🚀 我该看哪个文档？

### 👉 刚开始，想快速上手
**阅读：** `QUICK_START_DEBUG.md` (本目录)
- ⏱️ 5 分钟快速启动
- 3 步开始调试
- 常见问题快速解决

### 👉 想了解完整的调试功能
**阅读：** `docs/DEBUGGING_GUIDE.md`
- 📖 658 行完整教程
- 硬件连接详解
- VSCode / 命令行 / 烧录三种方法
- 高级功能（断点、监视点、ITM 跟踪）
- 故障排除指南
- 调试技巧和命令参考

### 👉 遇到问题，想让 Claude 帮忙
**阅读：** `docs/CLAUDE_REMOTE_DEBUG.md`
- 📖 498 行协作指南
- 工作原理说明
- 诊断命令模板（复制粘贴即用）
- 4 个完整示例场景
- 示例对话（看看如何与 Claude 协作）

### 👉 需要配置 OpenOCD 或更换调试器
**阅读：** `openocd-configs/README.md`
- 📖 286 行配置说明
- 4 种调试器配置文件说明
- 如何修改 SWD 速度
- 如何添加自定义烧录函数
- 故障排除（6 个常见问题）

### 👉 想知道这次配置都做了什么
**阅读：** `docs/DEBUG_SETUP_COMPLETE.md`
- 📖 完成报告
- 已交付的内容清单
- 核心功能介绍
- 验证结果
- 文件结构
- 下一步建议

---

## 📂 文档结构

```
E:\Robotic-Arm\
│
├── QUICK_START_DEBUG.md          ← 🎯 从这里开始！(5分钟)
│
├── openocd-configs/
│   ├── stlink-f103.cfg           ← OpenOCD 配置文件
│   ├── cmsis-dap-f103.cfg
│   ├── wch-link-f103.cfg
│   ├── stlink-f405.cfg
│   ├── test-connection.sh        ← 测试脚本
│   └── README.md                 ← OpenOCD 配置说明 (286行)
│
├── docs/
│   ├── DEBUGGING_GUIDE.md        ← 📚 完整调试教程 (658行)
│   ├── CLAUDE_REMOTE_DEBUG.md    ← 🤝 Claude 协作指南 (498行)
│   └── DEBUG_SETUP_COMPLETE.md   ← ✅ 配置完成报告
│
├── .vscode/
│   ├── launch.json               ← 8个调试配置
│   ├── tasks.json                ← 10个编译/烧录任务
│   ├── settings.json             ← 工具链路径
│   └── extensions.json           ← 推荐扩展
│
└── cubemx-validation-test/
    ├── VSCODE_SETUP_GUIDE.md     ← VSCode 完整设置 (417行)
    └── VALIDATION_REPORT.md      ← 验证测试报告
```

---

## 🔍 按主题查找

### 硬件连接
- `QUICK_START_DEBUG.md` → 第 1 步
- `docs/DEBUGGING_GUIDE.md` → "硬件准备" 章节

### OpenOCD 配置
- `openocd-configs/README.md` → 完整说明
- `docs/DEBUGGING_GUIDE.md` → "软件准备" 章节

### VSCode 调试
- `QUICK_START_DEBUG.md` → 第 3 步
- `docs/DEBUGGING_GUIDE.md` → "方法 1: VSCode 图形化调试"
- `.vscode/launch.json` → 具体配置

### 命令行调试
- `docs/DEBUGGING_GUIDE.md` → "方法 2: 命令行调试"
- `docs/CLAUDE_REMOTE_DEBUG.md` → 调试命令模板

### 故障排除
- `QUICK_START_DEBUG.md` → 常见问题
- `openocd-configs/README.md` → "故障排除" 章节
- `docs/DEBUGGING_GUIDE.md` → "故障排除" 章节

### 与 Claude 协作
- `docs/CLAUDE_REMOTE_DEBUG.md` → 完整指南
- 包含诊断命令、使用场景、示例对话

### 高级功能
- `docs/DEBUGGING_GUIDE.md` → "高级功能" 章节
  - 条件断点
  - 监视点
  - ITM 跟踪输出
  - 寄存器/内存查看

### 调试技巧
- `docs/DEBUGGING_GUIDE.md` → "调试技巧" 章节
  - HardFault 分析
  - GPIO 状态查看
  - 强制修改变量
  - 反汇编查看

---

## 🎯 按使用场景查找

### 场景 1: 第一次使用
**步骤:**
1. 📖 阅读 `QUICK_START_DEBUG.md`
2. 🔌 连接硬件
3. 🧪 运行 `test-connection.sh`
4. 🐛 在 VSCode 中按 `F5` 开始调试

### 场景 2: 程序不工作，不知道为什么
**步骤:**
1. 📖 阅读 `docs/CLAUDE_REMOTE_DEBUG.md` → "基础信息收集"
2. 🔧 运行诊断命令
3. 📋 把输出发给 Claude
4. ✅ 按照 Claude 的建议修复

### 场景 3: HardFault 崩溃
**步骤:**
1. 📖 阅读 `docs/DEBUGGING_GUIDE.md` → "技巧 1: 查找 HardFault 原因"
2. 或阅读 `docs/CLAUDE_REMOTE_DEBUG.md` → "HardFault 分析"
3. 🔧 运行 HardFault 诊断命令
4. 📋 把输出发给 Claude

### 场景 4: 外设不工作（USART/SPI/DMA/GPIO）
**步骤:**
1. 📖 阅读 `docs/CLAUDE_REMOTE_DEBUG.md` → 找到对应外设的检查命令
2. 🔧 运行外设状态检查命令
3. 📋 把输出发给 Claude
4. ✅ Claude 会告诉你哪个寄存器错了，如何修复

### 场景 5: 更换调试器
**步骤:**
1. 📖 阅读 `openocd-configs/README.md` → "配置文件列表"
2. 🔧 选择对应的配置文件
3. ⚙️ 修改 `.vscode/launch.json` 中的 `configFiles`
4. 🧪 运行 `test-connection.sh` 验证

### 场景 6: 需要自定义 OpenOCD 配置
**步骤:**
1. 📖 阅读 `openocd-configs/README.md` → "自定义配置"
2. ✏️ 修改对应的 `.cfg` 文件
3. 🧪 测试连接

---

## 📊 文档统计

| 文档 | 行数 | 主题 |
|------|------|------|
| `QUICK_START_DEBUG.md` | 130 | 快速启动 |
| `docs/DEBUGGING_GUIDE.md` | 658 | 完整调试教程 |
| `docs/CLAUDE_REMOTE_DEBUG.md` | 498 | Claude 协作 |
| `docs/DEBUG_SETUP_COMPLETE.md` | 352 | 配置完成报告 |
| `openocd-configs/README.md` | 286 | OpenOCD 配置 |
| `cubemx-validation-test/VSCODE_SETUP_GUIDE.md` | 417 | VSCode 设置 |
| **总计** | **2,341** | **6 份文档** |

---

## ❓ 常见问题快速跳转

| 问题 | 文档位置 |
|------|---------|
| 如何连接硬件？ | `QUICK_START_DEBUG.md` → 第 1 步 |
| 如何测试连接？ | `QUICK_START_DEBUG.md` → 第 2 步 |
| 如何在 VSCode 中调试？ | `QUICK_START_DEBUG.md` → 第 3 步 |
| OpenOCD 无法连接调试器 | `openocd-configs/README.md` → 问题 1 |
| OpenOCD 无法连接芯片 | `openocd-configs/README.md` → 问题 2 |
| 如何分析 HardFault？ | `docs/DEBUGGING_GUIDE.md` → 技巧 1 |
| 如何让 Claude 帮忙？ | `docs/CLAUDE_REMOTE_DEBUG.md` → 快速设置 |
| USART 不工作 | `docs/CLAUDE_REMOTE_DEBUG.md` → 场景 2 |
| DMA 不工作 | `docs/CLAUDE_REMOTE_DEBUG.md` → 场景 3 |
| GPIO 状态如何查看？ | `docs/DEBUGGING_GUIDE.md` → 技巧 2 |
| 如何修改变量值？ | `docs/DEBUGGING_GUIDE.md` → 技巧 3 |
| GDB 常用命令 | `docs/DEBUGGING_GUIDE.md` → 参考资料 |
| VSCode 快捷键 | `docs/DEBUGGING_GUIDE.md` → 参考资料 |

---

## 🎓 学习路径

### 初级（1-2 小时）
1. ✅ 阅读 `QUICK_START_DEBUG.md`
2. ✅ 成功连接硬件并测试
3. ✅ 在 VSCode 中成功调试一次
4. ✅ 学会设置断点、单步执行、查看变量

### 中级（3-5 小时）
1. ✅ 阅读 `docs/DEBUGGING_GUIDE.md` 完整教程
2. ✅ 学会命令行 GDB 调试
3. ✅ 学会查看外设寄存器
4. ✅ 学会分析简单的 HardFault
5. ✅ 阅读 `docs/CLAUDE_REMOTE_DEBUG.md`
6. ✅ 尝试让 Claude 帮助排查一个问题

### 高级（5-10 小时）
1. ✅ 掌握所有 GDB 命令
2. ✅ 能够独立分析复杂的 HardFault
3. ✅ 能够配置 ITM 跟踪输出
4. ✅ 能够自定义 OpenOCD 配置
5. ✅ 能够编写 GDB 自动化脚本
6. ✅ 能够远程调试（网络 GDB）

---

## 💡 提示

### 高效使用这些文档

1. **不要一次性全读** - 根据需要查找
2. **使用 Ctrl+F 搜索** - 快速定位关键词
3. **收藏常用章节** - 比如故障排除部分
4. **实践中学习** - 边调试边查文档

### 遇到问题时

1. **先查文档** - 90% 的问题文档里都有答案
2. **再跑诊断** - 运行 GDB 诊断命令
3. **最后问 Claude** - 把诊断结果发给我

### 与 Claude 协作的最佳实践

1. **提供完整输出** - 不要省略任何信息
2. **说明你的目标** - "我想让 LED 闪烁" 而不是 "GPIO 不工作"
3. **说明已尝试的方法** - 避免重复建议
4. **一次性发送所有诊断结果** - 让 Claude 一次看全

---

## 🔗 相关资源

### 项目文档
- `README.md` (项目根目录) - 项目概述
- `rst-control-fw/README_FIXED.md` - 固件说明
- `cubemx-validation-test/INDEX.md` - 测试文档索引

### 外部资源
- [OpenOCD 官方文档](http://openocd.org/doc/html/index.html)
- [GDB 官方文档](https://sourceware.org/gdb/documentation/)
- [ARM Cortex-M 技术参考手册](https://developer.arm.com/documentation/)
- [STM32F1 参考手册](https://www.st.com/resource/en/reference_manual/cd00171190.pdf)

---

**最后更新:** 2026-08-10  
**维护者:** Claude

**有新问题？** 在这个索引里找不到？告诉我，我会补充文档！
