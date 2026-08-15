# Config1 U-Arm 控制 Dummy 法兰实施方案

## 1. 目标与边界

目标是复刻 Feetech 版 Config1 U-Arm，将其作为一个无力输出的六自由度手动主端。主端只向 PC 上报关节位置；PC 负责主臂正运动学（FK）、相对法兰位姿映射、滤波、限速、Dummy 逆运动学（IK）、安全检查和命令下发。

本方案的控制目标是 Dummy 的末端法兰，不是主从关节一一对应。

```text
Config1 U-Arm (手动拖动、只读位置)
  -> PC 主端驱动
  -> PC 遥操作控制器
  -> PC Dummy 驱动
  -> Dummy USB-CDC
  -> Dummy 控制核 / CAN / 电机
```

第一版不控制 Dummy 夹爪；U-Arm 第 7 路可先保留为扳机或离合输入。Dummy 的现有 ASCII 协议没有暴露夹爪命令，需要另行扩展。

## 2. 已确认的源码事实

### 2.1 Config1 与主端代码

- Feetech Config1 装配源文件：`mechanical/Feetech_servo/Config1_STL/config1.STEP`。
- 对应 STL 包含 base、link1 到 link6、sitter、sitter_mid 和 trigger_short。
- 当前 Feetech 读取器访问 1 到 7 号舵机，串口为 `/dev/ttyUSB0`，波特率为 1,000,000：`src/uarm/scripts/Uarm_teleop/Feetech_servo/feetech_servo_reader.py`。
- 当前读取器通过 `GroupSyncRead` 批量读取位置，计算 `(current_pos - zero_pos) / 4096 * 360`，发布 7 元素角度数组到 `/servo_angles`。
- 现有项目明确定位为关节空间低延迟遥操作；Config1 的 README 适配名单含 xArm6、PiPER 等六轴臂：`U臂项目总览.md`。

### 2.2 Dummy 实体接口

- Dummy 固件接受 USB-CDC、UART4 的 ASCII 行命令：`firmware/dummy-ref-core-fw/UserApp/protocols/ascii_protocol.cpp`。
- `#GETJPOS` 返回六关节角度；`!START`、`!STOP`、`!DISABLE` 管理运行状态。
- `#CMDMODE 2` 选择可中断目标点模式。
- `>j1,j2,j3,j4,j5,j6,speed` 发送六关节角度目标，单位为度：`firmware/dummy-ref-core-fw/Robot/instances/dummy_robot.cpp`。
- Dummy 主控的固定控制任务由 5 ms 定时器唤醒，即 200 Hz：`firmware/dummy-ref-core-fw/UserApp/main.cpp`。
- Dummy 固件已有 `MoveL(x,y,z,a,b,c)`，但第一版不直接依赖它完成 PC 侧遥操作安全。

### 2.3 必须避开的现有行为

当前 Feetech 读取器在启动时会解锁 EPROM 并写入每个舵机的 Homing Offset。这不适合日常采集：主臂零点必须由 PC 的标定文件管理，不能因启动采集程序而改写机械零位。

## 3. 技术决策

| 项目 | 第一版决定 | 原因 |
| --- | --- | --- |
| 主臂构型 | Feetech Config1 | 机械 STEP 和同步读取代码均在仓库中 |
| 主端控制方式 | 只读位置、手动拖动 | 主臂不承担执行器控制责任 |
| 运动映射 | 相对笛卡尔法兰位姿 | 不要求主从关节拓扑相同 |
| 控制计算位置 | PC | FK、IK、限位、滤波和故障处理集中管理 |
| Dummy 下发方式 | PC 求 IK 后发送六关节目标 | 便于连续解选择、限位与速度检查 |
| 主端中间件 | 第一版不依赖 ROS 控制 | 减少 ROS1/ROS2 跨版本复杂度 |
| 可视化 | 可选 ROS2 / RViz 或独立 Web/日志 | 不放入实时安全闭环 |

## 4. 复刻前的输出物

在采购或打印前，建立一个 `config1_build/` 工程目录，至少包含以下文件：

```text
config1_build/
  bom.csv
  wiring.md
  assembly.md
  uarm_config1.urdf
  uarm_config1_calibration.yaml
  dummy_calibration.yaml
  safety_limits.yaml
  test_records/
```

仓库未提供本地 Config1 BOM 和逐步装配说明。因此螺丝、轴承、联轴器、线束、舵机支架和电源规格不能凭源码猜测，必须从 STEP 装配、所选舵机图纸和实物试装中提取。

## 5. 硬件实施

### 5.1 机械件

使用 `config1.STEP` 作为唯一机械基线，不混用 Zhonglin 版 Config1 零件。先完成以下步骤：

1. 在 CAD 中打开 STEP，识别每一个旋转关节的轴线、舵机安装方向、轴承、紧固件和干涉面。
2. 为每个关节建立编号 `J1` 到 `J6`，为扳机/夹爪输入建立编号 `G1`。
3. 在 CAD 中定义基座坐标系 `uarm_base` 和末端坐标系 `uarm_tool`。
4. 打印一个舵机安装验证件和一个完整关节，确认孔距、花键、轴向预紧和打印收缩补偿。
5. 通过单关节验证后再打印完整套件。
6. 所有走线位置必须在全行程内无拉扯、无夹线、无与旋转件摩擦。

### 5.2 舵机与编号

现有 Feetech 读取器访问 7 个地址，因此第一版硬件规划应预留：

- 6 个用于主臂关节位置读取的舵机；
- 1 个用于扳机、夹爪或保留通道的舵机；
- 一个能同时挂载全部设备的串行总线。

装配前逐个给舵机设置唯一 ID，并记录下表。修改 ID 时只连接一个舵机，避免整条总线被重编号。

| PC 逻辑关节 | 舵机 ID | 机械方向 | 机械零位 | 备注 |
| --- | ---: | ---: | --- | --- |
| J1 | 1 | 待标定 | 待标定 | 基座旋转 |
| J2 | 2 | 待标定 | 待标定 | 肩部 |
| J3 | 3 | 待标定 | 待标定 | 肘部 |
| J4 | 4 | 待标定 | 待标定 | 腕部 1 |
| J5 | 5 | 待标定 | 待标定 | 腕部 2 |
| J6 | 6 | 待标定 | 待标定 | 腕部 3 |
| G1 | 7 | 待标定 | 待标定 | 扳机或预留 |

具体 Feetech 舵机型号、供电电压、总线电平、接头定义和舵机输出花键，均需依据实际采购型号的数据手册确认。

### 5.3 供电与安全

主臂是手动输入设备，仍必须有稳定电源来读取位置。建议电气分为三部分：

```text
主臂舵机电源 -> 保险丝 -> 电源开关 -> Feetech 总线
PC USB -> 主臂 USB 串口适配器
PC USB -> Dummy USB-CDC

Dummy 执行器电源 -> 硬件急停/使能链 -> Dummy 电机系统
```

- 主臂与 Dummy 执行器使用独立电源。
- Dummy 必须具备不依赖 PC 的硬件急停和失能能力。
- PC 通过 USB 只能发送逻辑命令，不能作为唯一急停手段。
- 电源线、总线线、USB 线均做应力释放；旋转部位使用柔性线束和足够的弯折余量。
- 初次上电时主臂舵机扭矩保持关闭或设为不会阻碍手动拖动的模式。

## 6. 上位机接口设计

### 6.1 物理接口

PC 需要两条独立通信链路：

| 设备 | 连接方式 | PC 职责 |
| --- | --- | --- |
| Config1 U-Arm | USB 串口适配器 | 1 Mbps 读取 Feetech 位置 |
| Dummy 控制核 | USB-CDC 虚拟串口 | ASCII 指令和状态读取 |

Linux 下应使用 `/dev/serial/by-id/` 创建稳定设备名，例如：

```text
/dev/serial/by-id/uarm_master
/dev/serial/by-id/dummy_controller
```

不要将 `/dev/ttyUSB0` 或 `/dev/ttyACM0` 写死到正式程序中。设备枚举顺序会随重插、启动顺序和其他 USB 设备变化。

### 6.2 软件运行环境

推荐 Ubuntu Linux PC，Python 3.10+。实时控制进程不要求 ROS；最小依赖为：

```text
pyserial
numpy
scipy
PyYAML
feetech-servo-sdk
```

可选项：

- `pinocchio` 或 `pytorch-kinematics`：FK/IK 和 URDF 验证；
- ROS2：发布 `JointState`、RViz 可视化和日志；
- `pytest`：离线单元测试；
- `rosbag2` 或 CSV/Parquet：实验记录。

## 7. 上位机软件结构

建议单独建立 `pc_teleop/`，其模块边界如下：

```text
pc_teleop/
  config/
    uarm_config1_calibration.yaml
    dummy_calibration.yaml
    safety_limits.yaml
  uarm_driver.py
  uarm_kinematics.py
  teleop_controller.py
  dummy_driver.py
  safety_state_machine.py
  recorder.py
  main.py
  tests/
```

### 7.1 `uarm_driver.py`

职责：只读主臂舵机位置，绝不写 EPROM、零偏或控制力矩。

输出数据结构：

```python
MasterSample(
    timestamp_ns: int,
    sequence: int,
    q_rad: ndarray[6],
    trigger: float,
    valid: bool,
    read_latency_ms: float,
    missing_ids: list[int],
)
```

实现要求：

- 使用同步批量读，而不是 7 次独立等待式轮询；
- 读取失败时保留失败状态，不伪造新位置；
- 记录最后一次真实样本时间；
- 初始目标为 50 Hz，先实测 p99 读取时延和丢包率；
- 将原始 ticks 保留在日志中，角度换算交给标定层。

### 7.2 `uarm_kinematics.py`

职责：加载 Config1 URDF、标定后的六关节角度，计算：

```text
T_uarm_tool = FK(q_uarm)
```

URDF 建立方法：

1. 从 STEP 提取每个关节轴和相邻轴间几何关系；
2. 将关节零位定义为可重复装配的机械姿态；
3. 使用实物标定 `zero_ticks` 和 `direction` 修正舵机读数；
4. 通过十个以上已测姿态验证 FK；
5. 未达到位置和姿态误差目标前，不接入真实 Dummy。

### 7.3 `teleop_controller.py`

职责：由主臂相对位姿生成 Dummy 目标法兰位姿。

使能时捕获：

```text
T_master_ref = T_uarm_tool
T_dummy_ref  = FK_dummy(q_dummy_feedback)
```

运行时计算：

```text
Delta_T_master = inverse(T_master_ref) * T_uarm_tool
Delta_T_scaled = scale_translation_rotation(Delta_T_master)
T_dummy_target = T_dummy_ref * A * Delta_T_scaled * inverse(A)
```

其中 `A` 是已标定的主从坐标轴旋转矩阵。旋转必须使用四元数或 SO(3) 旋转向量，不能直接对 RPY 欧拉角做减法。

第一版初始参数：

| 参数 | 初始值 |
| --- | ---: |
| 平移缩放 | 0.30 |
| 旋转缩放 | 0.50 |
| 主端死区 | 0.5 deg 等效量 |
| 最大平移速度 | 0.05 m/s |
| 最大角速度 | 0.5 rad/s |
| 最大平移加速度 | 0.20 m/s2 |
| 最大角加速度 | 2.0 rad/s2 |
| 控制发送频率 | 20 Hz |

这些值只作为空载、低速起点。必须按实际 Dummy 动力学、工作空间和操作者手感调整。

### 7.4 `dummy_driver.py`

职责：Dummy 串口唯一读写者。

初始化顺序：

```text
连接串口
-> #GETJPOS
-> 检查返回的 6 个关节值
-> 等待操作者确认安全姿态
-> !START
-> #CMDMODE 2
-> 保持当前关节目标
```

控制命令格式：

```text
>j1,j2,j3,j4,j5,j6,speed\n
```

要求：

- PC 侧 IK 输出必须是六个绝对关节角，单位为度；
- 每个目标先经过 Dummy 真实限位、速度限制和加速度限制；
- 以最新状态覆盖旧目标，不在 PC 中堆积轨迹；
- 周期性发送 `#GETJPOS` 并检测反馈新鲜度；
- 串口断开、异常响应或反馈超时均进入 `FAULT`。

## 8. 安全状态机

```text
DISABLED
  -> ARMED       操作者确认、两端通信有效、姿态安全
  -> ACTIVE      deadman 按下，捕获参考姿态
  -> HOLD        deadman 松开、短暂输入超时、IK 暂时失败
  -> FAULT       越限、长超时、反馈错误、跟踪误差过大
```

状态规则：

- `DISABLED`：不发送运动目标；
- `ARMED`：读取两端状态，主从目标保持当前 Dummy 姿态；
- `ACTIVE`：只接受时间戳递增且有效的主端样本；
- `HOLD`：保持最后一个安全关节目标，不自动恢复运动；
- `FAULT`：发送 `!STOP`、`!DISABLE`，要求人工清错并重新按 deadman；
- 主端样本超过 80 ms 未更新、Dummy 反馈超过 100 ms 未更新时，进入 `FAULT`；
- PC 进程退出不能替代硬件急停。

Dummy 当前 `!STOP` 的源码逻辑只冻结目标并清队列，不保证所有电机物理失能。正式接入前应修改 Dummy 固件，加入主机心跳 watchdog：超过阈值未收到有效运动命令时清队列并调用全部关节的 `SetEnable(false)`。

## 9. 标定流程

### 9.1 主臂舵机标定

1. 关闭主臂舵机扭矩。
2. 将主臂放到定义好的机械标定姿态。
3. 读取并保存每个舵机原始 tick，写入 `zero_ticks`。
4. 手动正向转动每个关节，确认 PC 角度增大或减小，填入 `direction`。
5. 测量单轴转动 30、60、90 度，确认 ticks-to-radian 比例。
6. 重启 PC 程序，重新读取验证标定可重复性。

示例配置：

```yaml
master:
  servo_ids: [1, 2, 3, 4, 5, 6, 7]
  zero_ticks: [2047, 2047, 2047, 2047, 2047, 2047, 2047]
  direction: [1, -1, 1, 1, -1, 1, 1]
  ticks_per_revolution: 4096
  tool_frame: uarm_tool
```

数值只是配置结构示例，不是 Config1 的已标定参数。

### 9.2 主臂坐标系标定

1. 将 `uarm_base` 固定到主臂基座。
2. 定义 `uarm_tool` 在操作者实际握持或触点位置。
3. 使用治具或测量板采集至少十个不同姿态的末端位置。
4. 调整 URDF 固定变换和零偏，使 FK 与实测一致。
5. 记录位置 RMS 误差、最大误差与姿态误差。

### 9.3 主从坐标变换标定

令 Dummy 基座为 `dummy_base`，构造一个刚体旋转 `A`：

```text
uarm_base axes -> dummy_base axes
```

先只测试三个平移方向，再测试三个旋转方向。每个方向只允许 5 mm 或 5 deg 小增量。若方向错误，只修改 `A` 或映射配置，不修改底层驱动代码。

## 10. 测试与验收

### 10.1 软件离线测试

- 输入固定主臂样本，验证输出固定；
- 输入单轴主臂运动，验证 Dummy 法兰沿预期轴移动；
- 验证平移、旋转缩放；
- 验证旋转四元数连续性；
- 验证关节限位、速度限制、加速度限制；
- 验证 IK 无解时保持最后安全目标；
- 验证乱序时间戳、NaN、超时和串口异常均进入 HOLD 或 FAULT。

### 10.2 台架测试顺序

1. 主臂单独读位置，不连接 Dummy。
2. Dummy 单独执行 `#GETJPOS`、`!START`、`!STOP`、`!DISABLE`。
3. 桥接程序只记录，不发送命令。
4. 连接 Dummy，但保持 `DISABLED`，验证没有首帧运动。
5. 进入 `ARMED`，验证目标与 Dummy 当前关节反馈相同。
6. 仅启用一轴小幅平移或转动。
7. 低速完成六个法兰自由度测试。
8. 逐步提高工作空间和速度。
9. 进行连续 30 分钟低速稳定性测试。

### 10.3 最低验收指标

| 指标 | 第一版目标 |
| --- | --- |
| U-Arm 连续读取 | 30 分钟无异常退出 |
| 主端有效样本 | 实测频率稳定，记录 p99 时延 |
| 控制命令频率 | 20 Hz 稳定 |
| Dummy 反馈超时 | 小于 100 ms 时正常，大于阈值必进 FAULT |
| 首帧跳变 | 使能后无可见或超限跳变 |
| 断开主端 | 小于超时阈值进入安全停止 |
| IK 无解/越限 | 保持或停止，不发送非法关节角 |
| 急停 | 不依赖 PC，能让 Dummy 失能 |

## 11. 分阶段计划

### 阶段 A：机械和通信台架

输出：完整 BOM、打印件、已编号的舵机、稳定主臂串口读取。

完成条件：PC 能持续读取 1 到 7 号舵机，并能记录原始 ticks。

### 阶段 B：主臂模型和标定

输出：Config1 URDF、标定 YAML、FK 验证报告。

完成条件：主臂末端坐标与实体测量结果一致，误差满足预设目标。

### 阶段 C：Dummy 驱动和安全基础

输出：Dummy 串口驱动、状态机、固件 watchdog、硬件急停验证。

完成条件：所有通信失效场景均能安全停止。

### 阶段 D：低速法兰遥操作

输出：相对位姿控制器、主从坐标标定、控制日志。

完成条件：六个法兰方向低速、可预测、无跳变地工作。

### 阶段 E：性能与可视化

输出：延迟统计、故障报告、ROS2/RViz 或独立监控界面。

完成条件：完成长期运行、故障注入和操作者验证。

## 12. 需要确认的阻塞项

1. 实际购买的 Feetech 舵机具体型号、供电规格、数据线电平和 USB 适配器型号。
2. Config1 STEP 中每个紧固件、轴承、联轴器和安装配件的精确规格。
3. U-Arm 六个关节和第七通道的实际机械含义、行程和可达空间。
4. Dummy 实际烧录的固件是否为 `dummy-ref-core-fw`。
5. Dummy 当前关节零位、真实软限位、最大速度和电机使能链路。
6. Dummy 夹爪是否进入第一版范围，以及其可用控制接口。

在以上项目未确认前，不应让 PC 对真实 Dummy 进行无人工监控的自动运动。
