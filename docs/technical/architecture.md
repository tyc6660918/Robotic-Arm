# 项目架构说明

本文档从 HANDOVER.md（2026-08-09 交接文档）提取，说明项目的整体架构和技术选型。

---

## 项目概述

### 用途
基于开源硬件搭建主从式手术机器人技能训练平台（"手术机器人领域的飞行模拟器"）。

**目标:**
- 成本 < 6000 元
- 对标达芬奇 SimNow / RoSS 等数十万美元级模拟器

### 系统组成
- **从臂**: Dummy 六轴机械臂（稚晖君开源方案复刻）
- **手术前端**: OpenRST 绳驱器械（俯仰 + 上夹 + 下夹，3 DOF）
- **主臂**: U-Arm（方案选型中）
- **上位机**: 自研控制台

---

## 技术栈

### 仿真环境（tools/windows_sim）
```
Python 3.13 + NumPy + SciPy + Matplotlib(TkAgg)
```

**核心模块:**
- `urdf_model.py` - 严格 URDF 解析器（纯 xml.etree，不依赖 ROS）
- `kinematics.py` - 正/逆运动学、Jacobian
- `ik_solver.py` - 有界 IK 求解器（warm start + 多起点）
- `teleop_mapper.py` - 主从映射（相对 SE(3)，SO(3) log/exp）
- `motion_filter.py` - One Euro 滤波 + 速率限制
- `mock_plant.py` - 关节伺服仿真 + 故障注入
- `scenario.py` - 场景脚本系统
- `recorder.py` - 数据记录（CSV + JSON）

### 固件（robots/dummy-arm/firmware）
```
STM32F103ZET6, CubeMX + MDK-ARM (ARMCC V5.06)
```

**已实现:**
- TB6612 电机驱动
- 编码器读取
- ADC 电流采样
- CAN 总线通信
- 串口调试控制台

**待实现:**
- 位置/速度环 PID
- 电流限幅
- 堵转保护
- 看门狗

### 上位机工具（tools/）
```
Python + pyserial + matplotlib
```

**工具清单:**
- `simple-cli/` - 命令行控制
- `robot-viewer/` - 可视化（⚠️ 有安全隐患，连接时会使能电机）
- `windows_sim/` - 离线仿真（推荐）

---

## 坐标系统

### 统一约定
- **长度单位**: 米（m）
- **角度单位**: 弧度（rad）
- **四元数**: xyzw 顺序
- **坐标系**: 右手坐标系

### 硬件坐标映射
```python
# hardware_mapping.py
SAFE_JOINT_LIMITS_RAD = {
    'joint1': (-170°, 170°),
    'joint2': (-73°, 90°),
    'joint3': (-55°, 90°),
    ...
}

ROS_TO_HARDWARE_OFFSET_RAD = {...}
ROS_TO_HARDWARE_DIRECTION = {1, -1, ...}
```

---

## 串口协议

### Dummy 从臂协议（ASCII）

**运动控制:**
```
!START              # 使能所有电机
!DISABLE            # 失能所有电机
!STOP               # 急停
!HOME               # 归零
>j1,j2,j3,j4,j5,j6,speed  # 关节空间运动
@x,y,z,a,b,c,speed        # 笛卡尔空间运动
```

**状态查询:**
```
#GETJPOS            # 获取关节位置
#GETLPOS            # 获取末端位置
#CMDMODE 1|2|3|4    # 设置控制模式
```

**参数调整:**
```
#SET_DCE_KP <node> <val>
#SET_DCE_KI <node> <val>
#SET_DCE_KD <node> <val>
#REBOOT <node>
```

### OpenRST 协议（设计中，未实现）
```
P<0-255>U<0-255>L<0-255>\n  # Pitch + Upper + Lower
CALIB / STOP / ENABLE / DISABLE / PING
```

---

## 控制流（windows_sim）

```
虚拟主手 (GUI / 场景脚本)
   ↓
MasterState {timestamp, pose, grasp, deadman, clutch}
   ↓
TeleopSafetyStateMachine
   ↓ (Clutch? → 重新捕获参考)
OneEuroPoseFilter (震颤抑制)
   ↓
TeleopMapper (相对 SE(3) 映射)
   ↓
PoseRateLimiter (速度/加速度限幅)
   ↓
BoundedIKSolver (warm start, 15 iterations)
   ↓
MockJointPlant (jerk 受限伺服)
   ↓
IdealOpenRSTModel (理想 pitch/yaw/grasp)
   ↓
SimulationRecorder → CSV + JSON
```

**关键设计:**
- Clutch 释放后在**当前主从位姿重新捕获**参考
- IK 失败 → 保持上一安全目标 → 进 HOLD 状态
- 故障清除后必须**重新 rearm** 才能恢复

---

## 数据流

### URDF 依赖（只读）
```
Moveit_ws-main/dummy-ros2_description/urdf/dummy.urdf
OpenRST-main/URDF/openrst_description/urdf/openrst.urdf
```

⚠️ 只读取 joint 几何，不加载 mesh

### 串口契约
```
simple-cli/ → firmware/dummy-ref-core-fw/.../ascii_protocol.cpp
robot-viewer/ → 同上
```

### 无网络依赖
- 无数据库
- 无 Web 后端
- 无 REST API
- 纯本地文件 I/O（CSV + JSON）

---

## 项目完成度

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| M1 Dummy 硬件复刻 | ✅ 已完成 | 硬件文件、BOM、3D 打印文件齐全 |
| M2 RST 方案选型 | ✅ 已完成 | OpenRST 开源方案 |
| M3 RST 固件开发 | 🟡 约 25% | 仅板级 bring-up，无控制环 |
| M4 RST 机械组装 | ⏸️ 待开始 | 无证据 |
| M5 Dummy+RST 集成 | ⏸️ 待开始 | 无证据 |
| M6 主从遥操作 | 🟡 仿真完成 | windows_sim 已实现，硬件未集成 |
| M7 训练平台化 | ⏸️ 待开始 | 无训练任务/评估算法 |

---

## 已验证功能（windows_sim）

### 运动学验收（200 样本）
```
success_rate = 1.0
maximum_position_error = 32 μm    (<0.1mm ✓)
maximum_orientation_error = 0.0006° (<0.05° ✓)
solve_time_p50 = 13.9 ms
solve_time_p99 = 171.6 ms  (冷启动)
```

### 震颤抑制（tremor 场景）
```
intentional_amplitude_loss = 4.71%  (<5% ✓)
tremor_filter_attenuation = 16.04 dB  (>15dB ✓)
actual_tremor_attenuation = 53.44 dB
```

### 故障注入（13 类故障 + 恢复）
```
ik_success_rate = 0.9991
state_transitions: READY → TELEOP → HOLD → FAULT → TELEOP
fault_coverage: 10 / 10 类故障全覆盖
joint_limit_violation = 0
```

### 实时性（10 秒墙钟测试）
```
cycle_period_p50 = 10.02 ms
cycle_period_p99 = 10.41 ms
deadline_miss_count = 1
control_cycle_p99_under_20ms = True
```

---

## 已知问题（从 HANDOVER.md 提取）

### 🔴 P0 - 安全相关

**B1:** `robot-viewer/robot_viewer.py` 连接时发 `!START` 使能电机，退出不发 `!DISABLE`

**B2:** `rst-control-fw/Core/Src/debug_console.c` ISR 内调用 `HAL_Delay()` 导致死锁

**B3:** 固件无电流限幅（ADC 未启动）

**B4:** 固件无超时保护 / 无看门狗

**B5:** `Error_Handler` 不关闭 PWM

**B6:** 调试控制台回车会重复执行上一条命令

### 🟠 P1 - 功能正确性

**B7:** ADC Rank3 配置错误，PA5 采样不到

**B8:** CAN 实际波特率 562.5 kbps，不是设计的 1 Mbps

**B9:** TIM2 编码器引脚与 WK_UP 按键冲突

**B10:** 编码器 16 位计数器当 32 位读，反转时出错

**B11-B14:** 上位机工具的各种小 bug

### 🟡 P2 - 结构性隐患

**B15:** 关节限位有三套数据，无单一真源

**B16:** GPIO 手写配置在 CubeMX 再生成时会被清掉

**B17:** PWM 频率 1 kHz（可听频段啸叫）

**B18:** 引脚配置文档与代码不一致

---

## 架构级不一致

### OpenRST 自由度语义冲突

| 模块 | 自由度定义 |
|------|-----------|
| windows_sim | pitch + **yaw** + grasp (对称双爪) |
| RST 硬件设计 | pitch + **上夹** + **下夹** (独立) |
| OpenRST URDF | pitch + finger_left + finger_right |

**后果:** 仿真验证的 OpenRST 部分**无法直接迁移到硬件**

---

## 依赖管理

### Python 依赖（需要补 requirements.txt）
```
numpy==2.4.3
scipy==1.17.1
matplotlib==3.10.8
pyserial==3.x
```

### 固件工具链
```
arm-none-eabi-gcc 10.3
OpenOCD 0.11+
GDB multiarch
STM32CubeMX
```

### Vendored 上游（勿修改）
```
Moveit_ws-main/   # ROS2 + MoveIt2 完整工作空间
OpenRST-main/     # OpenRST 学术开源项目
firmware/dummy-*  # Dummy 原版固件
esp32-iot/        # Mongoose 示例集合
```

---

## 缺失的基础设施

- ❌ 无 `requirements.txt` / `pyproject.toml`
- ❌ 无根 `.gitignore`（已在重组分支中添加）
- ❌ 无 CI/CD
- ⚠️ `.vscode/settings.json` 只有一行，指向错误的 CMake 路径

---

## 后续开发路线

### 阶段 A: 工程基线（1-2 天）
- [x] git init + .gitignore（已完成）
- [ ] requirements.txt
- [ ] 更新技术文档
- [ ] 删除死代码

### 阶段 B: 安全加固（2-3 天）
- [ ] 修 robot_viewer 的 !START 问题
- [ ] 修固件死锁 + Error_Handler
- [ ] 统一关节限位真源

### 阶段 C: RST 固件补齐（2-3 周）
- [ ] 确认实物接线
- [ ] 修 .ioc 配置错误
- [ ] 实现电流限幅
- [ ] 实现 PID 控制环
- [ ] 实现堵转找零
- [ ] 实现串口协议

### 阶段 D-G: 机械集成 → 主从遥操作 → 训练平台化
详见原 HANDOVER.md 第 8 节。

---

## 参考文档

- 完整交接文档: [`../archive/handover-2026-08-09.md`](../archive/handover-2026-08-09.md)
- 项目总体设计: `项目完整技术文档.txt`（根目录）
- RST 控制设计: `RST夹取端控制设计方案.txt`（根目录）

---

**本文档提取自历史交接文档，部分内容可能已过时。** 📅
