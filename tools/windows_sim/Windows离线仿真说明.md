# Windows 原生离线主从仿真

本目录是 Dummy 机械臂与理想 OpenRST 器械的纯离线数字孪生。仅使用 Python、NumPy、SciPy、Matplotlib 与标准库，不包含串口代码，不会发送 `!START`、home 或关节命令，亦不依赖 ROS、Ubuntu、WSL、Docker 或虚拟机。

GUI 默认以 60 Hz 为目标更新动画，并使用局部 blit 避免每帧重绘完整 3D 画布。绘图所需正向运动学与轨迹快照仅按显示频率生成，控制循环仍独立保持 100 Hz；实际显示帧率取决于 Windows、TkAgg 与设备性能。

`rst-control-fw` 不属于本阶段的输入、构建项或依赖。OpenRST URDF 仅作静态结构校验；实际仿真使用明确标注的理想 `pitch/yaw/grasp` 模型，不模拟绳驱、摩擦、回差或电机动态。

## 快速开始

在工作区根目录 `E:\Robotic-Arm` 运行：

```powershell
# 交互 GUI，默认处于 READY；Run script 可启动 axis_steps
python windows_sim\run_sim.py

# 固定步长快速运行完整场景，不用于 Windows 实时性能结论
python windows_sim\run_sim.py --headless --no-realtime `
  --scenario windows_sim\scenarios\circle.json

# 真实墙钟 10 秒控制循环测试
python windows_sim\run_sim.py --headless --duration 10 `
  --scenario windows_sim\scenarios\circle.json

# 关闭 One Euro 滤波，记录原始基线
python windows_sim\run_sim.py --headless --no-realtime --no-filter `
  --scenario windows_sim\scenarios\tremor.json

# 1000 组非奇异随机 FK -> IK -> FK 验收
python windows_sim\validate_kinematics.py --samples 1000

# 60 分钟墙钟 soak；该命令会实际运行一小时
python windows_sim\run_sim.py --headless `
  --scenario windows_sim\scenarios\soak_60min.json

# 全部自动化测试
python -m unittest discover -s windows_sim\tests -v
```

运行结果写入 `windows_sim\runs\<唯一时间戳>\`：

- `teleop_samples.csv`：每个控制周期的原始/过滤主手位姿、映射与限速目标、目标/反馈/真实法兰、关节目标/反馈/真实值、逆运动学统计、反馈年龄、故障和误差。`safety_*` 字段是本周期步进前的安全判定输入，其余 tracking/feedback 字段与同一行步进后的关节状态一致。
- `report.json`：逆运动学成功率、P50/P99 周期、状态与故障计数、越界计数和验收布尔值。只有真实墙钟模式会评估 `control_cycle_p99_under_20ms`；固定步长快速模式将其写为 `null`。
- 报告聚合范围是整个 `SimulationApp` 会话。`metadata.scenario_runs` 记录每次脚本的起止时间和完成状态；会话包含脚本前交互或多次脚本时，`metadata.scenario` 为 `mixed_session`。
- 震颤场景分别给出滤波器阶段和实际法兰端到端的 0.5 Hz 幅值损失、10 Hz 衰减及相位差。衰减量以正 dB 表示（例如 `16 dB` 表示幅值降低约 6.3 倍）。滤波器阶段通过不等同于 mock plant 端到端跟踪通过。混合会话中的频谱指标只属于最近一次 tremor 场景段。

## 交互语义

- 内部统一使用米、弧度和四元数；GUI 的姿态滑块显示角度。
- 默认平移缩放为 `0.3`，旋转缩放为 `0.5`。`master_to_slave_axis_map` 默认为单位旋转，可配置主从坐标轴的置换/旋转；旋转映射使用 SO(3) 旋转向量，不直接相减 RPY。
- 默认工作位为 `[0, -30, 45, 0, 30, 0] deg`。Dummy 全零位仍用于正向运动学真值测试，但其 Jacobian 秩亏，不适合作为高精度遥操作起点。
- `Deadman` 使能后才允许运动。`Clutch` 按下时从端保持；释放后在当前主从位姿重新捕获参考，因此不会跳回旧目标。
- GUI 使用独立于 30 Hz 渲染的 100 Hz 主手心跳；超过 50 ms 没有新样本、未来/乱序时间戳、无效输入、反馈超时、持续跟踪误差、逆运动学失败或越界都会进入 HOLD。只有故障清除后的新鲜有效样本才能完成 deadman 释放或 clutch rearm，系统不会自动续动。
- Cartesian 命令限制线速度/角速度和线加速度/角加速度，并使用离散制动曲线避免小步阶跃超调。
- 逆运动学采用有界 SciPy least-squares、解析几何 Jacobian、上一安全目标 warm start 与关节目标速度整形。失败时保持上一安全目标。
- mock plant 使用速度、加速度和 jerk 受限伺服，并支持延迟、命令/反馈掉包、噪声、反馈冻结和关节卡死。
- Windows 调度停顿超过 50 ms 时，安全时钟记录完整停顿，但 plant 动力学只推进最多 50 ms，不追赶历史命令。这是防止数值跳变的保守冻结近似，不能用于推断实机在调度停顿期间的真实运动。
- OpenRST 首轮始终使用 `pitch=0`、`yaw=0`，仅让器械随 Dummy 法兰移动并验证 `grasp`；理想工具 API 已支持配置的 `+/-90 deg` pitch/yaw。

## 场景

- `axis_steps.json`：X/Y/Z、Roll/Pitch/Yaw、grasp 和 clutch。
- `circle.json`：连续圆轨迹和组合姿态。
- `figure_eight.json`：8 字轨迹和组合姿态。
- `tremor.json`：0.5 Hz、30 mm 主动运动叠加 10 Hz、1 mm 震颤。
- `fault_injection.json`：输入断流、80 ms 延迟、10% 命令掉包、反馈掉包/冻结、关节卡死、乱序、无效输入、逆运动学不收敛、不可达偏移、锁存 `FAULT`、显式 clear 及 rearm。不可达事件会刻意绕过滤波与 Cartesian 限速，仅用于确认逆运动学失败路径，不代表正常控制命令；`FAULT` 在事件窗口结束后仍保持，只有 clear 后再完成新的 deadman rearm 才能恢复运动。
- `soak_60min.json`：固定内存记录器下的 60 分钟慢速 8 字稳定性测试。

## 当前边界

本阶段能验证运动学、相对 SE(3) 映射、滤波、限速、离合、安全状态机、日志与确定性故障恢复。不能证明实机机械精度、串口闭环、OpenRST 绳驱性能、MoveIt Servo、ROS QoS、Windows 硬实时性或临床安全性。

未来只读数字影子必须作为独立适配器实现，并且只允许 `#GETJPOS`。不应复用会主动进入命令模式或发送 `!START` 的现有查看器连接逻辑。
