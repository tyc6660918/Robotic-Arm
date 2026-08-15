# 文档导航索引

本文档提供项目全部文档的结构化导航。

---

## 一、新用户入门路径

按以下顺序依次阅读：

1. **[项目总览](../项目总览与构建系统说明.md)**——了解项目背景与整体架构
2. **[快速上手指南](getting-started/新用户入门指南.md)**——首次使用必读
3. **[调试快速上手](getting-started/调试快速上手.md)**——5 分钟完成硬件连接并启动调试
4. **[开发工作流程](getting-started/开发工作流程.md)**——掌握完整开发循环

---

## 二、详细技术指南

深入学习各专项主题：

### 调试技术类
- **[完整调试技术教程](guides/完整调试技术教程.md)**——系统学习 OpenOCD 与 GDB 调试技术
- **[硬件连接步骤](guides/硬件连接与配置指南.md)**——详细硬件连接规程与故障排查
- **[Claude AI 远程调试](guides/Claude人工智能远程调试指南.md)**——AI 辅助调试技术流程

### 开发流程类
- **[开发工作流](getting-started/开发工作流程.md)**——STM32CubeMX + Visual Studio Code + Git 完整规程

---

## 三、技术参考文档

深入理解系统架构与技术细节：

- **[项目架构说明](technical/architecture.md)**——整体架构、技术选型、坐标系统、串行协议
- **[谐波减速器技术文档](technical/harmonic_reducer/谐波减速器技术参数说明.md)**——谐波减速器设计参数

---

## 四、历史归档文档

历史交接记录，供参考查阅：

- **[交接文档 2026-08-09](archive/handover-2026-08-09.md)**——项目历史交接记录

---

## 五、文档组织结构

```
docs/
├── INDEX.md                        # ← 当前位置
│
├── getting-started/                # 新用户入门区域
│   ├── 新用户入门指南.md          # 快速上手总览
│   ├── 调试快速上手.md           # 调试快速入门（5 分钟）
│   └── 开发工作流程.md            # 开发工作循环
│
├── guides/                         # 详细技术指南
│   ├── 完整调试技术教程.md       # 完整调试规程
│   ├── Claude人工智能远程调试指南.md  # AI 辅助调试
│   └── 硬件连接与配置指南.md      # 硬件连接详细规程
│
├── technical/                      # 技术参考文档
│   ├── architecture.md            # 项目架构
│   └── harmonic_reducer/          # 谐波减速器
│
└── archive/                        # 历史归档
    └── handover-2026-08-09.md     # 交接文档
```

---

## 六、文档贡献规范

### 分类原则

| 目录 | 功能定位 | 目标读者 |
|------|---------|---------|
| `getting-started/` | 快速入门，解决"如何开始"类问题 | 新用户 |
| `guides/` | 专项主题深度学习 | 具备一定基础的开发人员 |
| `technical/` | 技术细节与架构设计 | 需深入理解系统的开发人员 |
| `archive/` | 历史文档，不进行主动维护 | 需查阅历史背景的人员 |

### 命名规范

- 文件名采用中文描述性名称
- 各目录入口文件统一命名为对应中文名称，不再使用 README.md 作为目录入口

### 链接规范

- 一律使用相对路径：`[链接文本](../guides/xxx.md)`
- 禁止使用绝对路径：~~`[链接文本](/docs/xxx.md)`~~

---

## 七、快速检索表

| 需求场景 | 对应文档 |
|---------|---------|
| 首次接触本项目 | [getting-started/新用户入门指南.md](getting-started/新用户入门指南.md) |
| 连接硬件启动调试 | [getting-started/调试快速上手.md](getting-started/调试快速上手.md) |
| 了解完整开发流程 | [getting-started/开发工作流程.md](getting-started/开发工作流程.md) |
| 深入学习调试技术 | [guides/完整调试技术教程.md](guides/完整调试技术教程.md) |
| 解决硬件连接问题 | [guides/硬件连接与配置指南.md](guides/硬件连接与配置指南.md) |
| 启用 AI 辅助调试 | [guides/Claude人工智能远程调试指南.md](guides/Claude人工智能远程调试指南.md) |
| 理解项目整体架构 | [technical/architecture.md](technical/architecture.md) |
| 查阅历史交接文档 | [archive/handover-2026-08-09.md](archive/handover-2026-08-09.md) |
