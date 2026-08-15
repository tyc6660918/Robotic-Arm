# 项目架构说明

**文档版本信息：** 本文件提取自 `HANDOVER.md`（2026-08-09 交接文档），用于阐述项目的整体架构与技术选型。

---

## 区域用途

本项目基于开源硬件方案搭建主从式手术机器人技能训练平台，定位为"手术机器人领域的飞行模拟器"。

**设计目标：**
- 硬件总成本控制在 6000 元以上
- 功能对标达芬奇 SimNow、RoSS 等数十万美元级专业模拟器

**系统组成：**
- **从臂**：Dummy 六轴机械臂（稚晖君开源方案复刻）
- **手术前端**：OpenRST 绳驱器械（俯仰 + 上夹 + 下夹，3 DOF）
- **主臂**：U-Arm（方案选型阶段）
- **上位机**：自研控制台软件

---

## 关键文件

### 仿真环境模块（`tools/windows_sim`）

**技术栈：**
```
Python 3.13 + NumPy + SciPy + Matplotlib(TkAgg)
```

| 模块文件 | 功能说明 |
|---------|---------|
| `urdf_model.py` | 严格 URDF 解析器（纯 xml.etree 实现，无 ROS 依赖） |
| `kinematics.py` | 正运动学、逆运动学、Jacobian 矩阵计算 |
| `ik_solver.py` | 有界逆运动学求解器（支持 warm start 与多起点搜索） |
| `teleop_mapper.py` | 主从位姿映射（相对 SE(3)，SO(3) 对数/指数映射） |
| `motion_filter.py` | One Euro 滤波算法 + 运动速率限制 |
| `mock_plant.py` | 关节伺服仿真器 + 故障注入模块 |
| `scenario.py` | 训练场景脚本执行系统 |
| `recorder.py` | 实验数据记录模块（CSV + JSON 格式） |

### 固件模块（`robots/dummy-arm/firmware`）

**技术栈：**
```
STM32F103ZET6, CubeMX + MDK-ARM (ARMCC V5.06)
```

**已实现功能模块：**
- TB6612 电机驱动接口
- 编码器脉冲读取
- ADC 电流采样
- CAN 总线通信接口
- 串口调试控制台

**待实现功能模块：**
- 位置环 / 速度环 PID 控制器
- 电流限幅保护
- 堵转检测与保护
- 独立看门狗（IWDG）

### 上位机工具（`tools/`）

**技术栈：**
```
Python + pyserial + matplotlib
```

| 工具目录 | 功能说明 |
|---------|---------|
| `simple-cli/` | 命令行控制工具 |
| `robot-viewer/` | 机械臂状态可视化工具 |
| `windows_sim/` | 离线仿真环境 |

---

## 当前进展

### 坐标系统约定

**统一坐标系规则：**
- **长度单位**：米（m）
- **角度单位**：弧度（rad）
- **四元数格式**：xyzw 顺序
- **坐标系方向**：右手坐标系

**硬件坐标映射配置（`hardware_mapping.py`）：**
```python
SAFE_JOINT_LIMITS_RAD = {
    'joint1': (-170°, 170°),
    'joint2': (-73°, 90°),
    'joint3': (-55°, 90°),
    ...
}

ROS_TO_HARDWARE_OFFSET_RAD = {...}
ROS_TO_HARDWARE_DIRECTION = {1, -1, ...}
```

### 串口通信协议

#### 从臂通信协议（ASCII 编码）

**运动控制指令集：**
```
!START              # 使能全部电机
!DISABLE            # 失能全部电机
!STOP               # 紧急停止指令
!HOME               # 机械归零指令
>j1,j2,j3,j4,j5,j6,speed  # 关节空间运动指令
@x,y,z,a,b,c,speed        # 笛卡尔空间运动指令
```

**状态查询指令集：**
```
#GETJPOS            # 获取关节当前位置
#GETLPOS            # 获取末端执行器位置
#CMDMODE 1|2|3|4    # 设置控制模式
```

**参数调整指令集：**
```
#SET_DCE_KP <node> <val>
#SET_DCE_KI <node> <val>
#SET_DCE_KD <node> <val>
#REBOOT <node>
```

#### OpenRST 通信协议（设计阶段，未实现）
```
P<0-255>U<0-255>L<0-255>\n  # Pitch + Upper Jaw + Lower Jaw
CALIB / STOP / ENABLE / DISABLE / PING
```

---

## 已完成功能

### 控制流架构（`windows_sim` 仿真环境）

```
虚拟主手输入 (GUI / 场景脚本)
   ↓
MasterState {timestamp, pose, grasp, deadman, clutch}
   ↓
TeleopSafetyStateMachine（遥操作安全状态机）
   ↓ (Clutch 触发 → 重新捕获参考位姿)
OneEuroPoseFilter（震颤抑制滤波器）
   ↓
TeleopMapper（主从相对 SE(3) 映射）
   ↓
PoseRateLimiter（速度/加速度限幅器）
   ↓
BoundedIKSolver（有界逆运动学求解器，warm start，15 次迭代）
   ↓
MockJointPlant（加加速度受限关节伺服模型）
   ↓
IdealOpenRSTModel（理想 pitch/yaw/grasp 执行模型）
   ↓
SimulationRecorder → CSV + JSON 数据记录
```

**关键设计特征：**
- Clutch 释放后，在当前主从位姿状态下重新捕获参考位姿
- 逆运动学求解失败时，保持上一安全目标位姿，进入 HOLD 状态
- 故障清除后，必须执行 rearm 操作方可恢复正常运行

### 数据流架构

#### URDF 依赖（只读）
```
Moveit_ws-main/dummy-ros2_description/urdf/dummy.urdf
OpenRST-main/URDF/openrst_description/urdf/openrst.urdf
```
系统仅读取关节几何信息，不加载网格模型（mesh）。

#### 串口契约层
```
simple-cli/ → firmware/dummy-ref-core-fw/.../ascii_protocol.cpp
robot-viewer/ → 同上
```

#### 系统特性
- 无数据库依赖
- 无 Web 后端服务
- 无 REST API 接口
- 纯本地文件 I/O（CSV + JSON）

### 仿真环境验证结果

#### 运动学测试（200 样本）
```
求解成功率 = 1.0
最大位置误差 = 32 μm    (< 0.1 mm，符合要求)
最大姿态误差 = 0.0006° (< 0.05°，符合要求)
求解时间中位数 = 13.9 ms
求解时间 P99 = 171.6 ms （冷启动场景）
```

#### 震颤抑制测试（tremor 场景）
```
有意运动幅度损失 = 4.71%  (< 5%，符合要求)
震颤滤波衰减量 = 16.04 dB  (> 15 dB，符合要求)
实际震颤衰减量 = 53.44 dB
```

#### 故障注入测试（13 类故障 + 恢复流程）
```
逆运动学求解成功率 = 0.9991
状态转移序列：READY → TELEOP → HOLD → FAULT → TELEOP
故障覆盖率：10 / 10 类故障全部覆盖
关节限位违反次数 = 0
```

#### 实时性能测试（10 秒墙钟测试）
```
控制周期中位数 = 10.02 ms
控制周期 P99 = 10.41 ms
截止期错失次数 = 1
控制周期 P99 低于 20 ms = True
```

### 项目里程碑状态

| 里程碑编号 | 里程碑名称 | 状态 | 说明 |
|-----------|----------|------|------|
| M1 | Dummy 硬件复刻 | 已完成 | 硬件文件、BOM 清单、3D 打印文件齐全 |
| M2 | RST 方案选型 | 已完成 | 选定 OpenRST 开源方案 |
| M3 | RST 固件开发 | 约 25% 完成 | 仅完成板级 bring-up，控制环未实现 |
| M4 | RST 机械组装 | 待启动 | 无实施证据 |
| M5 | Dummy+RST 集成 | 待启动 | 无实施证据 |
| M6 | 主从遥操作 | 仿真完成 | `windows_sim` 已实现，硬件集成待完成 |
| M7 | 训练平台化 | 待启动 | 无训练任务与评估算法 |

---

## 未完成工作

### 已知问题清单

#### P0 级：安全相关问题

| 编号 | 问题描述 | 影响位置 |
|-----|---------|---------|
| B1 | `robot-viewer/robot_viewer.py` 连接时发送 `!START` 使能电机，退出时未发送 `!DISABLE` | `robot-viewer/` |
| B2 | `rst-control-fw/Core/Src/debug_console.c` 中 ISR 内调用 `HAL_Delay()` 导致系统死锁 | 固件调试控制台 |
| B3 | 固件无电流限幅机制（ADC 采样未启动） | 固件安全层 |
| B4 | 固件无通信超时保护 / 无看门狗机制 | 固件安全层 |
| B5 | `Error_Handler` 异常处理函数未关闭 PWM 输出 | 固件异常处理 |
| B6 | 调试控制台裸回车会重复执行上一条命令 | 固件调试控制台 |

#### P1 级：功能正确性问题

| 编号 | 问题描述 | 影响位置 |
|-----|---------|---------|
| B7 | ADC Rank3 配置错误，PA5 通道无法采样 | 固件 ADC 模块 |
| B8 | CAN 实际波特率为 562.5 kbps，与设计值 1 Mbps 不符 | 固件 CAN 模块 |
| B9 | TIM2 编码器引脚与 WK_UP 按键存在资源冲突 | 固件定时器配置 |
| B10 | 编码器 16 位计数器按 32 位读取，反转时出现异常 | 固件编码器模块 |
| B11-B14 | 上位机工具存在若干缺陷 | `tools/` |

#### P2 级：结构性隐患

| 编号 | 问题描述 | 影响位置 |
|-----|---------|---------|
| B15 | 关节限位数据存在三套独立定义，缺乏单一真源 | 全系统 |
| B16 | GPIO 手写配置在 CubeMX 重新生成代码时会被清除 | 固件 GPIO 模块 |
| B17 | PWM 频率为 1 kHz（处于可听频段，会产生啸叫） | 固件 PWM 模块 |
| B18 | 引脚配置文档与实际代码不一致 | 文档与代码 |

### 架构级不一致

#### OpenRST 自由度语义冲突

| 模块 | 自由度定义 |
|------|-----------|
| `windows_sim` | pitch + **yaw** + grasp（对称双爪模型） |
| RST 硬件设计 | pitch + **上夹** + **下夹**（独立双夹模型） |
| OpenRST URDF | pitch + finger_left + finger_right |

**影响**：仿真环境中验证的 OpenRST 控制逻辑无法直接迁移至硬件平台。

---

## 使用说明

（本章节内容原文档未提供，待补充）

---

## 风险与局限

### 基础设施缺失项

| 基础设施 | 状态 | 说明 |
|---------|------|------|
| `requirements.txt` / `pyproject.toml` | 缺失 | Python 依赖未统一管理 |
| 根目录 `.gitignore` | 缺失 | 已在重组分支中添加 |
| CI/CD 流水线 | 缺失 | 无自动化构建与测试 |
| `.vscode/settings.json` | 配置错误 | 仅含一行配置，指向错误的 CMake 路径 |

---

## 依赖关系

### Python 依赖（需补充 `requirements.txt`）
```
numpy==2.4.3
scipy==1.17.1
matplotlib==3.10.8
pyserial==3.x
```

### 固件工具链依赖
```
arm-none-eabi-gcc 10.3
OpenOCD 0.11+
GDB multiarch
STM32CubeMX
```

### Vendored 上游代码（禁止直接修改）
```
Moveit_ws-main/   # ROS2 + MoveIt2 完整工作空间
OpenRST-main/     # OpenRST 学术开源项目
firmware/dummy-*  # Dummy 原版固件
esp32-iot/        # Mongoose 示例集合
```

---

## 后续建议

### 阶段 A：工程基线建立（预计 1-2 天）
- [x] 初始化 git 仓库 + 添加 `.gitignore`（已完成）
- [ ] 编写 `requirements.txt`
- [ ] 更新技术文档体系
- [ ] 清理并删除死代码

### 阶段 B：安全加固（预计 2-3 天）
- [ ] 修复 `robot_viewer` 的 `!START` 使能问题
- [ ] 修复固件死锁问题与 `Error_Handler` 异常处理
- [ ] 统一关节限位数据真源

### 阶段 C：RST 固件功能补齐（预计 2-3 周）
- [ ] 核实实物接线方案
- [ ] 修复 `.ioc` 配置错误
- [ ] 实现电流限幅机制
- [ ] 实现 PID 闭环控制
- [ ] 实现堵转找零标定
- [ ] 实现串口通信协议

### 阶段 D-G：机械集成 → 主从遥操作 → 训练平台化
详细内容请参阅原 `HANDOVER.md` 第 8 节。

---

## 参考文档

- 完整交接文档：[`../archive/handover-2026-08-09.md`](../archive/handover-2026-08-09.md)
- 项目总体设计：`项目完整技术文档.txt`（位于项目根目录）
- RST 控制设计：`RST夹取端控制设计方案.txt`（位于项目根目录）

---

**文档说明：** 本文件提取自历史交接文档，部分内容可能已过时。文档更新日期：2026-08-09。
