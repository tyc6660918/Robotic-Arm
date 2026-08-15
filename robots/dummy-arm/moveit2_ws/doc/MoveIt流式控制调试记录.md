# MoveIt流式控制调试记录

## 1. 系统架构与文件变更

为实现基于MoveIt Servo的机械臂流式实时控制，对工作区内的相关文件进行了以下新增与修改。

### 1.1 新增文件清单

1. **`src/dummy_controller/dummy_controller/dummy_servo_hardware.py`**
   - 功能定位：作为硬件的直接驱动桥梁。该模块摒弃了传统高延迟的Action通信机制，实现高速率的关节指令下发与状态回传。
2. **`src/dummy_moveit_config/config/servo_streaming.yaml`**
   - 功能定位：MoveIt Servo组件的核心计算配置文件，包含速度限制、奇异点阈值、碰撞检测等关键参数。
3. **`src/dummy_moveit_config/launch/servo_streaming.launch.py`**
   - 功能定位：流式模式的专属一键启动脚本。该启动文件摒弃了`ros2_control_node`，直接将Servo计算引擎与Python硬件桥接节点关联。

### 1.2 修改文件清单

1. **`src/dummy_controller/setup.py`**
   - 修改原因：将新增的Python硬件节点注册至ROS 2构建系统，使其可通过`ros2 run`或launch文件进行启动。
2. **Servo 流式集成最佳实践记录（参见 `../dummy_moveit_config/launch/伺服流式启动指南.md`）**
   - 记录说明：原计划在 `src/dummy_controller/` 目录新增该指南文件，但实际未创建；相关配置与启动说明已统一整理至 `dummy_moveit_config/launch/伺服流式启动指南.md`，重点涵盖后期发现的 Servo 引擎需手动激活等注意事项。

---

## 2. 切换至编译工作区后执行构建流程

当在Gemini开发目录完成程序修改后，需按以下步骤同步至编译工作区并执行构建：

```bash
cd ~/apps/dummy_ws
# （恢复备份）将备份工作区的源码同步至Gemini开发目录
cp -r ~/apps/backup/dummy_ws_20260328/src/* ~/apps/gemini/dummy_ws/src/
# 将Gemini开发目录的最新修改同步至正式编译工作区
cp -r ~/apps/gemini/dummy_ws/src/* ~/apps/dummy_ws/src/
# 执行工作区构建
colcon build
# 刷新工作区环境变量
source install/setup.bash
```

---

## 3. 基础运行与调试命令

### 3.1 启动机械臂流式控制节点

```bash
ros2 launch dummy_moveit_config servo_streaming.launch.py
```

### 3.2 启动后激活Servo引擎响应

出于安全设计，Servo引擎启动后默认处于待机状态，需手动调用服务进行激活：

```bash
ros2 service call /servo_node/start_servo std_srvs/srv/Trigger
```

### 3.3 检查Servo引擎运行状态

通过订阅状态话题确认Servo引擎是否已进入正常工作状态：

```bash
ros2 topic echo /servo_node/status
```

### 3.4 奇点规避：启动后指定关节初始偏移

机械臂上电后若所有关节角度均为`Radians: [0. 0. 0. 0. 0. 0.]`，可能导致逆运动学求解遭遇奇异构型。建议启动后先执行一次微小的关节增量运动：

```bash
ros2 topic pub --once /servo_node/delta_joint_cmds control_msgs/msg/JointJog "{header: {stamp: 'now', frame_id: 'base_link'}, joint_names: ['Joint1', 'Joint2', 'Joint3', 'Joint4', 'Joint5','Joint6'], velocities: [0.1, 0.1, 0.1, 0.1, 0.1, 0.1]}"
```

---

## 4. 笛卡尔空间控制指令集

以下指令通过`/servo_node/delta_twist_cmds`话题以50 Hz频率持续发布`TwistStamped`消息，实现末端执行器的六自由度流式控制。

### 4.1 平移运动

- **Y轴负向平移**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.05, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
  ```

- **Y轴正向平移**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: 0.05, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
  ```

- **X轴正向平移**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.05, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
  ```

- **X轴负向平移**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: -0.05, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
  ```

- **Z轴正向平移**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.0, z: 0.05}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
  ```

- **Z轴负向平移**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.0, z: -0.05}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
  ```

### 4.2 姿态旋转运动

- **绕X轴正向旋转（Roll+）**（注意：原注释行中附带的launch命令仅为上下文残留，执行前需单独启动）：
  ```bash
  ros2 launch dummy_moveit_config servo_streaming.launch.py
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.0, z: -0.0}, angular: {x: 0.1, y: 0.0, z: 0.0}}}"
  ```

- **绕X轴负向旋转（Roll-）**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.0, z: -0.0}, angular: {x: -0.1, y: 0.0, z: 0.0}}}"
  ```

- **绕Y轴正向旋转（Pitch+）**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.0, z: -0.0}, angular: {x: 0.0, y: 0.1, z: 0.0}}}"
  ```

- **绕Y轴负向旋转（Pitch-）**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.0, z: -0.0}, angular: {x: 0.0, y: -0.1, z: 0.0}}}"
  ```

- **绕Z轴正向旋转（Yaw+）**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.0, z: -0.0}, angular: {x: 0.0, y: 0.0, z: 0.1}}}"
  ```

- **绕Z轴负向旋转（Yaw-）**：
  ```bash
  ros2 topic pub --rate 50 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.0, z: -0.0}, angular: {x: 0.0, y: 0.0, z: -0.1}}}"
  ```

### 4.3 定长时间控制示例

- **Y轴负向平移（持续0.5秒，共发送25帧）**：
  ```bash
  ros2 topic pub --rate 50 -t 25 /servo_node/delta_twist_cmds geometry_msgs/msg/TwistStamped "{header: {stamp: 'now', frame_id: 'base_link'}, twist: {linear: {x: 0.0, y: -0.05, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}}"
  ```

---

## 5. HTTP流式API服务集成

### 5.1 设计背景说明

`dummy_server`包中的`api_server.py`已将MoveIt的`plan`与`execute`流程封装为可通过HTTP调用的接口。每次调用需输入目标位姿参数，随后由MoveIt完成规划与执行。该模式适用于长距离离散运动规划场景。

为满足遥操作场景下的实时连续控制需求，新增流式实时控制HTTP接口（`stream_api`）。该接口面向遥控器等输入设备，推拉杆数值区间为`[0.0, 1.0]`，其中`0.0`表示对应方向静止，`1.0`表示对应方向全速运动。

本次开发约束：不修改原有离线规划API相关文件（如`api_server.py`等），新增HTTP服务端程序命名为`stream_api_server.py`。

### 5.2 新增与修改文件清单

1. **新增文件：`src/dummy_server/server/stream_api_server.py`**
   - 核心服务端程序，采用FastAPI框架，将HTTP请求转换为MoveIt Servo的实时增量速度指令。
2. **新增文件：`src/dummy_server/server/stream_api_client_demo.py`**
   - 不依赖ROS 2环境的纯Python客户端调用示例。
3. **修改文件：`src/dummy_server/CMakeLists.txt`**
   - 安装配置：在`install(PROGRAMS ...)`列表中添加`stream_api_server.py`，确保`colcon build`后可正确安装。

### 5.3 运行建议

1. **启动服务端（需运行于已配置ROS 2环境的终端）**：
   ```bash
   # 确保 MoveIt Servo 节点已启动后运行
   python3 src/dummy_server/server/stream_api_server.py
   ```

2. **启动客户端Demo（可运行于任意联网终端）**：
   ```bash
   python3 src/dummy_server/server/stream_api_client_demo.py
   ```

### 5.4 启动与测试命令

#### 启动流式服务
```bash
cd ~/apps/dummy_ws
python src/dummy_server/server/stream_api_server.py
```
*注：若首次启动后控制无响应，可重复启动两次进行验证。*

#### 功能测试
```bash
# 流式控制末端笛卡尔位姿
python src/dummy_server/server/stream_api_client_demo.py

# 流式控制各关节运动、查询关节状态、恢复关节初始位姿
python src/dummy_server/server/stream_api_client_demo2.py
```

---

## 6. 基于LeRobot的移动端遥操作集成

### 6.1 环境准备

切换至LeRobot项目目录，并激活对应的conda虚拟环境：
```bash
source ~/apps/python/init_conda.profile
conda activate lerobot
```

### 6.2 初始集成方案

参考`examples/phone_to_so100/teleopmobile_test.py`，采用移动端应用实现机械臂遥操作。与原始实现不同，控制指令不再直接调用CLI-Tool，而是参考`stream_api_client_demo.py`中的HTTP调用方式进行转发。

移动端摇杆通道与机械臂控制自由度的映射关系：
- `a1`：控制X轴（水平左右方向）
- `a2`：控制Y轴（水平前后方向）
- `a3`：控制Z轴（垂直上下方向）
- `a6`：控制Pitch姿态角
- `a7`：控制Yaw姿态角
- `a8`：控制Roll姿态角

初始版本脚本存放路径：`examples/phone_to_so100/stream_teleopmobile_test.py`

### 6.3 v2版本功能增强

在`stream_teleopmobile_test_v2.py`中，保持原有末端笛卡尔控制功能不变的前提下，新增以下功能模块：

**新增功能清单：**
1. **关节空间流式控制**：长按`b3`按钮时触发（未按下`b3`时保持末端笛卡尔坐标控制模式）
   - `a1`、`a2`：分别控制Joint1、Joint2
   - `a3`：控制Joint3
   - `a6`：控制Joint6
   - `a7`、`a8`：分别控制Joint4、Joint5
2. **恢复初始位姿**：按下`b6`按钮时触发，调用对应API将机械臂恢复至初始零位。

**集成API调用列表：**
1. 流式控制末端笛卡尔坐标移动
2. 流式控制各关节独立运动
3. 查询所有关节当前状态
4. 恢复机械臂至初始位姿

**参考Demo命令：**
```bash
# 流式控制末端（已实现API）
python src/dummy_server/server/stream_api_client_demo.py

# 流式控制各关节、查询关节状态、恢复关节（待实现API）
python src/dummy_server/server/stream_api_client_demo2.py
```

**v2版本运行命令：**
```bash
cd ~/apps/gemini/lerobot
python examples/phone_to_dummy/stream_teleopmobile_test_v2.py
```

---

## 7. 全流程启动规范

### 步骤一：启动MoveIt机械臂流式控制节点
```bash
ros2 launch dummy_moveit_config servo_streaming.launch.py
```

### 步骤二：启动MoveIt HTTP流式转发服务
```bash
cd ~/apps/dummy_ws
python src/dummy_server/server/stream_api_server.py
```
*注：若首次启动后控制无响应，可重复启动两次进行验证。*

### 步骤三：激活LeRobot运行环境
```bash
source ~/apps/python/init_conda.profile
conda activate lerobot
cd ~/apps/gemini/lerobot
```

### 步骤四：测试LeRobot遥操作脚本
```bash
python examples/phone_to_dummy/stream_teleopmobile_test_v2.py
```

### 步骤五：启动正式遥操作流程（`robot.ip`默认使用`127.0.0.1`）

**配置方案1：双摄像头（OpenCV前视 + Intel RealSense环境），FPS=1**
```bash
lerobot-teleoperate     --robot.type=dummy_stream     --robot.id=my_awesome_arm     --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 15, fourcc: "MJPG"}, env: {type: intelrealsense, "serial_number_or_name": "242322075348", color_mode: "rgb", width: 640, height: 480, fps: 15, warmup_s: 10}}"     --teleop.type=mobile     --teleop.id=my_awesome_teleop    --fps=1
```

**配置方案2：单摄像头（OpenCV前视，30 FPS）**
```bash
lerobot-teleoperate     --robot.type=dummy_stream     --robot.id=my_awesome_arm     --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}}"     --teleop.type=mobile     --teleop.id=my_awesome_teleop
```

**配置方案3：单摄像头（Intel RealSense环境，15 FPS）**
```bash
lerobot-teleoperate     --robot.type=dummy_stream     --robot.id=my_awesome_arm     --robot.cameras="{env: {type: intelrealsense, "serial_number_or_name": "242322075348", width: 640, height: 480, fps: 15}}"     --teleop.type=mobile     --teleop.id=my_awesome_teleop
```

**配置方案4：无摄像头最简配置**
```bash
lerobot-teleoperate     --robot.type=dummy_stream     --robot.id=my_awesome_arm     --teleop.type=mobile     --teleop.id=my_awesome
```

### 依赖安装与设备查询
```bash
# 安装RealSense相关依赖
pip install -e ".[realsense]"

# 查询RealSense设备列表
lerobot-find-cameras realsense
```

---

## 8. 性能问题与优化方案

### 8.1 已知问题

接入摄像头后，系统出现MoveIt调用卡顿及视频流延迟现象。

### 8.2 优化方案

**方案一：统一采用RealSense摄像头**
RealSense系列摄像头在驱动层面优化相对完善，相较普通USB摄像头在相同参数配置下延迟略低，但整体仍存在卡顿现象。

**方案二：节点物理分离部署**
将MoveIt服务与物理机械臂驱动部署于一台独立主机，LeRobot环境与摄像头采集模块部署于另一台独立主机，通过网络进行通信，以避免单主机计算资源争用。

---

## 9. VirtualBox虚拟机环境配置

在VirtualBox虚拟机环境中，受限于硬件直通性能，可通过降低分辨率与帧率参数延长系统稳定运行时长。

### 配置A：双路320×240@30 FPS
*预期稳定运行时长：约30秒*
```bash
lerobot-teleoperate     --robot.type=dummy_stream     --robot.id=my_awesome_arm     --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 320, height: 240, fps: 30, fourcc: "MJPG"}, env: {type: opencv, index_or_path: 2, width: 320, height: 240, fps: 30, fourcc: "MJPG"}}"     --teleop.type=mobile     --teleop.id=my_awesome_teleop
```

### 配置B：双路320×240@10 FPS（同步降低遥操作主循环至10 FPS）
*预期稳定运行时长：约2分钟（即使不启动MoveIt HTTP服务，性能表现一致）*
```bash
lerobot-teleoperate     --robot.type=dummy_stream     --robot.id=my_awesome_arm     --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 320, height: 240, fps: 10, fourcc: "MJPG"}, env: {type: opencv, index_or_path: 2, width: 320, height: 240, fps: 10, fourcc: "MJPG"}}"     --teleop.type=mobile     --teleop.id=my_awesome_teleop  --fps=10
```
