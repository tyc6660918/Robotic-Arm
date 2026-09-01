# U-Arm 主臂

## 1. 定位与边界

U-Arm 是主从式训练平台的手动主端：操作者移动主臂，PC 读取关节位置并计算从臂目标。主端不主动驱动，不承担力反馈；逆运动学、滤波、限速、安全状态机和命令下发均在 PC 端完成。当前目标是先接入 Dummy 六轴机械臂，后续再扩展 xArm、Dobot 等从臂。

## 2. 代码与数据入口

- `robots/U-Arm/src/uarm/`：主臂串口读取、标定和遥操作脚本。
- `robots/U-Arm/src/simulation/mani_skill/`：ManiSkill 仿真框架及参考机器人实现。
- `tools/windows_sim/`：与硬件隔离的 Windows 离线验证环境。
- 历史设计稿不纳入当前提交；本文件只记录当前有效结论。

## 3. 控制链路

主臂舵机位置 → 串口 `ServoReader` → 角度标定 → 主臂 FK → 相对法兰位姿（SE(3)）映射 → One-Euro/限速处理 → Dummy IK → 关节命令。控制周期设计为 20–50 Hz；Clutch 用于重新建立相对零点，Deadman 用于操作者在位确认。

推荐的安全状态机为 `DISABLED → ARMED → ACTIVE`，并支持 `HOLD`、`FAULT` 和人工复位。任何通信超时、数据越界、不可达目标或从臂反馈异常都必须进入保持或故障状态，不能继续发送运动目标。

## 4. 仿真验证

先在 Windows 离线仿真中验证 FK/IK、相对位姿映射、滤波、速度/加速度限制、Clutch/Deadman 和故障恢复，再进行无负载硬件测试。常用命令：

```powershell
python tools\windows_sim\run_sim.py
python tools\windows_sim\run_sim.py --headless --duration 10 --scenario tools\windows_sim\scenarios\circle.json
python -m unittest discover -s tools\windows_sim\tests -v
```

仿真结果只证明数字模型和安全逻辑，不能替代真实舵机、编码器、串口延迟或机械干涉验证。

## 5. 硬件接入要求

接入前必须确认 U-Arm 型号、舵机总线、串口号、波特率和标定方向；默认串口为 1 Mbps 的 Feetech 总线，实际值以设备配置为准。首轮测试应断开从臂负载，限制电源电流并保留断电手段。未确认探针、目标板和串口身份前，不执行烧录、复位、上电或电机动作。

硬件验收至少记录：代码版本、主臂型号、串口和波特率、标定参数、控制周期、目标/反馈数据、停止条件及异常现象。"能读取位置"不等于"遥操作闭环已通过"。

## 6. 当前状态与后续顺序

现有主臂脚本、仿真框架和多种从臂适配代码可作为集成基础，但 U-Arm Config1 的专用模型、与 Dummy 法兰坐标的最终标定以及真实端到端延迟尚未完成验收。建议按以下顺序推进：

1. 固定 U-Arm 与 Dummy 的坐标系、关节方向和标定数据。
2. 在仿真中完成相对 SE(3) 映射、IK 可达性和安全状态机测试。
3. 进行 U-Arm 单机读数和低速无负载测试。
4. 接入 Dummy，逐关节、低速、限流验证，再开展连续遥操作。
5. 最后再统一串口/CAN/ROS2 接口，并记录实机证据。
