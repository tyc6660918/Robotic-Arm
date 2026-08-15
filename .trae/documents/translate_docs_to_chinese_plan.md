# 说明文档中文化翻译计划

## 一、项目调研结论

### 1.1 文档整体概况

Robotic-Arm 项目为一个基于开源硬件的主从式手术机器人技能训练平台。项目文档涵盖根目录说明、调试配置（debug/）、官方文档体系（docs/）、资源说明（resources/）、各类机器人子项目（robots/）、工具集（tools/）等多个层级。

经全面扫描，项目中包含大量 `.md` 和 `.txt` 文档，但可分为以下三大类：

| 类别 | 数量估算 | 是否需要翻译 |
|------|---------|------------|
| 项目本身的英文说明文档 | 约 50-60 个文件 | ✅ 需要翻译 |
| 项目本身的中文说明文档 | 约 20-30 个文件 | ❌ 跳过（已是中文） |
| 第三方库/SDK/开发板资料 | 约 200+ 个文件 | ❌ 跳过（保持原文） |

### 1.2 需排除的第三方文档目录

以下目录为第三方库或外部资料，**不在本次翻译范围内**：

- `tools/esp32-iot/firmware/examples/` — Mongoose 网络库的示例 README（约 120+ 个文件）
- `robots/U-Arm/src/simulation/mani_skill/` — ManiSkill 第三方仿真库文档
- `robots/U-Arm/src/uarm/scripts/Follower_Arm/xarm/xArm-Python-SDK/` — xArm 官方 SDK 文档
- `robots/U-Arm/src/uarm/scripts/Follower_Arm/LeRobot/` — LeRobot 第三方库文档
- `docs/野火【STM32F103开发板-霸道】资料/` — 野火开发板配套资料
- `docs/WHEELTEC 直流电机附送资料/` — 轮趣科技电机配套资料
- `resources/references/bbs_backup/` — 备份资料
- `robots/openrst-gripper/OpenRST/00_Claude分析文档/` — 已是中文的分析文档
- `robots/Dummy-Arm/firmware/stm32-control/` 下的 `00-安全第一.md`、`01-傻瓜式操作手册.md`、`接线教程.md` 等 — 已是中文
- 所有 `LICENSE.txt`、`requirements.txt`、`meta.md`、`CODE_OF_CONDUCT.md`、`CONTRIBUTING.md` 等非项目说明性文件
- 所有 CMake 生成的构建产物目录（build/、install/、log/）中的文本文件

### 1.3 文件重命名与翻译映射表

> **命名规范说明**：所有文件名统一采用"中文名称+下划线分隔"格式，扩展名 `.md` 保持不变。
> **GitHub 兼容性说明**：根目录及各子目录下名为 `README.md` 的文件，重命名后 GitHub 将不再将其识别为默认首页。如需要保留该特性，可在翻译完成后在原位置保留一份名为 `README.md` 的空文件或跳转说明文件。

#### 第一组：根目录文档（3 个）

| 原文件名 | 新中文文件名 | 内容说明 |
|---------|------------|---------|
| `README.md` | `项目总览与构建系统说明.md` | 项目主入口文档（含 Root Configuration & Build System 分析报告） |
| `PROJECT_PROGRESS.md` | `项目进度跟踪.md` | 项目进度跟踪文档 |
| `README_SCRIPTS.md` | `脚本使用说明.md` | 脚本使用说明 |

#### 第二组：debug/ 调试配置文档（4 个）

| 原文件名 | 新中文文件名 | 内容说明 |
|---------|------------|---------|
| `debug/README_VSCODE.md` | `debug/VSCode调试配置说明.md` | VSCode 调试配置说明 |
| `debug/README_OPENOCD.md` | `debug/OpenOCD调试说明.md` | OpenOCD 调试说明 |
| `debug/README_AI_DEBUG.md` | `debug/人工智能辅助调试说明.md` | AI 辅助调试说明 |
| `debug/openocd-configs/README.md` | `debug/openocd-configs/配置文件使用说明.md` | OpenOCD 配置文件说明 |

#### 第三组：docs/ 官方文档体系（9 个）

| 原文件名 | 新中文文件名 | 内容说明 |
|---------|------------|---------|
| `docs/README.md` | `docs/文档体系总览.md` | 文档根目录分析报告 |
| `docs/getting-started/README.md` | `docs/getting-started/新用户入门指南.md` | 新用户入门分析报告 |
| `docs/getting-started/debugging.md` | `docs/getting-started/调试快速上手.md` | 调试快速上手（5 分钟入门） |
| `docs/getting-started/workflow.md` | `docs/getting-started/开发工作流程.md` | 完整开发工作流 |
| `docs/guides/README.md` | `docs/guides/详细指南索引.md` | 详细指南目录索引 |
| `docs/guides/debugging-complete.md` | `docs/guides/完整调试技术教程.md` | OpenOCD + GDB 完整调试教程 |
| `docs/guides/claude-debug.md` | `docs/guides/Claude人工智能远程调试指南.md` | Claude AI 远程调试工作流 |
| `docs/guides/hardware-setup.md` | `docs/guides/硬件连接与配置指南.md` | 硬件连接详细步骤与故障排除 |
| `docs/technical/harmonic_reducer/README.md` | `docs/technical/harmonic_reducer/谐波减速器技术参数说明.md` | 谐波减速器设计参数文档 |

注：`docs/INDEX.md`、`docs/technical/architecture.md`、`docs/archive/handover-2026-08-09.md` 已含大量中文内容，需检查后局部润色处理。

#### 第四组：resources/ 资源文档（3 个）

| 原文件名 | 新中文文件名 | 内容说明 |
|---------|------------|---------|
| `resources/README_HARDWARE.md` | `resources/硬件资源说明.md` | 硬件设计资料说明 |
| `resources/README_3D_MODELS.md` | `resources/三维模型资源说明.md` | 3D 模型文件资源说明 |
| `resources/bom/README.md` | `resources/bom/物料清单说明.md` | 物料清单（BOM）目录说明 |

#### 第五组：robots/Dummy-Arm/ 子项目文档（20 个）

| 原文件名 | 新中文文件名 | 内容说明 |
|---------|------------|---------|
| `robots/Dummy-Arm/README_FIRMWARE.md` | `robots/Dummy-Arm/固件系统说明.md` | Dummy 机械臂固件说明 |
| `robots/Dummy-Arm/README_KINEMATICS.md` | `robots/Dummy-Arm/运动学分析说明.md` | 运动学模型与算法说明 |
| `robots/Dummy-Arm/firmware/README.md` | `robots/Dummy-Arm/firmware/固件目录总览.md` | 固件子项目总目录说明 |
| `robots/Dummy-Arm/firmware/dummy-35motor-fw/README.md` | `robots/Dummy-Arm/firmware/dummy-35motor-fw/35系列电机固件说明.md` | 35 电机驱动固件说明 |
| `robots/Dummy-Arm/firmware/dummy-42motor-fw/README.md` | `robots/Dummy-Arm/firmware/dummy-42motor-fw/42系列电机固件说明.md` | 42 电机驱动固件说明 |
| `robots/Dummy-Arm/firmware/stm32-control/README_FIXED.md` | `robots/Dummy-Arm/firmware/stm32-control/控制固件修复说明.md` | STM32 控制固件修复记录 |
| `robots/Dummy-Arm/firmware/stm32-control/FIRMWARE_FIX_REPORT.md` | `robots/Dummy-Arm/firmware/stm32-control/固件修复技术报告.md` | 固件问题修复详细报告 |
| `robots/Dummy-Arm/firmware/stm32-control/CUBEMX_SETUP_GUIDE.md` | `robots/Dummy-Arm/firmware/stm32-control/CubeMX工程配置指南.md` | STM32CubeMX 配置步骤指南 |
| `robots/Dummy-Arm/hardware/motor35/README.md` | `robots/Dummy-Arm/hardware/motor35/35系列电机硬件说明.md` | 35 电机硬件设计文档 |
| `robots/Dummy-Arm/hardware/motor42/README.md` | `robots/Dummy-Arm/hardware/motor42/42系列电机硬件说明.md` | 42 电机硬件设计文档 |
| `robots/Dummy-Arm/hardware/ref-controller/README.md` | `robots/Dummy-Arm/hardware/ref-controller/参考控制器硬件说明.md` | 参考控制器设计说明 |
| `robots/Dummy-Arm/3d-model/README.md` | `robots/Dummy-Arm/3d-model/三维模型说明.md` | 机械臂 3D 模型总览 |
| `robots/Dummy-Arm/3d-model/latest/README.md` | `robots/Dummy-Arm/3d-model/latest/最新版三维模型说明.md` | 最新版本 3D 模型说明 |
| `robots/Dummy-Arm/moveit2_ws/README.md` | `robots/Dummy-Arm/moveit2_ws/MoveIt2工作空间说明.md` | MoveIt2 集成工作区说明 |
| `robots/Dummy-Arm/moveit2_ws/dummy_server/README.md` | `robots/Dummy-Arm/moveit2_ws/dummy_server/控制服务器说明.md` | Dummy Server 模块说明 |
| `robots/Dummy-Arm/moveit2_ws/dummy_server/server/API_DOC.md` | `robots/Dummy-Arm/moveit2_ws/dummy_server/server/应用程序接口文档.md` | REST API 接口参考文档 |
| `robots/Dummy-Arm/moveit2_ws/dummy_server/server/API_STARTUP_GUIDE.md` | `robots/Dummy-Arm/moveit2_ws/dummy_server/server/接口服务启动指南.md` | API 服务启动与配置指南 |
| `robots/Dummy-Arm/moveit2_ws/dummy_server/server/STREAM_API_DOC.md` | `robots/Dummy-Arm/moveit2_ws/dummy_server/server/流式控制接口文档.md` | 流式控制协议 API 文档 |
| `robots/Dummy-Arm/moveit2_ws/dummy_controller/SERVO_STREAMING_GUIDE.md` | `robots/Dummy-Arm/moveit2_ws/dummy_controller/伺服流式控制指南.md` | Servo 流式控制操作指南 |
| `robots/Dummy-Arm/moveit2_ws/dummy_moveit_config/launch/SERVO_STREAMING_GUIDE.md` | `robots/Dummy-Arm/moveit2_ws/dummy_moveit_config/launch/伺服流式启动指南.md` | Servo 流式配置启动指南 |

注：`stm32-control/` 目录下的其余 `.md` 文件（如 `快速开始.md`、`00-安全第一.md`、`接线教程.md` 等）已是中文，跳过翻译与重命名。

#### 第六组：robots/U-Arm/ 子项目文档（5 个）

| 原文件名 | 新中文文件名 | 内容说明 |
|---------|------------|---------|
| `robots/U-Arm/README.md` | `robots/U-Arm/U臂项目总览.md` | U-Arm 主臂项目说明 |
| `robots/U-Arm/README_CONTROL.md` | `robots/U-Arm/控制方案设计说明.md` | 控制系统方案文档 |
| `robots/U-Arm/README_SIMULATION.md` | `robots/U-Arm/仿真方案设计说明.md` | 仿真系统方案文档 |
| `robots/U-Arm/teleoperation_plan.md` | `robots/U-Arm/遥操作实施方案.md` | 主从遥操作技术方案 |
| `robots/U-Arm/CONFIG1_UARM_DUMMY_FLANGE_IMPLEMENTATION.md` | `robots/U-Arm/U臂与Dummy臂法兰接口实现说明.md` | 机械接口连接实现细节 |

注：`robots/U-Arm/README_CN.md` 已是中文，保留原名；`src/simulation/mani_skill/` 与 `xArm-Python-SDK/` 为第三方库目录，跳过。

#### 第七组：robots/openrst-gripper/ 夹爪项目文档（2 个）

| 原文件名 | 新中文文件名 | 内容说明 |
|---------|------------|---------|
| `robots/openrst-gripper/README.md` | `robots/openrst-gripper/OpenRST夹爪项目总览.md` | OpenRST 夹爪子项目说明 |
| `robots/openrst-gripper/OpenRST/README.md` | `robots/openrst-gripper/OpenRST/绳驱器械技术说明.md` | OpenRST 绳驱器械规格说明 |

注：`00_Claude分析文档/` 下的文件均已是中文，跳过。

#### 第八组：tools/ 工具集文档（8 个）

| 原文件名 | 新中文文件名 | 内容说明 |
|---------|------------|---------|
| `tools/README.md` | `tools/工具集总览说明.md` | 工具模块总览（Zone 分析报告） |
| `tools/README_CALIBRATION.md` | `tools/系统标定技术说明.md` | 机械臂标定流程说明 |
| `tools/README_SERIAL_MCP.md` | `tools/串口MCP服务说明.md` | 模型上下文协议串口服务说明 |
| `tools/simple-cli/README.md` | `tools/simple-cli/命令行控制工具说明.md` | 简单命令行工具使用文档 |
| `tools/windows_sim/README.md` | `tools/windows_sim/Windows离线仿真说明.md` | Windows 原生仿真文档（已有大量中文，需检查润色） |
| `tools/esp32-iot/README.md` | `tools/esp32-iot/ESP32物联网工具说明.md` | ESP32 IoT 桥接工具说明 |
| `tools/esp32-iot/firmware/README.md` | `tools/esp32-iot/firmware/ESP32固件构建说明.md` | ESP32 固件构建系统说明 |
| `tools/esp32-iot/firmware/examples/README.md` | `tools/esp32-iot/firmware/examples/固件示例索引.md` | ESP32 示例程序目录索引 |

注：`esp32-iot/firmware/examples/` 下各子目录的 README 为 Mongoose 第三方示例，不翻译不重命名。

### 1.4 汇总统计

| 统计项 | 数值 |
|-------|------|
| 需翻译+重命名的文件总数 | **54 个** |
| 其中需翻译文档（不含 README.md 已是中文） | 约 52 个主要翻译文件 |
| 预计英文字符总量 | 约 20-30 万 |
| 预计中文字符产出量 | 约 30-45 万 |
| 语言风格要求 | **严谨科学技术风格**（规范、客观、精确、非口语化） |

---

## 二、翻译策略与科学严谨风格规范

### 2.1 翻译总原则

1. **信（忠实性）**：技术事实、参数、公式、步骤必须准确无误，严禁意译、增删或曲解原始技术含义
2. **达（规范性）**：使用符合中文科技文献写作标准的表达，严禁口语化、网络化或情感化措辞
3. **雅（严谨性）**：行文逻辑严密、层次清晰、表述客观，采用正式书面语
4. **术语统一**：严格执行 2.3 节术语对照表，同一术语全文统一
5. **格式保真**：Markdown 结构、标识符、路径、代码块保持原样

### 2.2 科学严谨写作强制规范

#### 2.2.1 人称与视角规范

| 禁止表达 | 规范替代 | 说明 |
|---------|---------|------|
| 我们建议 / 我们认为 / 我们使用 | 建议 / 研究表明 / 采用 | 技术文档禁用第一人称复数，保持客观第三人称视角 |
| 你需要 / 你可以 / 请你 | 操作人员应 / 可执行 / 建议实施 | 禁用第二人称，改用施动者身份（操作人员、工程人员、系统） |
| 大家注意 / 兄弟们 / 亲们 | 相关人员应注意 / 工程技术人员须知 | 严禁非正式呼语 |
| 笔者认为 / 本文作者 | 本方案采用 / 该设计规定 | 避免个人化表达，采用方案/设计/系统作为主语 |

#### 2.2.2 语气与措辞规范

| 禁止表达 | 规范替代 | 说明 |
|---------|---------|------|
| 非常重要！ / 切记！ / 小心！ | 该操作对系统安全具有关键意义 / 该参数为强制性要求 | 禁用感叹号与情感化副词，采用陈述式说明后果 |
| 太棒了 / 完美通过 / 完美支持 | 指标满足设计要求 / 功能符合技术规范 / 兼容性验证通过 | 禁用评价性形容词，采用客观验证表述 |
| 搞定了 / 跑通了 / 没问题 | 功能调试完成 / 流程验证通过 / 运行状态正常 | 禁用口语化动词短语，采用工程术语 |
| 很快 / 很慢 / 有点卡 | 响应时间小于 X ms / 帧率约为 X Hz / 存在周期性延迟 | 禁用模糊副词，采用定量描述或具体指标 |
| 等等 / 之类的 / 啥的 | 等组件 / 等外设模块 / 等相关接口 | 禁用非正式列举词 |
| 基本上 / 大概 / 差不多 | 近似为 / 约 / 相对误差小于 X % | 禁用模糊化表述，采用量化或相对误差说明 |

#### 2.2.3 逻辑连接与篇章规范

| 禁止表达 | 规范替代 | 说明 |
|---------|---------|------|
| 然后 / 接着 / 再然后 | 继而 / 随后 / 下一步骤为 / 此后 | 采用正式逻辑连接词，体现操作顺序与因果关系 |
| 因为...所以... | 鉴于...故... / 由于...因此... / 基于上述原因 | 采用书面语因果连词 |
| 但是 / 不过 / 可是 | 然而 / 但需注意 / 尽管如此 | 采用正式转折连词 |
| 还有 / 另外 / 再说 | 此外 / 除此之外 / 进一步而言 | 采用正式递进连词 |
| 总之 / 一句话 / 说白了 | 综上所述 / 综上可知 / 归纳可得 | 采用正式总结用语 |

#### 2.2.4 数量与单位规范

| 禁止表达 | 规范替代 | 说明 |
|---------|---------|------|
| 三个步骤 / 五台电机 / 七根线 | 3 个步骤 / 5 台电机 / 7 根导线 | 技术文档中计数一律采用阿拉伯数字 |
| 大概三毫米 / 差不多五伏 | 约 3 mm / 约 5 V | 数字与单位符号之间保留 1 个半角空格 |
| 频率很高 / 速度很快 / 精度不错 | 时钟频率为 168 MHz / 最大线速度为 0.5 m/s / 重复定位精度 ±0.1 mm | 必须给出定量指标，禁用主观评价 |
| 温度上升了一些 / 电流有点大 | 温升约为 15 ℃ / 电流超出额定值 12 % | 采用具体数值与偏差百分比表述 |
| mm / cm / m / kg | mm（毫米） / cm（厘米） / m（米） / kg（千克） | 首次出现时加注中文单位名称（正文上下文已明确可省略） |

#### 2.2.5 指代与名词规范

| 禁止表达 | 规范替代 | 说明 |
|---------|---------|------|
| 它 / 这个 / 那个 / 这玩意儿 | 该控制器 / 该模块 / 上述固件 / 前述接口 | 严禁模糊代词，必须明确指代对象的技术名称 |
| 东西 / 零件 / 部件 | 构件 / 组件 / 模块 / 单元 / 器件 | 根据技术语境选用准确层级名词 |
| 机器 / 设备 / 玩意儿 | 机械臂系统 / 控制器单元 / 驱动模块 / 伺服机构 | 采用具体技术名词，禁用泛称 |
| 连上去 / 接上去 / 插上去 | 电气连接 / 机械装配 / 线缆插接 / 总线接入 | 采用准确动作术语，区分连接类型 |
| 代码 / 程序 / 脚本 | 固件源代码 / 上位机应用程序 / Python 自动化脚本 | 明确软件类型与运行层级 |

### 2.2.6 标题与小节命名规范

标题必须为名词性短语或陈述式表达，禁止采用口语化疑问或命令式：

| 禁止标题 | 规范标题 |
|---------|---------|
| 怎么开始调试？ | 调试流程启动方法 |
| 快来看！五步搞定！ | 五步调试操作规程 |
| 常见坑和避坑指南 | 常见故障模式与排查对策 |
| 小白也能看懂的教程 | 入门级操作说明（适用于初级工程人员） |
| 搞不懂原理的看这里 | 工作原理解析 |
| 踩过的坑分享 | 工程实践问题与解决方案汇总 |

### 2.3 核心术语对照表（建议稿）

| 英文术语 | 统一中文译名 | 备注 |
|---------|------------|------|
| Robotic Arm | 机械臂 | |
| Surgical Robot | 手术机器人 | |
| Training Platform | 训练平台 | |
| Dummy | Dummy 机械臂 | 保留原名，首次出现加注"稚晖君开源方案" |
| OpenRST | OpenRST 绳驱器械 | 保留原名 |
| U-Arm | U-Arm 主臂 | 保留原名 |
| Firmware | 固件 | |
| Debugger | 调试器 | |
| ST-Link / CMSIS-DAP / WCH-Link | 保留原名 | 硬件调试器品牌 |
| OpenOCD | 保留原名 | 开源片上调试器 |
| GDB | 保留原名 | GNU 调试器 |
| VSCode | Visual Studio Code 编辑器 | 可简称为 VSCode |
| STM32F103 / STM32F405 | 保留原名 | 芯片型号 |
| CubeMX | STM32CubeMX | 全称用于首次出现 |
| MoveIt2 | 保留原名 | ROS2 运动规划框架 |
| ROS2 | 保留原名 | 机器人操作系统 2 |
| URDF | 统一机器人描述格式 | Unified Robot Description Format |
| Forward Kinematics (FK) | 正向运动学 | |
| Inverse Kinematics (IK) | 逆向运动学 | |
| Jacobian | 雅可比矩阵 | |
| Teleoperation | 遥操作 | |
| PID Controller | PID 控制器 | 比例-积分-微分控制器 |
| PWM | 脉冲宽度调制 | Pulse Width Modulation |
| ADC | 模数转换器 | Analog-to-Digital Converter |
| CAN Bus | CAN 总线 | 控制器局域网总线 |
| UART / Serial Port | 串行端口 / 串口 | |
| Harmonic Reducer | 谐波减速器 | |
| Encoder | 编码器 | |
| Joint | 关节 | 机械臂关节 |
| End Effector | 末端执行器 | |
| Digital Twin | 数字孪生 | |
| Control Loop | 控制回路 | |
| Safety State Machine | 安全状态机 | |
| Cartesian | 笛卡尔坐标系 | 亦可简称"直角坐标" |
| Workspace | 工作区 / 工作空间 | ROS 语境用"工作空间"，IDE 语境用"工作区" |
| Build System | 构建系统 | |
| Toolchain | 工具链 | |
| Cross-compilation | 交叉编译 | |

---

## 三、文件名重命名与链接同步更新策略

> **关键原则**：文件名重命名必须配合跨文档链接同步更新，否则所有相对路径链接均将失效。

### 3.1 单文件操作标准流程

每个文件的完整处理顺序必须严格遵循以下 5 步，不得颠倒：

| 步骤 | 操作内容 | 说明 |
|------|---------|------|
| 第 1 步 | 读取原文内容 | 获取英文原文与当前 Markdown 链接结构 |
| 第 2 步 | **翻译正文内容** | 依据 2.2 节科学严谨规范完成中文翻译，保持链接目标（href）暂时不变 |
| 第 3 步 | **更新本文件内部的出站链接** | 依据 1.3 节映射表，将本文件中引用的其他英文文档链接目标（路径部分）同步改为中文文件名 |
| 第 4 步 | 写入翻译内容到**新中文文件名** | 以中文文件名保存（`Write` 操作） |
| 第 5 步 | 删除原英文文件名 | 确认新文件正确后，删除旧文件（避免两份并存造成混淆） |

### 3.2 全局链接更新的双重保障

由于文档 A 可能引用文档 B，而文档 B 可能尚未处理，需采用**两轮更新法**：

- **第一轮（翻译阶段）**：在每个文件的第 3 步，对本文件的出站链接执行批量替换——只要目标文件名出现在 1.3 节映射表中，即改为中文文件名。若引用的目标文件尚未处理，链接将提前指向即将出现的中文文件名。
- **第二轮（收尾阶段）**：全部 54 个文件翻译+重命名完成后，执行全局 Grep 扫描，搜索所有文档中是否仍残留"英文文件名.md"的引用（如 `README.md`、`debugging.md` 等），对遗漏项进行二次修正。

### 3.3 特殊链接类型处理规则

| 链接类型 | 处理规则 |
|---------|---------|
| 相对路径指向 1.3 节中的文件 | 必须更新：路径中文件名部分改为中文（目录名保持英文） |
| 相对路径指向第三方目录文件（mani_skill、野火资料等） | 保持不变：第三方目录不在本次处理范围 |
| 相对路径指向已存在中文文件名（如 `快速开始.md`） | 保持不变：已是正确中文 |
| 绝对 URL 外部链接（https://...） | 保持不变：不受本项目文件名影响 |
| 锚点链接（#section-name） | 保持不变：仅指向文件内部，与文件名无关 |
| 指向非 md 文件（.png、.jpg、.stl、.pdf、.xlsx） | 保持不变：资源文件不重命名 |
| 指向目录本身的路径（如 `../getting-started/`） | 保持不变：目录名不改动，仅文件名改动 |

### 3.4 GitHub 默认首页兼容方案

根目录与各子目录的 `README.md` 重命名后，GitHub 将不再自动展示首页内容。采用以下兼容方案：

翻译与重命名完成后，在以下位置**新建**一份精简版 `README.md`（仅数行），作为自动跳转提示：

```markdown
# 文档说明

本项目说明文档已中文化，请查阅：
- [项目总览与构建系统说明](./项目总览与构建系统说明.md)
```

需要新建该占位文件的目录清单为（共 20 个）：
根目录、debug/openocd-configs/、docs/、docs/getting-started/、docs/guides/、docs/technical/harmonic_reducer/、resources/bom/、robots/Dummy-Arm/firmware/、robots/Dummy-Arm/firmware/dummy-35motor-fw/、robots/Dummy-Arm/firmware/dummy-42motor-fw/、robots/Dummy-Arm/hardware/motor35/、robots/Dummy-Arm/hardware/motor42/、robots/Dummy-Arm/hardware/ref-controller/、robots/Dummy-Arm/3d-model/、robots/Dummy-Arm/3d-model/latest/、robots/Dummy-Arm/moveit2_ws/、robots/Dummy-Arm/moveit2_ws/dummy_server/、robots/openrst-gripper/OpenRST/、tools/simple-cli/、tools/esp32-iot/、tools/esp32-iot/firmware/、tools/esp32-iot/firmware/examples/

---

## 四、执行步骤（含翻译、重命名、链接更新）

> **执行准则**：每个文件必须严格按 3.1 节的 5 步流程操作。

### 阶段一：根目录与 debug 文档（7 个文件）

1. 处理根目录 `README.md` → `项目总览与构建系统说明.md`（翻译+更新出站链接+重命名+删旧）
2. 处理根目录 `PROJECT_PROGRESS.md` → `项目进度跟踪.md`
3. 处理根目录 `README_SCRIPTS.md` → `脚本使用说明.md`
4. 处理 `debug/README_VSCODE.md` → `debug/VSCode调试配置说明.md`
5. 处理 `debug/README_OPENOCD.md` → `debug/OpenOCD调试说明.md`
6. 处理 `debug/README_AI_DEBUG.md` → `debug/人工智能辅助调试说明.md`
7. 处理 `debug/openocd-configs/README.md` → `debug/openocd-configs/配置文件使用说明.md`

### 阶段二：docs/ 官方文档体系（9 个文件）

8. 处理 `docs/README.md` → `docs/文档体系总览.md`
9. 处理 `docs/getting-started/README.md` → `docs/getting-started/新用户入门指南.md`
10. 处理 `docs/getting-started/debugging.md` → `docs/getting-started/调试快速上手.md`
11. 处理 `docs/getting-started/workflow.md` → `docs/getting-started/开发工作流程.md`
12. 处理 `docs/guides/README.md` → `docs/guides/详细指南索引.md`
13. 处理 `docs/guides/debugging-complete.md` → `docs/guides/完整调试技术教程.md`（520 行，重点文件）
14. 处理 `docs/guides/claude-debug.md` → `docs/guides/Claude人工智能远程调试指南.md`
15. 处理 `docs/guides/hardware-setup.md` → `docs/guides/硬件连接与配置指南.md`
16. 处理 `docs/technical/harmonic_reducer/README.md` → `docs/technical/harmonic_reducer/谐波减速器技术参数说明.md`

> 本阶段后需对 `docs/INDEX.md` 进行**内容润色与出站链接更新**（该文件已是中文，但需修正其中指向英文文件名的链接）。

### 阶段三：resources/ 与 Dummy-Arm 文档（3+20=23 个文件）

17. 处理 `resources/README_HARDWARE.md` → `resources/硬件资源说明.md`
18. 处理 `resources/README_3D_MODELS.md` → `resources/三维模型资源说明.md`
19. 处理 `resources/bom/README.md` → `resources/bom/物料清单说明.md`
20. 处理 `robots/Dummy-Arm/README_FIRMWARE.md` → `robots/Dummy-Arm/固件系统说明.md`
21. 处理 `robots/Dummy-Arm/README_KINEMATICS.md` → `robots/Dummy-Arm/运动学分析说明.md`
22. 处理 `robots/Dummy-Arm/firmware/README.md` → `robots/Dummy-Arm/firmware/固件目录总览.md`
23. 处理 `robots/Dummy-Arm/firmware/dummy-35motor-fw/README.md` → `robots/Dummy-Arm/firmware/dummy-35motor-fw/35系列电机固件说明.md`
24. 处理 `robots/Dummy-Arm/firmware/dummy-42motor-fw/README.md` → `robots/Dummy-Arm/firmware/dummy-42motor-fw/42系列电机固件说明.md`
25. 处理 `robots/Dummy-Arm/firmware/stm32-control/README_FIXED.md` → `robots/Dummy-Arm/firmware/stm32-control/控制固件修复说明.md`
26. 处理 `robots/Dummy-Arm/firmware/stm32-control/FIRMWARE_FIX_REPORT.md` → `robots/Dummy-Arm/firmware/stm32-control/固件修复技术报告.md`
27. 处理 `robots/Dummy-Arm/firmware/stm32-control/CUBEMX_SETUP_GUIDE.md` → `robots/Dummy-Arm/firmware/stm32-control/CubeMX工程配置指南.md`
28. 处理 `robots/Dummy-Arm/hardware/motor35/README.md` → `robots/Dummy-Arm/hardware/motor35/35系列电机硬件说明.md`
29. 处理 `robots/Dummy-Arm/hardware/motor42/README.md` → `robots/Dummy-Arm/hardware/motor42/42系列电机硬件说明.md`
30. 处理 `robots/Dummy-Arm/hardware/ref-controller/README.md` → `robots/Dummy-Arm/hardware/ref-controller/参考控制器硬件说明.md`
31. 处理 `robots/Dummy-Arm/3d-model/README.md` → `robots/Dummy-Arm/3d-model/三维模型说明.md`
32. 处理 `robots/Dummy-Arm/3d-model/latest/README.md` → `robots/Dummy-Arm/3d-model/latest/最新版三维模型说明.md`
33. 处理 `robots/Dummy-Arm/moveit2_ws/README.md` → `robots/Dummy-Arm/moveit2_ws/MoveIt2工作空间说明.md`（先润色已有中文，再翻译残留英文）
34. 处理 `robots/Dummy-Arm/moveit2_ws/dummy_server/README.md` → `robots/Dummy-Arm/moveit2_ws/dummy_server/控制服务器说明.md`
35. 处理 `robots/Dummy-Arm/moveit2_ws/dummy_server/server/API_DOC.md` → `robots/Dummy-Arm/moveit2_ws/dummy_server/server/应用程序接口文档.md`
36. 处理 `robots/Dummy-Arm/moveit2_ws/dummy_server/server/API_STARTUP_GUIDE.md` → `robots/Dummy-Arm/moveit2_ws/dummy_server/server/接口服务启动指南.md`
37. 处理 `robots/Dummy-Arm/moveit2_ws/dummy_server/server/STREAM_API_DOC.md` → `robots/Dummy-Arm/moveit2_ws/dummy_server/server/流式控制接口文档.md`
38. 处理 `robots/Dummy-Arm/moveit2_ws/dummy_controller/SERVO_STREAMING_GUIDE.md` → `robots/Dummy-Arm/moveit2_ws/dummy_controller/伺服流式控制指南.md`
39. 处理 `robots/Dummy-Arm/moveit2_ws/dummy_moveit_config/launch/SERVO_STREAMING_GUIDE.md` → `robots/Dummy-Arm/moveit2_ws/dummy_moveit_config/launch/伺服流式启动指南.md`

### 阶段四：U-Arm、openrst-gripper、tools 文档（5+2+8=15 个文件）

40. 处理 `robots/U-Arm/README.md` → `robots/U-Arm/U臂项目总览.md`
41. 处理 `robots/U-Arm/README_CONTROL.md` → `robots/U-Arm/控制方案设计说明.md`
42. 处理 `robots/U-Arm/README_SIMULATION.md` → `robots/U-Arm/仿真方案设计说明.md`
43. 处理 `robots/U-Arm/teleoperation_plan.md` → `robots/U-Arm/遥操作实施方案.md`
44. 处理 `robots/U-Arm/CONFIG1_UARM_DUMMY_FLANGE_IMPLEMENTATION.md` → `robots/U-Arm/U臂与Dummy臂法兰接口实现说明.md`
45. 处理 `robots/openrst-gripper/README.md` → `robots/openrst-gripper/OpenRST夹爪项目总览.md`
46. 处理 `robots/openrst-gripper/OpenRST/README.md` → `robots/openrst-gripper/OpenRST/绳驱器械技术说明.md`
47. 处理 `tools/README.md` → `tools/工具集总览说明.md`
48. 处理 `tools/README_CALIBRATION.md` → `tools/系统标定技术说明.md`
49. 处理 `tools/README_SERIAL_MCP.md` → `tools/串口MCP服务说明.md`
50. 处理 `tools/simple-cli/README.md` → `tools/simple-cli/命令行控制工具说明.md`
51. 处理 `tools/windows_sim/README.md` → `tools/windows_sim/Windows离线仿真说明.md`（润色已有中文，翻译残留英文）
52. 处理 `tools/esp32-iot/README.md` → `tools/esp32-iot/ESP32物联网工具说明.md`
53. 处理 `tools/esp32-iot/firmware/README.md` → `tools/esp32-iot/firmware/ESP32固件构建说明.md`
54. 处理 `tools/esp32-iot/firmware/examples/README.md` → `tools/esp32-iot/firmware/examples/固件示例索引.md`

> 注：第 33 项与第 51 项文件已有大量中文，先按 2.2 节严谨规范润色中文，再补齐英文部分的翻译。

### 阶段五：全局链接二次校正与 GitHub 兼容

55. 执行全局 Grep 扫描：在所有 `.md` 文件中搜索 1.3 节映射表左侧的旧英文文件名，若仍有残留，批量替换为中文文件名
56. 执行特殊链接检查：逐份打开含大量交叉引用的核心文件（INDEX.md、项目总览与构建系统说明.md、文档体系总览.md、工具集总览说明.md），手动抽查 20 条链接有效性
57. 按 3.4 节清单在 20 个目录中创建占位版 `README.md` 跳转提示文件
58. 润色已有中文文档：对 `docs/INDEX.md`、`docs/technical/architecture.md`、`docs/archive/handover-2026-08-09.md`、`robots/Dummy-Arm/firmware/stm32-control/` 下各中文 md、`robots/openrst-gripper/OpenRST/00_Claude分析文档/` 下各中文 md 进行风格审查，将不符合 2.2 节严谨规范的口语化表达（如"兄弟们"、"搞定"、"踩坑"等）统一修正

### 阶段六：质量总验收

59. 格式完整性检查：所有翻译文档的 Markdown 标题、表格、代码块、列表结构与原文一致
60. 术语一致性检查：全局抽取 2.3 节核心术语，确认每个术语的译名全文统一
61. 标识符保真检查：抽样 10 段代码块与命令行，确认路径、命令、变量名未被误译
62. 风格合规性检查：逐份文档抽查 5 段，确认无人称违规、无口语化表达、无误用感叹号

---

## 五、潜在依赖项与注意事项

### 5.1 标识符保留规则（强制执行）

以下内容**必须保持英文原样**，严禁翻译或改写：
- 文件与目录路径：如 `robots/Dummy-Arm/firmware/`
- Shell 命令及参数：如 `cmake --build . -j4`、`ros2 launch dummy_moveit_config demo.launch.py`
- 代码块全部内容（含注释中的标识符、函数名、宏定义）
- 程序标识符：变量名、函数名、类名、结构体名、枚举值、宏定义
- 芯片与器件型号：STM32F103ZET6、STM32F405RG、TB6612FNG、MG310L、CP2102
- 软件产品名：VSCode、OpenOCD、GDB、MoveIt2、ROS2、CubeMX、Keil MDK-ARM
- 标准技术缩写：PID、PWM、ADC、DAC、CAN、UART、USB、I2C、SPI、SWD、SWO、ITM
- 协议字段与命令字：`!START`、`!DISABLE`、`#GETJPOS`、`#SETJPOS`、`SAFE_JOINT_LIMITS_RAD`

### 5.2 中英混合文档处理

对于同时存在中英文内容的文档（`docs/technical/architecture.md`、`tools/windows_sim/README.md`、`robots/Dummy-Arm/moveit2_ws/README.md` 等）：
1. 先审查已有中文内容是否符合 2.2 节严谨规范，不符合则**修正润色**
2. 再将剩余英文部分翻译为中文，确保全文风格与术语统一
3. 不得保留英文片段（除 5.1 节规定需保留的标识符外）

### 5.3 文件格式保真要求

- 行尾换行符保持原 Windows 风格（CRLF）
- Markdown 标题层级保持原样（`#` → `#`、`##` → `##`，不得随意升降级）
- 表格列分隔线 `|---|---|` 保持完整，列宽对齐方式不变
- 代码块语言标记（`bash`、`python`、`json`、`c` 等）原样保留
- 超链接：仅翻译方括号内的显示文本，圆括号内的 URL / 相对路径按 3.3 节规则处理
- 图片引用：`![Alt](path/to/image)` 仅翻译 Alt 描述部分，图片路径保持不变

---

## 六、风险识别与应对措施

| 风险项 | 影响等级 | 应对措施 |
|--------|---------|---------|
| 文件重命名后跨文档链接大面积失效 | 极高 | 严格执行 3.1 节 5 步流程 + 3.2 节两轮更新法；阶段五执行全局 Grep 二次校正 |
| Zone 分析报告类表格结构在翻译中损坏 | 高 | 先复制 Markdown 表格骨架（分隔线、对齐符），再逐单元格填充中文译文；完成后对照原文行数与列数 |
| 核心术语翻译不一致 | 高 | 翻译前熟读 2.3 节术语表；发现新术语即时补充到临时记录；阶段六执行术语全局抽检 |
| 已有中文文档中口语化表达（如"兄弟们""踩坑"）遗漏修正 | 中 | 阶段五第 58 步执行专项润色，建立违禁词清单与替换表 |
| GitHub 仓库浏览体验退化（README.md 重命名后无自动首页） | 中 | 按 3.4 节在 20 个关键目录创建跳转版 README.md 占位文件 |
| `debugging-complete.md` 等长文档分多次翻译造成风格断层 | 低 | 长文档一次性翻译完毕，或分段后保存中间稿；段间统一查阅术语表 |
| 用户后续要求追加第三方文档翻译（Mongoose 示例、mani_skill 文档） | 低 | 本计划范围已明确排除，如用户追加需求则单独扩展计划文件 |

---

## 七、验收标准体系

### 7.1 文件处理完整性验收

| 验收项 | 通过判据 |
|-------|---------|
| 文件翻译覆盖率 | 1.3 节映射表中的 54 个文件全部完成翻译与重命名，零遗漏 |
| 旧文件清理 | 映射表左侧所列英文文件名全部删除，无中英双份并存 |
| 占位文件创建 | 3.4 节列出的 20 个目录均创建跳转提示版 README.md |

### 7.2 译文技术准确性验收

| 验收项 | 通过判据 |
|-------|---------|
| 术语一致性 | 从 2.3 节抽取 20 个核心术语，全局搜索每个术语的所有出现位置，要求译名 100% 统一 |
| 标识符保真 | 随机抽取 10 个代码块或命令行片段，与原文对照确认命令、参数、路径零改动 |
| 数据与参数准确 | 文档中出现的频率、电压、转速、精度、尺寸、时间等数值与原文一一对应，零偏差 |

### 7.3 写作风格合规性验收

| 验收项 | 通过判据 |
|-------|---------|
| 人称合规 | 全文搜索"我们"、"你"、"大家"、"兄弟们"、"亲们"等违禁代词，结果为零命中 |
| 语气合规 | 全文搜索感叹号 `!`（代码块与字符串内除外），要求零命中或仅出现在标注为非译文的原英文片段 |
| 措辞合规 | 抽查 10 份文档各 5 段，无"搞定""跑通""踩坑""坑""小白""牛逼""真香"等口语化表达 |
| 指代合规 | 抽查 5 份文档各 3 段，模糊代词"它""这个""那个"出现频率不超过 1 次/千字 |

### 7.4 链接与格式验收

| 验收项 | 通过判据 |
|-------|---------|
| 内部链接有效性 | 在核心文档（INDEX.md、总览类、指南类 md）中抽查 50 条同项目相对链接，成功率不低于 98% |
| 外部链接保留 | 所有 https://、http:// 开头的外部链接与原文完全一致 |
| 资源链接保留 | 指向 .png/.jpg/.stl/.pdf/.xlsx 的资源链接路径不变 |
| Markdown 结构一致 | 随机抽取 5 份文档的标题层级数、表格数量、代码块数量与原文对应相等 |

