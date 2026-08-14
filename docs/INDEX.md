# 📚 文档索引

本文档提供项目所有文档的导航。

---

## 🚀 新用户入门

从这里开始，按顺序阅读：

1. **[项目总览](../README.md)** - 了解项目是什么
2. **[快速上手指南](getting-started/README.md)** - 第一次使用必读
3. **[调试快速上手](getting-started/debugging.md)** - 5分钟连接硬件开始调试
4. **[开发工作流](getting-started/workflow.md)** - 完整的开发循环

---

## 📖 详细指南

深入学习各个主题：

### 调试相关
- **[完整调试教程](guides/debugging-complete.md)** - 深入学习 OpenOCD + GDB 调试
- **[硬件连接步骤](guides/hardware-setup.md)** - 详细的硬件连接和故障排除
- **[Claude AI 远程调试](guides/claude-debug.md)** - 让 AI 协助你调试

### 开发相关
- **[开发工作流](getting-started/workflow.md)** - CubeMX + VSCode + Git 完整流程

---

## 🏗️ 技术文档

深入了解项目架构和技术细节：

- **[项目架构说明](technical/architecture.md)** - 整体架构、技术选型、坐标系统、串口协议
- **[谐波减速器技术文档](technical/harmonic_reducer/README.md)** - 谐波减速器设计参数

---

## 📦 归档文档

历史交接文档，供参考：

- **[交接文档 2026-08-09](archive/handover-2026-08-09.md)** - 项目历史交接记录

---

## 🗂️ 文档结构

```
docs/
├── INDEX.md                        # ← 你在这里
│
├── getting-started/                # 新用户入门
│   ├── README.md                  # 快速上手总指南
│   ├── debugging.md               # 调试快速上手（5分钟）
│   └── workflow.md                # 开发工作流
│
├── guides/                         # 详细指南
│   ├── debugging-complete.md      # 完整调试教程
│   ├── claude-debug.md            # Claude AI 远程调试
│   └── hardware-setup.md          # 硬件连接详细步骤
│
├── technical/                      # 技术文档
│   ├── architecture.md            # 项目架构
│   └── harmonic_reducer/          # 谐波减速器
│
└── archive/                        # 历史归档
    └── handover-2026-08-09.md     # 交接文档
```

---

## 📝 文档贡献指南

### 文档分类原则

| 目录 | 用途 | 目标读者 |
|------|------|----------|
| `getting-started/` | 快速上手，解决"怎么开始"问题 | 新用户 |
| `guides/` | 深入学习某个主题 | 有一定基础的开发者 |
| `technical/` | 技术细节和架构设计 | 需要深入理解的开发者 |
| `archive/` | 历史文档，不再主动维护 | 需要了解历史的人 |

### 文档命名规范

- 使用小写字母和连字符（kebab-case）
- 描述性名称：`debugging.md` 而非 `doc1.md`
- README.md 作为目录的入口文档

### 链接规范

- 使用相对路径：`[text](../guides/xxx.md)`
- 不要使用绝对路径：~~`[text](/docs/xxx.md)`~~

---

## 🔍 快速查找

| 我想... | 看这个文档 |
|---------|-----------|
| 第一次使用这个项目 | [getting-started/README.md](getting-started/README.md) |
| 连接硬件开始调试 | [getting-started/debugging.md](getting-started/debugging.md) |
| 了解完整开发流程 | [getting-started/workflow.md](getting-started/workflow.md) |
| 深入学习调试技术 | [guides/debugging-complete.md](guides/debugging-complete.md) |
| 解决硬件连接问题 | [guides/hardware-setup.md](guides/hardware-setup.md) |
| 让 Claude 帮我调试 | [guides/claude-debug.md](guides/claude-debug.md) |
| 了解项目整体架构 | [technical/architecture.md](technical/architecture.md) |
| 查看历史交接文档 | [archive/handover-2026-08-09.md](archive/handover-2026-08-09.md) |

---

**找不到你需要的文档？告诉我，我帮你找！** 💬
