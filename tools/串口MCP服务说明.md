# 模型上下文协议串口服务调研分析

## 1. 区域用途

本区域记录 Robotic-Arm 项目中模型上下文协议（Model Context Protocol，简称 MCP）集成的调研工作。经全面代码库分析后，**未发现 MCP 集成**。项目转而使用 HTTP REST API（FastAPI）、ROS2 通信及串口协议进行机器人控制与集成。

## 2. 关键文件

| 文件路径 | 用途 | 状态 | 备注 |
|-----------|---------|--------|-------|
| `/e/Robotic-Arm/robots/Dummy-Arm/moveit2_ws/dummy_server/server/HTTP接口开发文档.md` | MoveIt2 控制的 HTTP REST API 文档 | 已完成 | 记录用于机器人控制的 FastAPI 端点。HTTP API 服务器（非 MCP）。通过 8000 端口提供 `/api/status`、`/api/pose`、`/api/move_to_pose`、`/api/move_optimal` 端点 |
| `/e/Robotic-Arm/robots/Dummy-Arm/moveit2_ws/dummy_server/server/接口服务启动指南.md` | HTTP API 服务器启动指南 | 已完成 | 记录 FastAPI + uvicorn 服务器启动流程。需要 Python 依赖：fastapi、uvicorn、pydantic、rclpy |
| `/e/Robotic-Arm/tools/windows_sim/sim/urdf_model.py` | URDF 解析器与运动学模型 | 已完成 | 纯 Python URDF 解析器，含 URDFModel、Joint、JointLimit 类。CodeGraph 因方法名标记但与 MCP 无关 |
| `/e/Robotic-Arm/tools/windows_sim/sim/openrst_model.py` | OpenRST 夹持器运动学模型 | 已完成 | 用于工具控制仿真的 IdealOpenRSTModel。与 MCP 无关 |
| `/e/Robotic-Arm/tools/simple-cli/simple-cli.py` | 串口命令行控制工具 | 已完成 | 使用直接串口通信的电机 PID 整定实用程序。无 MCP 集成 |
| `/e/Robotic-Arm/tools/robot-viewer/robot_viewer.py` | 机器人可视化工具 | 已完成 | 基于 Matplotlib 的正向运动学显示工具。无 MCP 集成 |
| `/e/Robotic-Arm/tools/windows_sim/Windows离线仿真说明.md` | Windows 仿真环境文档 | 已完成 | 使用 NumPy/SciPy/Matplotlib 的离线数字孪生系统。纯离线运动学仿真，不依赖 ROS 或 MCP |
| `/e/Robotic-Arm/.claude/settings.json` | Claude Code 工作流配置 | 最小化 | 包含工作流设置（maxConcurrentAgents、agentTimeout）。无 MCP 服务器配置 |

## 3. 当前进度

| 组件 | 状态 | 证据 | 备注 |
|-----------|--------|----------|-------|
| MCP 集成搜索 | 已完成 | 整个代码库范围内的全面 grep、find 与 CodeGraph 分析 | 未发现模型上下文协议实现 |
| 误报分析 | 已完成 | 检查含 "mcp" 模式的方法名 | 确认与 MCP 无关（如 `set_collision_tool_model()`、`MockJointPlant`、解剖学关节命名） |
| HTTP API 服务器分析 | 已完成 | 审查 HTTP接口开发文档.md 与 接口服务启动指南.md | 已记录基于 FastAPI 的机器人控制 REST 服务器 |
| 通信协议审计 | 已完成 | 分析串口、CAN、ROS2 协议 | 项目使用传统嵌入式/机器人协议，而非 MCP |
| 配置文件审查 | 已完成 | 检查 `.claude/settings.json` | 无 MCP 服务器定义或工具配置 |
| MCP 服务器实现 | 未找到 | 全项目搜索无结果 | 无 MCP 服务器代码 |
| MCP 工具定义 | 未找到 | 搜索 MCP 工具模式与处理器 | 无 MCP 工具定义 |
| MCP 客户端集成 | 未找到 | 检查 MCP 客户端库或使用方式 | 无 MCP 客户端代码 |
| MCP 依赖 | 未找到 | 审查 package.json、requirements.txt 等价物 | 任何包文件中均无 MCP 相关依赖 |

## 4. 已完成功能

- 使用多种方法（grep、find、CodeGraph）对代码库进行 MCP 引用的全面搜索
- 误报的分析与分类（方法名、关节命名中的解剖学术语）
- HTTP REST API 服务器实现与文档的完整检查
- 所有工具目录（simple-cli、robot-viewer、windows_sim、esp32-iot）的审查
- 集成模式与架构决策的文档审查
- 在用通信协议（串口 ASCII、CAN 总线、ROS2 主题/服务）的验证
- Claude Code 配置文件中 MCP 服务器定义的检查

## 5. 未完成工作

| 任务 | 优先级 | 阻碍 | 下一步 |
|------|----------|---------|-----------|
| MCP 服务器实现 | N/A | 代码库中未发现实现 | 如需集成，设计 MCP 服务器架构 |
| MCP 工具定义 | N/A | 未发现工具模式或处理器 | 如需，考虑将现有 FastAPI 端点包装为 MCP 工具 |
| MCP 客户端集成 | N/A | 未发现客户端库或使用模式 | 评估 HTTP API 是否可在无 MCP 情况下满足当前需求 |
| dummy_server 实现验证 | 低 | 服务器目录结构存在但分析期间未直接读取 Python 源文件 | 通过检查 dummy_server 目录中的实际 Python 源文件以验证 FastAPI 实现 |

## 6. 使用说明

### 为何不存在 MCP 集成

项目架构显示明确的设计选择，这些选择不需要模型上下文协议：

**嵌入式聚焦**：STM32 固件配合裸机控制环路，以 200Hz（Dummy 臂）和 20kHz（RST 夹持器）运行。这些系统使用直接串口与 CAN 协议。

**仿真聚焦**：纯 Python 离线仿真（`windows_sim`）使用 NumPy/SciPy/Matplotlib 进行运动学验证，无需外部 AI 集成。

**ROS2 集成**：MoveIt2 运动规划工作区使用标准 ROS2 主题、服务与动作进行机器人控制。

**HTTP API**：FastAPI 服务器通过 HTTP REST 端点公开机器人控制，提供适合 Web 应用与外部集成的程序化访问。

### 现有集成点

**HTTP REST API**（FastAPI + uvicorn，端口 8000）：
- `GET /api/status` - 机器人状态与关节位置
- `GET /api/pose` - 当前末端执行器位姿
- `POST /api/move_to_pose` - 笛卡尔运动规划
- `POST /api/move_optimal` - 优化的基于逆运动学的运动

**串口 ASCII 协议**用于直接电机控制：
- 命令：`!START`、`!DISABLE`、`>j1,j2,j3,j4,j5,j6`
- 由 simple-cli.py 与 streaming_control.py 使用

**CAN 总线协议**用于电机通信（30+ 命令 0x01-0x7F）

**ROS2 主题/服务**位于 MoveIt2 工作区中，用于运动规划

### 潜在 MCP 用例（如需要）

1. **大语言模型驱动的机器人控制**：MCP 服务器公开机器人控制工具，用于自然语言命令
2. **知识库访问**：MCP 服务器向 AI 助手提供文档与技术规范
3. **遥测/监控**：MCP 工具用于实时机器人状态查询与诊断信息

然而，当前 HTTP API 已提供适合大多数集成需求的程序化访问，无需 MCP 基础设施。

## 7. 风险与局限

| 风险 | 影响 | 证据 | 缓解措施 |
|------|--------|----------|------------|
| dummy_server 实现未直接验证 | 低 | 服务器目录结构表明存在但分析期间未读取 Python 文件 | 通过检查 `/e/Robotic-Arm/robots/Dummy-Arm/moveit2_ws/dummy_server/` 中的实际 Python 源文件进行验证 |
| FastAPI 服务器维护状态未知 | 低 | API 文档存在但实际运行状态与测试覆盖率未知 | 审查服务器实现，为 HTTP 端点添加自动化测试 |
| HTTP API 端点无自动化测试 | 中 | 未发现 FastAPI 路由的测试文件 | 基于 test client 实现 pytest 的 API 测试 |
| API 文档可能过时 | 低 | 文档存在但与实现的同步未验证 | 对照实际 FastAPI 路由定义交叉引用 HTTP接口开发文档.md |

## 8. 依赖

**HTTP API 服务器（dummy_server）**：
- `fastapi` - 用于构建 API 的现代 Web 框架
- `uvicorn` - 用于生产部署的 ASGI 服务器
- `pydantic` - 数据验证与设置管理
- `rclpy` - 用于 MoveIt2 集成的 ROS2 Python 客户端库

**串口通信工具**：
- `pyserial` - 串口通信（simple-cli、robot-viewer）

**仿真环境（windows_sim）**：
- `numpy` - 运动学的数值计算
- `scipy` - 逆运动学求解器的科学计算（最小二乘优化）
- `matplotlib` - 机器人状态的三维可视化

## 9. 下一步

1. **验证 dummy_server FastAPI 实现** - 读取实际 Python 源文件以确认 API 端点与文档匹配，并评估实现质量（优先级：中）

2. **评估 HTTP API 充分性** - 确定现有 FastAPI REST 端点是否可在无需 MCP 基础设施的情况下满足所有集成需求（优先级：高）

3. **设计 MCP 服务器架构（如需要）** - 若确实需要模型上下文协议集成以实现大语言模型驱动控制或知识库访问，设计公开机器人控制工具的 MCP 服务器（优先级：低 - 仅在确认需求时）

4. **考虑将 FastAPI 端点包装为 MCP 工具** - 若需要 MCP 集成，在现有 HTTP API 周围创建轻量 MCP 工具包装以保持一致性（优先级：低 - 取决于步骤 3）

5. **记录集成架构决策** - 创建架构决策记录（ADR），解释为何在本机器人项目中选择 HTTP REST API 而非 MCP（优先级：低）
