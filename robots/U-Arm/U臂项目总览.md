# U-Arm 主臂系统

## 1. 区域功能定位（功能定位）

本方案采用 U-Arm 模块提供主从式机器人遥操作系统中的主臂硬件与软件栈。该模块基于 LeRobot Anything 项目构建，通过 Feetech 舵机实现位置传感并发布关节角度，以支持对从臂（xArm、Dobot 或 Dummy）的 SE(3) 位姿控制。主臂以只读模式运行（无主动控制），所有逆运动学求解与轨迹规划均在 PC 端完成，控制频率范围为 20–50Hz。

## 2. 关键文件（关键文件）

| File Path | Purpose | Status | Notes |
|-----------|---------|--------|-------|
| `/e/Robotic-Arm/robots/U-Arm/requirements.txt` | Core Python dependencies for U-Arm project | Complete | 180 packages including mani_skill, xarm-python-sdk, feetech-servo-sdk, torch, tensorflow, opencv-python, pyrealsense2, pyserial |
| `/e/Robotic-Arm/robots/U-Arm/overall_requirements.txt` | Complete dependency set including ROS1 Noetic packages | Complete | 280 packages - superset including rospy, tf, rviz, moveit, gazebo |
| `/e/Robotic-Arm/robots/U-Arm/ros1_requirements.txt` | ROS1-specific Python packages for catkin workspace | Complete | 101 packages - actionlib, tf, rosbag, rviz, moveit integration |
| `/e/Robotic-Arm/robots/U-Arm/README_CN.md` | Main project documentation for LeRobot Anything system | Complete | Covers 3 hardware configs, cost $60+, supports xArm7/Dobot CR5/Franka, requires Ubuntu 20.04 + ROS Noetic |
| `/e/Robotic-Arm/robots/U-Arm/U臂与Dummy臂法兰接口实现说明.md` | Implementation plan for Config1 controlling Dummy via PC teleoperation | Complete | 436 lines - DH parameters, calibration, safety FSM, IK/FK requirements, PC software architecture |
| `/e/Robotic-Arm/robots/U-Arm/遥操作实施方案.md` | Software verification plan using windows_sim for offline testing | Complete | Describes simulation environment, SE(3) mapping, One Euro filter, IK solver, safety FSM |
| `/e/Robotic-Arm/robots/U-Arm/src/uarm/scripts/Uarm_teleop/Feetech_servo/feetech_servo_reader.py` | ROS node reading Feetech servo positions and publishing to /servo_angles | Complete | 50Hz, 1Mbps, reads 7 servos via GroupSyncRead. WARNING: writes EPROM offsets on startup |
| `/e/Robotic-Arm/robots/U-Arm/src/uarm/scripts/Follower_Arm/xarm/servo2xarm.py` | ROS teleoperation node subscribing to /servo_angles and controlling xArm | Complete | 20Hz control loop, IP 192.168.1.199, converts servo angles to xArm joint commands with gripper control |
| `/e/Robotic-Arm/robots/U-Arm/src/uarm/scripts/Follower_Arm/LeRobot/README.md` | Guide for using U-Arm with LeRobot framework | Complete | Requires LeRobot environment with [feetech] feature, no ROS needed for LeRobot integration |
| `/e/Robotic-Arm/robots/U-Arm/mechanical/Feetech_servo/Config1_STL/config1.STEP` | CAD assembly file for Config1 mechanical design | Available | Complete STEP file with STL exports for 3D printing - base, 6 links, sitter, trigger components |
| `/e/Robotic-Arm/robots/U-Arm/src/uarm/package.xml` | ROS1 catkin package manifest | Complete | Depends on rospy and std_msgs, minimal ROS package configuration |
| `/e/Robotic-Arm/robots/U-Arm/src/uarm/scripts/run_all_nodes.sh` | Launch script to start complete teleoperation system | Complete | Launches cam_pub, servo_reader, servo2xarm, episode_recorder nodes for full ROS pipeline |

## 3. 当前进度（当前进展）

| Component | Status | Evidence | Notes |
|-----------|--------|----------|-------|
| Project structure analysis | Complete | All key files identified and reviewed | 12 critical files documented |
| Dependency documentation | Complete | 3 requirements files covering 280+ packages | ROS1, Python ML stack, robotics libraries |
| Setup instructions review | Complete | README_CN.md analyzed | Covers hardware configs, cost estimates, Ubuntu/ROS requirements |
| SDK integration patterns | Complete | xArm-Python-SDK usage reviewed in servo2xarm.py | Ethernet control at 20Hz via 192.168.1.199 |
| Hardware requirements documentation | Complete | Config1 STEP file and BOM reviewed | 7 Feetech servos, 3D printed parts, USB-serial adapter |
| ROS1 package configuration | Complete | package.xml and catkin structure reviewed | Minimal rospy + std_msgs dependencies |
| Teleoperation implementation | Complete | feetech_servo_reader.py and servo2xarm.py analyzed | 50Hz sensing, 20Hz control, /servo_angles topic |
| Physical Config1 hardware assembly | Incomplete | No evidence of assembled hardware | Blocks servo calibration and URDF creation |
| Servo calibration and zero-point recording | Incomplete | Awaiting physical hardware | Cannot proceed without assembled Config1 |
| URDF model creation for Config1 | Incomplete | Blocked by lack of physical measurements | STEP file available but not measured |
| Hardware connection testing | Incomplete | No physical hardware to test | Serial port, power supply, servo IDs need validation |
| End-to-end latency measurements | Incomplete | No real hardware for measurement | Target <100ms not yet validated |

## 4. 已完成功能（已完成功能）

- **项目架构文档**：README_CN.md 涵盖 3 种硬件配置（Config1/2/3），包含成本估算、从臂兼容性（xArm7、Dobot CR5、Franka），以及 Ubuntu 20.04 + ROS Noetic 的部署要求
- **依赖管理**：针对核心 Python 栈（180 个包）、ROS1 集成（101 个包）及整体环境（280 个包）提供完整的依赖文件，涵盖 torch、tensorflow、mani_skill、机器人学工具链
- **实施规划**：U臂与Dummy臂法兰接口实现说明.md 提供 436 行的详细方案，涵盖 DH 参数、标定流程、安全状态机（DISABLED/ARMED/ACTIVE/HOLD/FAULT）、IK/FK 需求及 PC 端软件架构
- **ROS 集成**：提供功能完备的 ROS1 catkin 包，包含 feetech_servo_reader.py（50Hz 位置传感）与 servo2xarm.py（20Hz 控制）节点，向 /servo_angles 话题发布 Float64MultiArray 消息
- **SDK 集成**：servo2xarm.py 中展示 xArm-Python-SDK 集成方案，支持以太网控制（192.168.1.199）、关节指令转换与夹爪控制
- **机械设计**：提供完整的 Config1 CAD 包，包含 config1.STEP 装配体与用于 3D 打印的 STL 导出文件（基座、6 个连杆、支架、扳机组件）
- **仿真验证规划**：遥操作实施方案.md 记述 windows_sim 离线测试方案，包括 SE(3) 映射、One Euro 滤波器、IK 求解器及安全状态机验证
- **LeRobot 框架支持**：LeRobot/README.md 中记载了替代集成路径，要求启用 [feetech] 特性的 LeRobot 环境，无需 ROS 依赖
- **启动自动化**：run_all_nodes.sh 脚本实现完整遥操作管线（cam_pub、servo_reader、servo2xarm、episode_recorder）的自动化启动

## 5. 未完成内容（未完成工作）

| Task | Priority | Blocker | Next Step |
|------|----------|---------|-----------|
| Physical hardware assembly (Config1 U-Arm not yet built) | High | Requires 3D printing, servo procurement, mechanical assembly | Procure 7x Feetech servos with unique IDs, print Config1 STL parts, assemble per config1.STEP |
| Servo calibration and zero-point recording | High | Awaiting physical Config1 hardware | After assembly, run calibration routine to record EPROM offsets and joint directions |
| URDF model creation for Config1 | High | Blocked by lack of physical measurements from assembled hardware | Measure link lengths from assembled Config1, extract DH parameters, create URDF matching STEP geometry |
| Hardware connection testing | High | No physical hardware available | Validate USB-serial adapter, test Feetech servo communication at 1Mbps, verify power supply voltage/current |
| End-to-end latency measurements with real hardware | Medium | Physical U-Arm and follower arm required | Measure total latency from servo read → IK computation → follower command, confirm <100ms target |

## 6. 使用说明（使用说明）

### Core Architecture（核心架构）

- **主臂**：Config1 配置，含 6 个 Feetech 舵机（只读位置传感）+ 1 个扳机/夹爪通道
- **通信**：USB 串口，波特率 1Mbps，采用 Feetech scservo_sdk 协议
- **控制范式**：相对 SE(3) 位姿映射（非关节对关节），计算任务在 PC 端执行
- **ROS1 集成**：以 50Hz 频率发布 /servo_angles（Float64MultiArray）

### Setup Requirements（环境要求）

1. **操作系统**：Ubuntu 20.04，已安装 ROS Noetic
2. **工作空间**：在 `robots/U-Arm/` 目录构建 catkin 工作空间
3. **依赖安装**：从 `requirements.txt` 安装 Python 依赖包
4. **网络配置**：为 xArm 配置网络（若使用 xArm 从臂，IP 为 192.168.1.199）
5. **串口配置**：设置 udev 规则以确保串口设备名称稳定
6. **标定流程**：标定舵机零位与方向（需物理硬件支持）
7. **URDF 建模**：基于 STEP 文件测量结果创建 Config1 URDF 模型（需物理硬件支持）

### Hardware Configuration（硬件配置 - Config1）

- 7 个具备唯一 ID 的 Feetech 舵机（ID 范围 1–7）
- 用于主臂的 USB-串口适配器
- 舵机独立供电电源（电压取决于舵机型号）
- 来自 Config1_STL 的 3D 打印机械结构件
- Config1 STEP 文件可供参考，但尚未完成实物装配

### Running the System（启动流程）

```bash
# Source ROS workspace
source /opt/ros/noetic/setup.bash
source ~/catkin_ws/devel/setup.bash

# Launch all nodes
cd robots/U-Arm/src/uarm/scripts
./run_all_nodes.sh
```

该启动脚本依次加载以下节点：
- `cam_pub`：相机发布节点
- `servo_reader`：Feetech 舵机位置读取节点（50Hz）
- `servo2xarm`：xArm 控制转换节点（20Hz）
- `episode_recorder`：训练数据记录节点

### SDK Integration Patterns（SDK 集成模式）

- **xArm**：通过以太网使用原生 Python SDK（192.168.1.199），控制循环频率 20Hz
- **Dobot**：`Follower_Arm/Dobot/` 目录中的自定义 API 封装
- **ARX5**：无需 ROS 的直接控制方案
- **LeRobot**：替代框架集成方案（无需 ROS）

### Critical Warnings（关键警示）

- `feetech_servo_reader.py` 在启动时写入 EPROM 偏移量——开发阶段可能覆盖标定数据。量产部署前需修改该行为。
- xArm IP 地址已硬编码（192.168.1.199），需根据实际网络进行配置
- 串口设备名称（/dev/ttyUSB0）采用硬编码方式，未使用 udev 规则

## 7. 风险与限制（风险与局限）

| Risk | Impact | Evidence | Mitigation |
|------|--------|----------|------------|
| Feetech servo reader writes EPROM offsets on startup | High | `feetech_servo_reader.py` writes calibration data to servo flash on every startup | Modify code to read-only mode or add startup flag to disable EPROM writes during development |
| No Config1 URDF exists yet | High | FK/IK calculations blocked until hardware assembled and measured | Prioritize physical assembly to enable URDF creation from measurements |
| xArm IP address hardcoded | Medium | `servo2xarm.py` uses hardcoded 192.168.1.199 | Move IP to ROS parameter or config file |
| ROS1 Noetic EOL in 2025 | Medium | Project built on ROS1 which reaches end-of-life 2025 | Plan migration to ROS2, or accept maintenance burden for legacy stack |
| Hardware assembly prerequisites not documented | Medium | BOM incomplete - fasteners, bearings, couplers not specified | Extract complete BOM from STEP file, add assembly manual with wiring diagrams |
| Multiple Python environments may conflict | Medium | ROS1 system Python vs LeRobot env may have version conflicts | Use virtual environments with clear activation instructions, document environment switching |
| Serial port device names hardcoded | Low | Uses `/dev/ttyUSB0` instead of udev rules | Create udev rules based on Feetech adapter VID/PID for stable device names |

## 8. 依赖关系（依赖项）

- **ROS1 Noetic 环境**（Ubuntu 20.04）
- **Python 3.8+**
- **xArm-Python-SDK**：用于从臂控制（版本 1.15.3）
- **Feetech servo SDK**（feetech-servo-sdk 1.0.0）：用于主臂数据读取
- **Config1 物理硬件装配**（尚未完成）
- **xArm 网络配置**（若作为从臂使用）
- **串口访问权限与 udev 规则**：确保设备名称稳定
- **来自 Config1_STL 文件的 3D 打印机械结构件**
- **舵机标定数据**（受硬件装配阻塞）
- **核心 Python 栈**：torch 2.8.0、tensorflow 2.16.1、opencv-python 4.11.0、pyrealsense2 2.55.1、numpy、scipy
- **机器人学库**：mani_skill 3.0.0b21、pytorch-kinematics、roboticstoolbox-python、spatialmath-python
- **仿真环境**：SAPIEN 3.0.1 物理引擎、ManiSkill 框架

## 9. 下一步计划（后续工作）

1. **在 Ubuntu 20.04 上安装 ROS1 Noetic**（若尚未部署）—— 构建 catkin 工作空间与执行 ROS 节点的前置条件
2. **创建 Python 虚拟环境并安装 requirements.txt**—— 将依赖与系统 Python 隔离，避免与 ROS1 系统包产生版本冲突
3. **构建 catkin 工作空间**（`cd robots/U-Arm && catkin_make`）—— 编译 ROS 包并验证依赖完整性
4. **配置 xArm-Python-SDK 与机器人 IP 地址**—— 若使用 xArm 作为从臂，配置网络并验证与 192.168.1.199 的以太网连通性
5. **采购并装配 Config1 硬件**—— 3D 打印 STL 结构件，采购 7 个具备唯一 ID 的 Feetech 舵机，按照 config1.STEP CAD 文件完成装配（高优先级——阻塞所有硬件验证工作）
6. **使用物理 Feetech 舵机测试舵机读取程序**—— 硬件装配完成后，验证 1Mbps USB-串口通信有效性，确认 7 个舵机的 GroupSyncRead 功能正常
7. **标定 Config1 运动学参数并创建 URDF 模型**—— 基于装配后的实物测量连杆长度，提取 DH 参数，构建与物理几何一致的 URDF
8. **修改 feetech_servo_reader.py 为只读运行模式**—— 移除启动时的 EPROM 写入操作，避免开发阶段标定数据损坏
9. **配置 udev 规则以获取稳定的串口设备名称**—— 基于 Feetech 适配器的 VID/PID 创建规则，消除 /dev/ttyUSB0 硬编码
10. **运行 windows_sim 进行离线验证**—— 在硬件集成前测试 SE(3) 映射、IK 求解器、One Euro 滤波器及安全状态机
11. **测量端到端延迟**—— 硬件集成后，验证从舵机读取经 IK 计算到从臂指令下达的全链路延迟是否满足 <100ms 指标
