# Robotic-Arm / "灵犀"模拟 —— 项目交接文档

> 交接时间：2026-08-09
> 面向对象：接手本项目的开发者或 AI Agent
> 本文档中的每条结论都标注了依据文件路径。**标注为「未验证」的部分不要当作事实使用。**

---

## 0. 30 秒速览

这个仓库不是一个单体项目，而是**一个硬件项目 + 一个软件项目 + 五份 vendored 上游资产**的集合体，目标是做低成本主从式手术机器人训练平台（详见 `项目完整技术文档.txt`）。

当前真实状态：

| 部分 | 状态 | 一句话 |
|---|---|---|
| `windows_sim/` | **成熟可用**，92 测试全绿 | 纯离线主从遥操作数字孪生，是当前唯一工程质量达标的模块 |
| `rst-control-fw/` | **约 25%（板级 bring-up）** | 能点灯读编码器，但**没有任何控制环**，不是电机控制器 |
| `simple-cli/`、`robot-viewer/` | 能跑但粗糙 | 三份复制粘贴的串口探测逻辑，`robot_viewer.py` 有安全隐患 |
| `Moveit_ws-main/`、`ros2/`、`firmware/`、`OpenRST-main/`、`esp32-iot/` | vendored 上游 | **勿修改**；只有两个 URDF 文件被实际使用 |

**最需要立刻知道的三件事：**
1. 整个仓库**不在 git 版本控制下**（`git rev-parse` 报 not a git repository），且 `windows_sim/runs/` 已累积 118 个目录 / 422 MB 产物。
2. `robot-viewer/robot_viewer.py` 这个"查看器"在连接时会发送 `!START`，**会上电使能全部 6 个电机**，退出时不发 `!DISABLE`。
3. `rst-control-fw` 的核心控制函数 `RST_ControlLoop20kHz()` 是空的，且**从未被调用**；同时没有电流限幅、没有超时保护、没有看门狗。

---

## 1. 项目用途与完成度

### 1.1 用途
基于开源硬件搭建主从式手术机器人技能训练平台（"手术机器人领域的飞行模拟器"）。目标成本 < 6000 元，对标达芬奇 SimNow / RoSS 等数十万美元级模拟器。依据：`项目完整技术文档.txt` 第 98-141 行。

系统组成（`项目完整技术文档.txt` 第 146-174 行）：
- **从臂**：Dummy 六轴机械臂（稚晖君开源方案复刻），REF 板 STM32F405 + 6 块 CAN 驱动板
- **手术前端**：OpenRST 绳驱器械（俯仰 + 上夹 + 下夹，3 DOF）
- **主臂**：U-Arm（**尚未开始**，仅方案选型）
- **上位机**：自研控制台

### 1.2 完成度对照里程碑

`项目完整技术文档.txt` 第 481-504 行自述 M1/M2 已完成、M3 进行中。**代码层面核对结果：**

| 里程碑 | 文档自述 | 代码实际 |
|---|---|---|
| M1 Dummy 硬件复刻 | 已完成 | 硬件文件存在（`hardware/`、`bom/`）；固件是 vendored 上游，未验证是否与实机一致 |
| M2 RST 方案选型 | 已完成 | 与代码一致，`RST夹取端控制设计方案.txt` 完整 |
| M3 RST 固件开发 | 进行中 | **约 25%**，仅板级 bring-up，见 §5 |
| M4 RST 机械组装 | 待开始 | 无证据 |
| M5 Dummy+RST 集成 | 待开始 | 无证据 |
| M6 主从遥操作 | 待开始 | **`windows_sim/` 实际上已在纯仿真层面完成了这一项**（见 §4） |
| M7 训练平台化 | 待开始 | `windows_sim/sim/recorder.py` 提供了数据记录基础，训练任务/评估算法均无 |

**注意文档与代码脱节**：文档把 `windows_sim` 完全没提（文档 V2.0 日期 2026-08-05，`windows_sim` 最后活动 2026-08-08）。`项目完整技术文档.txt` 第 538-547 行的"相关文件索引"缺 `windows_sim/`。**接手后应先更新这份文档。**

---

## 2. 技术栈与工程结构

```
E:\Robotic-Arm\
├── windows_sim/          ★ 自研，Python 3.13 + NumPy + SciPy + Matplotlib(TkAgg)
├── rst-control-fw/       ★ 自研，STM32F103ZET6，CubeMX + MDK-ARM (ARMCC V5.06)
├── simple-cli/           ★ 自研，Python + pyserial (+PyQt5 一处)
├── robot-viewer/         ★ 自研，Python + matplotlib/ursina
├── hardware/ bom/ 3d-model/   ★ 自研硬件设计与 BOM
│
├── Moveit_ws-main/       ○ vendored ROS2/MoveIt 工作区（372 文件，含已提交 build 产物）
├── ros2/                 ○ vendored，Moveit_ws-main 的更旧子集，死代码
├── firmware/             ○ vendored Dummy 固件（ref-core / 42motor / 35motor）
├── OpenRST-main/         ○ vendored OpenRST 学术开源项目（ROS1）
├── esp32-iot/            ○ vendored Mongoose 示例（2851 文件，几乎全是无关示例）
│
├── 项目完整技术文档.txt    ★ 总体设计（V2.0）
├── RST夹取端控制设计方案.txt ★ RST 控制设计（V2.0）
└── openrst_paper.txt      ○ 论文文本
```

★ = 自研，可改 ｜ ○ = vendored 上游，**勿修改**

### 2.1 缺失的工程基础设施（重要）
- ❌ **无 git**：`git rev-parse` 失败。无历史、无分支、无法回滚。
- ❌ 无 `requirements.txt` / `pyproject.toml` / `setup.py`
- ❌ 无根 `.gitignore`；`__pycache__/`、`windows_sim/runs/`（422 MB）、`MDK-ARM/*/`(构建产物) 全部裸露
- ❌ 无 CI
- ⚠️ `.vscode/settings.json` 只有一行，把 cmake 指向 `firmware/dummy-35motor-fw`（与当前工作流无关的 vendored 目录）

### 2.2 已验证的运行环境
```
Python 3.13.7 / numpy 2.4.3 / scipy 1.17.1 / matplotlib 3.10.8
```
（我实际执行确认）

---

## 3. 核心模块与入口文件

### 3.1 唯一活跃的软件入口
| 入口 | 命令 | 说明 |
|---|---|---|
| `windows_sim/run_sim.py` | `python windows_sim\run_sim.py` | 主仿真器，GUI / headless 两种模式 |
| `windows_sim/validate_kinematics.py` | `python windows_sim\validate_kinematics.py --samples 1000` | FK→IK→FK 闭环验收 |

### 3.2 windows_sim 模块职责（全部位于 `windows_sim/sim/`）
| 文件 | 职责 |
|---|---|
| `urdf_model.py` | 严格 URDF 解析器（纯 `xml.etree`，不依赖 ROS）。`parse_urdf` / `chain()` |
| `kinematics.py` | `SerialKinematics`：FK、`forward_all`、解析几何 Jacobian、数值 Jacobian 交叉校验 |
| `hardware_mapping.py` | **坐标约定单一真源**：`SAFE_JOINT_LIMITS_RAD`、`ROS_TO_HARDWARE_OFFSET_RAD`、`ROS_TO_HARDWARE_DIRECTION` |
| `ik_solver.py` | `BoundedIKSolver`：有界 SciPy `least_squares` + warm start，控制期 `max_nfev=15`，冷启动 `bootstrap_max_nfev=300` + 12 多起点 |
| `teleop_mapper.py` | `TeleopMapper`（相对 SE(3) 映射，SO(3) log/exp，不用欧拉角相减）+ `TeleopSafetyStateMachine`（10 位故障掩码） |
| `motion_filter.py` | `OneEuroPoseFilter`（位置+四元数）、`PoseRateLimiter`（离散制动曲线限速） |
| `mock_plant.py` | `MockJointPlant`：jerk 受限一阶伺服 + 故障注入（延迟/掉包/噪声/冻结/卡死） |
| `openrst_model.py` | `IdealOpenRSTModel`：**理想** pitch/yaw/grasp，明确不含绳驱/摩擦/回差/电机动力学 |
| `scenario.py` | `ScenarioPlayer`：keyframes / parametric / faults 三类脚本 |
| `recorder.py` | 流式 CSV + `report.json`，蓄水池采样算分位数（soak 测试不涨内存） |
| `viewer.py` | Matplotlib 3D GUI，局部 blit 优化，60 Hz 目标渲染 |
| `signal_analysis.py` | `MultiToneAnalyzer` 频域幅值/相位估计（**我未读源码**，仅确认被 tremor 场景使用） |

### 3.3 固件入口
| 文件 | 说明 |
|---|---|
| `rst-control-fw/Core/Src/main.c` | **实际编译的主程序**。`while(1)` 里只有 LED 心跳 + 按键扫描 |
| `rst-control-fw/Core/Src/app_main.c` | ⚠️ **孤儿死代码**：不在任何构建清单里，且引用了不存在的 `hcan1`（`app_main.c:115`，实际是 `hcan`），加进工程会立即编译失败。**建议删除** |
| `rst-control-fw/Core/Src/debug_console.c` | 11 条命令的交互式调试 shell |
| `rst-control-fw/Core/Src/motor_driver.c` | TB6612 驱动层，4 个函数完整实现 |

### 3.4 上位机 CLI 入口
| 文件 | 质量 |
|---|---|
| `simple-cli/dummy_port_scanner.py` | **最佳**：唯一正确使用 VID/PID 检测，只读安全 |
| `simple-cli/streaming_control.py` | 功能最完整：50 Hz 键盘 jog，JOINT/CARTESIAN 双模式。仅 Windows（模块级 `ctypes.windll`） |
| `simple-cli/simple-cli.py` | 可用但粗糙。注意文件名带连字符，无法 `import` |
| `simple-cli/chatgpt_gui.py` | **不可用**：与 ChatGPT 无关（是 MPU6050 曲线 GUI），依赖固件不存在的 `#GETMPU` 命令 |
| `robot-viewer/robot_viewer.py` | ⚠️ **有安全隐患**，见 §6.1 |
| `robot-viewer/fk_solver.py` | 半成品：URDF 数值手抄硬编码，`MESH_FILES` + `get_link_transforms()` 是 Ursina 时代死代码 |
| `robot-viewer/test_render.py` | 一次性 ursina 冒烟脚本，可删 |

---

## 4. 数据流与模块关系

### 4.1 windows_sim 控制流（每周期 100 Hz，`run_sim.py::SimulationApp._step`，第 809 行）

```
虚拟主手 (GUI 滑块 100Hz 心跳 / ScenarioPlayer)
   │  ScenarioSample{pose, grasp, deadman, clutch, faults}
   ▼
_master_state()  → MasterState{timestamp, sequence, validity_flags}
   ▼
TeleopSafetyStateMachine.update_master()   ← feedback_fresh / tracking_ok
   │  DISABLED / READY / TELEOP / HOLD / FAULT
   ▼
[clutch?] ─是→ pose_filter.reset() + mapper.capture() + rate_limiter.reset()
   │否
   ▼
OneEuroPoseFilter.filter()      ← 震颤抑制
   ▼
TeleopMapper.map_pose()          ← 相对 SE(3)，translation_scale=0.3 / rotation_scale=0.5
   ▼
PoseRateLimiter.update()         ← 线/角 速度+加速度限幅
   ▼
BoundedIKSolver.solve()          ← warm start = 上一安全目标
   ▼
关节目标速度整形 (joint_target_scale)
   ▼
MockJointPlant.command() → .step() → .feedback()
   ▼
IdealOpenRSTModel.forward(actual_flange)
   ▼
SimulationRecorder.record()  →  runs/<ts>/teleop_samples.csv + report.json
   └→ _update_snapshot() (按 render_rate_hz 降频) → viewer
```

关键设计（`windows_sim/README.md` 第 49-58 行 + 代码核对）：
- 内部统一 **米 / 弧度 / 四元数 xyzw**；GUI 才显示角度
- `Clutch` 释放后在**当前主从位姿重新捕获**参考，不会跳回旧目标（`teleop_mapper.py:155-157`）
- IK 失败 → 保持上一安全目标 → 进 HOLD（`ik_solver.py:258-260`）
- 故障清除后必须**新鲜有效样本 + 重新 rearm** 才能恢复，不自动续动（`teleop_mapper.py:345-350`）

### 4.2 上游资产的耦合面（只有 3 处，都很窄）
1. `windows_sim/config.json` → `../Moveit_ws-main/dummy-ros2_description/urdf/dummy.urdf` 和 `../OpenRST-main/URDF/openrst_description/urdf/openrst.urdf`（**只读 joint 几何**，不加载 mesh）
2. `windows_sim/sim/hardware_mapping.py` → `dummy.urdf` 的关节命名，有断言保护（`kinematics.py:345`）
3. `simple-cli/`、`robot-viewer/` → `firmware/dummy-ref-core-fw/UserApp/protocols/ascii_protocol.cpp` 的 ASCII 命令字契约

**没有数据库，没有 Web 后端，没有网络接口。** "前端/后端/接口"在本项目中的对应物是：GUI（`sim/viewer.py`）↔ 控制线程（`SimulationApp`）↔ CSV/JSON 文件（`sim/recorder.py`）。

### 4.3 ASCII 串口协议（Dummy，vendored 固件契约）
子 Agent 已逐条核对 `ascii_protocol.cpp`：
```
!START / !DISABLE / !STOP / !HOME / !CALIBRATION / !RESET
#GETJPOS            → ok <6 个关节角>
#GETLPOS            → ok X Y Z A B C
#CMDMODE 1|2|3|4    → 2 = COMMAND_TARGET_POINT_INTERRUPTABLE
>j1,...,j6,speed    → 关节目标（dummy_robot.cpp:440）
@x,y,z,a,b,c,speed  → 笛卡尔目标，固件内建 IK（dummy_robot.cpp:467）
#SET_DCE_KP/KI/KD <node> <val>
#REBOOT <node>
```
⚠️ 上游 bug（勿擅改但需知晓）：节点校验用位与 `node >= 1 & node <= 6` 而非 `&&`（`ascii_protocol.cpp:58/70/82/93`）。

### 4.4 RST 串口协议（设计中，**固件未实现**）
`RST夹取端控制设计方案.txt` 第 238-267 行规定 `P<0-255>U<0-255>L<0-255>\n`、`CALIB/STOP/ENABLE/DISABLE/PING`。子 Agent 对这些关键字做全仓库检索：**零命中**。

---

## 5. 已完成 / 未完成 / 可能有 bug

### 5.1 ✅ 已完成且已验证（我实际执行）

**`windows_sim` 全部测试通过：**
```
python -m unittest discover -s windows_sim\tests -v
→ Ran 92 tests in 13.346s  OK
```

**circle 场景（固定步长快速模式）：**
```
ik_success_rate = 1.0 (1900 attempts)
position_error_rms_m = 0.000641   position_error_max_m = 0.000716
joint_limit_violation_count = 0   dropped_plant_commands = 0
state_sample_counts = {READY: 99, TELEOP: 1900, HOLD: 1}
```

**运动学验收（200 样本 FK→IK→FK）：**
```
success_rate = 1.0        skipped_singular_samples = 0
maximum_position_error_m = 3.22e-05      (<0.1mm ✓)
maximum_orientation_error_rad = 9.75e-06 (<0.05° ✓)
solve_time_p50_s = 0.0139   solve_time_p99_s = 0.1716
```
⚠️ p99 = 172ms 是**冷启动**路径（无 warm start 时走 `bootstrap_max_nfev=300` + 12 多起点，`ik_solver.py:184-194`），不是控制期路径。控制期用 `max_nfev=15`。

**tremor 场景（震颤抑制）：**
```
intentional_amplitude_loss_percent = 4.71   (<5% ✓)
tremor_filter_attenuation_db = 16.04        (>15dB ✓)
actual_tremor_attenuation_db = 53.44
filter_intentional_amplitude_pass = True
filter_tremor_attenuation_pass = True
```

**fault_injection 场景（13 类故障 + 恢复）：**
```
ik_success_rate = 0.9991
state_sample_counts = {READY:99, TELEOP:2249, HOLD:602, FAULT:50}
fault_reason 覆盖 10 类：input timed out / deadman released / feedback timed out /
  tracking error / rearm required / out-of-order timestamp / invalid input /
  IK failed / injected fatal fault
scenario_finished = True    joint_limit_violation_count = 0
```

**真实墙钟 10 秒实时性：**
```
cycle_period_p50_s = 0.01002    cycle_period_p99_s = 0.01041
control_cycle_p99_under_20ms = True   deadline_miss_count = 1
```
→ 100 Hz 控制环在 Windows 上确实跑住了。

### 5.2 ❌ 未完成

**RST 固件（`rst-control-fw/`），子 Agent 报告，我未独立复核每一行：**
- `RST_ControlLoop20kHz()`（`main.c:278`）函数体只有 `(void)m;` + TODO 注释，**且全仓库无调用点**
- `RST_Loop1kHz()`（`main.c:273`）函数体为空
- 5 kHz 速度环在代码和 `.ioc` 配置中都不存在
- **没有任何定时器中断被使能**（`.ioc` 的 NVIC 段无 `TIMx_IRQn`）→ 20k/5k/1k 三层控制环在硬件配置层面也不存在
- ADC **从未启动**：全仓库无 `HAL_ADC_Start` / `HAL_ADC_Start_DMA`，且 `ContinuousConvMode = DISABLE` + 软件触发从不触发 → `current_ma` 恒为 0
- 归零/标定状态机不存在：`homing_step`、`homing_stall_cnt` 从未被赋值；所有电机永久停留 `STATE_NO_CALIB`
- PID：结构体、增益初值、在线调参命令都有，但**没有一行代码用这些增益做运算**
- 指定串口协议（`P/U/L/CALIB/PING/...`）零实现
- CAN：只有 Init + Start，无滤波器配置、无 `HAL_CAN_ActivateNotification` → 接收中断永不触发
- EEPROM 参数持久化：仅注释占位

**windows_sim 的边界（`windows_sim/README.md` 第 69-73 行，代码一致）：**
- 无串口层，不与真机通信（`report.json` 的 `serial_access: False` 由 `tests/test_integration.py` 断言）
- OpenRST **pitch/yaw 恒为 0**（`run_sim.py:952` 硬编码 `set_command(0.0, 0.0, master.grasp)`），只驱动 grasp
- 不模拟绳驱、摩擦、回差、电机动力学
- 不能证明实机精度、串口闭环、MoveIt Servo、ROS QoS、Windows 硬实时、临床安全

**完全未开始：**
- 主臂（U-Arm）—— 零代码
- 训练任务模块（夹针/走线/打结）
- 技能评估算法（GEARS 类）
- 数据回放

### 5.3 🐛 Bug 与风险清单

#### 🔴 P0 —— 安全相关

| # | 位置 | 问题 |
|---|---|---|
| B1 | `robot-viewer/robot_viewer.py:145` | "查看器"连接时发 `#CMDMODE 2` + `!START`，**使能全部 6 个电机**；`stop()` 只 `close()` 串口，**不发 `!DISABLE`**，退出后电机仍使能。`windows_sim/README.md:72-73` 明确警告过这一点 |
| B2 | `rst-control-fw/Core/Src/debug_console.c:279,280,403` | **ISR 内调用 `HAL_Delay()`**。USART1 抢占优先级 0，SysTick 15 → SysTick 无法抢占 → `HAL_GetTick()` 冻结 → 死循环。**输入 `led 1 blink` 或 `reboot` 会 100% 固件挂死**，且 `reboot` 连复位都执行不到 |
| B3 | `rst-control-fw` 全局 | **完全没有电流限幅**（ADC 未启动 + 无比较逻辑 + 无 `CUR_LIMIT_MA` 常量）。用户可用 `pwm 0 1000` 直接给 100% 占空比，堵转时唯一保护是 TB6612 热关断 |
| B4 | `rst-control-fw` 全局 | **无超时保护 / 无看门狗 / 无失效安全**。`.ioc` 无 IWDG/WWDG；`Motor_SetPWM` 设定值无限期保持 → 上位机断线/串口拔掉/ISR 死锁时电机持续转动。按键急停未实现（`main.c:161-162` 只 `printf`） |
| B5 | `rst-control-fw/Core/Src/main.c:303-308` | `Error_Handler` 静默变砖：`__disable_irq()` + `while(1)`，**不关闭 PWM**、不置方向脚 coast、无任何指示。20+ 处 HAL 失败会跳进来 |
| B6 | `rst-control-fw/Core/Src/debug_console.c:150-158` | `cmd_line` 处理后不清空 → 收到裸回车会**重复执行上一条命令**。对 `pwm 0 1000` 意味着误触回车即重放电机指令 |

#### 🟠 P1 —— 功能正确性

| # | 位置 | 问题 |
|---|---|---|
| B7 | `rst-control-fw/Core/Src/adc.c:79` | Rank3 只改 Rank 没改 Channel，仍是 `ADC_CHANNEL_3` → **PA5（上夹电流）永远采不到**，PA3 被采两次。`.ioc` 里也是错的（不是笔误） |
| B8 | `rst-control-fw/Core/Src/can.c:41-45` | CAN 实际波特率 **562.5 kbps**（36MHz APB1 / (4×16)），不是设计的 1 Mbps。`CubeMX_配置指南.md:97` 误用 72MHz 算出 1.125M。`debug_console.c:237` 还向用户打印虚假的 "1Mbps"。**上位机按 1Mbps 配置将完全无法通信** |
| B9 | `rst-control-fw/Core/Src/tim.c:354-357` | TIM2 编码器落在 **PA0/PA1**，而 `PA0` 是 `CubeMX_配置指南.md:8,220` 明令禁用的 WK_UP 按键复用脚；文档要求的 `__HAL_AFIO_REMAP_TIM2_PARTIAL_1()`（PA15/PB3）**全仓库零调用** |
| B10 | `rst-control-fw/Core/Src/debug_console.c:344` | `int32_t cnt = (int32_t)(tim->CNT)` —— 16 位计数器当无符号 32 位读。**反转时 CNT 回卷 65535 会被读成 +9828°** 而不是 -0.15°；无圈数累加。这个 bug 会直接毁掉未来任何位置环 |
| B11 | `simple-cli/chatgpt_gui.py:89` | 依赖固件**不存在**的 `#GETMPU` 命令 → 图表永远空白。另有 L92 前缀硬切、L100-106 点数管理（判断 >120 却删到剩 20）两个 bug |
| B12 | `simple-cli/simple-cli.py:101` | `r.replace("ok","")` 缺 `count=1`，会删掉响应里所有 `ok` |
| B13 | `simple-cli/simple-cli.py:152` | `do_home` 发 `>0,-70,180,0,0,0`，而 `streaming_control.py:325` 和 `robot_viewer.py:37` 都是 `-73`。J2 不一致，且绕过了固件的 `!HOME` |
| B14 | `robot-viewer/fk_solver.py` | 缺 wrist→法兰段偏移（`L_WRIST=0.072` 未出现），且忽略 `dummy.urdf:120` `world_joint` 的 rpy 翻转 → **viewer 显示的 EE 位置与固件 `#GETLPOS` 有系统性偏差，两者不可互校** |

#### 🟡 P2 —— 结构性隐患

| # | 位置 | 问题 |
|---|---|---|
| B15 | 跨模块 | **关节限位有三套互不一致的数据，无单一真源**：`dummy.urdf`（J1 ±180, J2 -75~90, J3 ±90）、`streaming_control.py:55-58`（J1 ±170, J2 -73~90, J3 35~180）、`hardware_mapping.py:13-23`（J1 ±170, J2 -73~90, J3 -55~90）。`hardware_mapping.py:12` 注释称是"故意取交集"，但**无任何机制保证同步** |
| B16 | `rst-control-fw/Core/Src/gpio.c:54-79` | LED/按键/DIP/方向脚的手写配置位于 `MX_GPIO_Init()` **函数体内**，而 `USER CODE BEGIN 2` 在 `gpio.c:83`（函数之外）。配合 `.ioc: DeletePrevious=true`，**CubeMX 一次 Generate Code 就会清掉这 26 行** |
| B17 | `rst-control-fw/Core/Src/tim.c:50-52,252-254` | PWM 频率 = **1 kHz**（可听频段啸叫）。若真跑 20 kHz 电流环，控制频率是 PWM 的 20 倍，物理上无意义 → 定时器方案需重新设计 |
| B18 | `rst-control-fw/Core/Inc/rst_config.h` vs 代码 | 三处引脚不一致：Pitch PWM 文档说 PA8 实际 PE9；上夹编码器文档说 PB6/PB7 实际 PD12/PD13；下夹文档说 PA15/PB3 实际 PA0/PA1。**我无法判定哪一边匹配实物**（无原理图），必须用万用表确认 |
| B19 | `rst-control-fw/MDK-ARM/*.uvprojx:192` | `useUlib=0`，MicroLIB **未启用**，与 `CubeMX_配置指南.md:296-300` 矛盾。这使 `debug_console.c:99-102` 的 `vsnprintf` 返回值语义成为真实的栈越界隐患 |
| B20 | `rst-control-fw/Core/Src/main.c:54` | `g_rst` 未加 `volatile`，同时被主循环和 USART1 ISR 读写，编译优化 `-O3`。补上控制环后可能出现上位机改参数不生效 |
| B21 | `simple-cli/`、`robot-viewer/` | `find_port()` / `_drain()` / `_query()` / `list_ports()` 各复制 3-4 份，且只有 `dummy_port_scanner.py` 的 VID/PID 检测是正确的；其余硬编码 `["COM5","COM6"]` + 黑名单 `{"COM3","COM4"}` |
| B22 | 仓库根 | 无 git、无依赖清单、无 `.gitignore`；`windows_sim/runs/` 118 目录 / **422 MB** |

### 5.4 🔀 架构级不一致（最容易被忽略，务必读）

**`windows_sim` 的 OpenRST 模型与 RST 硬件的自由度语义不匹配：**

| | 自由度定义 |
|---|---|
| `windows_sim/sim/openrst_model.py` | pitch + **yaw** + grasp（对称双爪，单一 grasp 标量） |
| `RST夹取端控制设计方案.txt` §1.1 | pitch + **上夹** + **下夹**（两爪完全独立） |
| `OpenRST-main/.../openrst.urdf` | `joint_pitch` + `joint_finger_left` + `joint_finger_right` |

仿真里的 `yaw` **在硬件上没有对应物**；硬件的独立上/下夹在仿真里被折叠成一个对称 `grasp`。而 URDF 本身（finger_left/right 并联同级）反而更接近硬件。

**后果**：`windows_sim` 现在验证的 OpenRST 部分（且 pitch/yaw 恒为 0，只动 grasp）**无法直接迁移到 RST 硬件**。集成前必须先统一这一层的语义定义。这是 M5 的隐藏前置条件。

---

## 6. 如何启动、测试、构建、部署

### 6.1 windows_sim（唯一可立即运行的部分）

在工作区根目录 `E:\Robotic-Arm` 执行：

```powershell
# 交互 GUI（默认 READY 状态，需勾 Deadman 才动）
python windows_sim\run_sim.py

# 固定步长快速跑完整场景（不能用于实时性结论）
python windows_sim\run_sim.py --headless --no-realtime --scenario windows_sim\scenarios\circle.json

# 真实墙钟 10 秒实时性测试
python windows_sim\run_sim.py --headless --duration 10 --scenario windows_sim\scenarios\circle.json

# 关闭 One Euro 滤波，取原始基线
python windows_sim\run_sim.py --headless --no-realtime --no-filter --scenario windows_sim\scenarios\tremor.json

# 运动学验收
python windows_sim\validate_kinematics.py --samples 1000

# 60 分钟 soak（会真的跑一小时）
python windows_sim\run_sim.py --headless --scenario windows_sim\scenarios\soak_60min.json

# 全部测试
python -m unittest discover -s windows_sim\tests -v
```

可用场景（`windows_sim/scenarios/`）：`axis_steps` / `circle` / `figure_eight` / `tremor` / `fault_injection` / `soak_60min`

产物：`windows_sim/runs/<时间戳>/{teleop_samples.csv, report.json}`

**读 report 时注意**：`control_cycle_p99_under_20ms` 只在真实墙钟模式评估；`--no-realtime` 时写为 `null`（`recorder.py:204-210`）。

**依赖安装**（无 requirements.txt，需手动）：
```powershell
pip install numpy scipy matplotlib
```

### 6.2 rst-control-fw 构建
- **只有一种构建方式**：MDK-ARM（Keil）。无 Makefile / CMakeLists / .cproject
- 工程：`rst-control-fw/MDK-ARM/rst-control-fw.uvprojx`
- 工具链：MDK-Lite 5.36 + ARMCC V5.06 update 7
- 上次构建成功：`Code=27468 RO=1472 RW=20 ZI=2684`，0 Error / 1 Warning
  - 那个 Warning 是真问题：`usart.c(125): Console_RxCallback declared implicitly`（`usart.c` 没 include `debug_console.h`）
- ⚠️ 重新生成 CubeMX 代码前必读 §5.3 B16

### 6.3 上位机 CLI
```powershell
python simple-cli\dummy_port_scanner.py          # 安全：只探测，不发运动命令
python simple-cli\simple-cli.py -l               # 列端口
python simple-cli\streaming_control.py -p COM5   # 键盘 jog（会使能电机）
```
⚠️ `simple-cli/README.md` 已过期（描述 macOS + `simple_cli.py` 下划线文件名）。

### 6.4 ROS2 / MoveIt
**当前工作流不使用。** `Moveit_ws-main/` 和 `ros2/` 是 vendored 上游，自研代码中零 `rclpy`/`rclcpp` 引用。唯一实际依赖是两个 URDF 的静态 XML。

⚠️ 若将来要启用：`dummy.urdf` 的 mesh 是**硬编码 Linux 绝对路径**（`file:///home/hata_ros/apps/dummy_ws/install/...`），Windows 必然失效；`openrst.urdf` 用 `package://`，无 ROS 环境无法解析。对 `windows_sim` 无影响（只读 joint 几何）。

### 6.5 部署
**当前没有部署流程。** 无打包、无安装脚本、无容器。`windows_sim` 是 Windows 本地直接跑源码。

---

## 7. 当前最应该优先处理的问题

按「风险 × 阻塞程度」排序：

### P0-1　给仓库上 git + 加 .gitignore
**理由**：422 MB 产物、无历史、无法回滚。这是所有后续工作的前置条件，成本 10 分钟。
```
.gitignore 至少应包含：
__pycache__/  *.pyc  windows_sim/runs/  rst-control-fw/MDK-ARM/rst-control-fw/
rst-control-fw/MDK-ARM/*.uvguix.*  *.axf  *.hex  *.map
```
同时清理 `windows_sim/runs/` 旧产物（118 个目录里只有最近几个有参考价值）。

### P0-2　修掉 robot_viewer.py 的 `!START`
**理由**：一个命名为"查看器"的工具会使能真机电机，且退出不失能。这是最容易在实机调试时出事的地方。
**改法**：`robot_viewer.py:145` 只发 `#GETJPOS` 轮询，删掉 `#CMDMODE 2` 和 `!START`；`stop()` 补 `!DISABLE`。参考 `windows_sim/README.md:72-73` 已写明的约束。

### P0-3　修 RST 固件的死锁与失效安全（不需要动 .ioc）
按此顺序，都是纯软件改动：
1. `Console_RxCallback` 改为**只入队**，解析和输出移到主循环 → 同时解决 B2 死锁和 B25 ISR 阻塞
2. 删除 ISR 路径上所有 `HAL_Delay`
3. `cmd_line` 用后清零（防命令重放，B6）
4. `Error_Handler` 先 `Motor_Sleep()` ×3 再挂起，并点错误 LED（B5）
5. 删除孤儿文件 `Core/Src/app_main.c`（B-§3.3）
6. 把 `gpio.c` 的手写 GPIO 配置搬到 `USER CODE BEGIN 2` 之后的独立函数（B16）—— **这一步必须在任何 CubeMX 再生成之前完成**

### P1-1　用万用表/原理图确认 RST 实际接线
**理由**：§5.3 B18 的三处引脚不一致（PE9 vs PA8、PD12/13 vs PB6/7、PA0/1 vs PA15/PB3）我**无法从代码判定哪边对**。这个不定下来，后面写控制环等于在猜。同时确认 INA180 电路以定 ADC 采样时间。

### P1-2　修 .ioc 层面的配置错误（一次性做完，避免反复再生成）
- ADC Rank3 → `ADC_CHANNEL_5`（B7）
- ADC 采样时间 1.5 → 239.5 cycles
- CAN 预分频按 36 MHz 重算到真正的 1 Mbps（B8）
- TIM2 编码器移到 PA15/PB3 并加 `__HAL_AFIO_REMAP_TIM2_PARTIAL_1()`（B9）
- **新增一个定时器中断作为控制环时基**（当前完全没有）
- 加 IWDG
- 重定 PWM 频率：建议 PWM ≥ 16 kHz，控制环 ≤ PWM/8（B17）

### P1-3　统一关节限位真源
**理由**：B15 的三套数据是最有可能在实机上造成撞限位的结构性问题。
**改法**：以 `windows_sim/sim/hardware_mapping.py` 为单一真源（它已经是唯一带注释说明和转换函数的地方），让 `streaming_control.py` 从它导入，并加一个测试断言它与 `dummy.urdf` 的交集关系成立。

### P2-1　统一 OpenRST 自由度语义
**理由**：§5.4。不解决这个，`windows_sim` 的 OpenRST 部分无法迁移到硬件，M5 会卡住。
**建议**：把仿真模型改成 pitch + upper_jaw + lower_jaw（与硬件和 URDF 一致），`grasp` 降级为一个便捷映射函数。

### P2-2　抽公共 `dummy_link.py`
把 `simple-cli/` 和 `robot-viewer/` 里复制 3-4 份的端口检测/探活/parse 收敛为一份，VID/PID 逻辑取 `dummy_port_scanner.py` 那份（唯一正确的），并提供一条**禁止 `!START`** 的只读路径。

---

## 8. 后续开发路线图

### 阶段 A：工程基线（1-2 天）
- [ ] git init + .gitignore + 清理 runs/
- [ ] `requirements.txt`（`numpy`、`scipy`、`matplotlib`、`pyserial`；pin 版本）
- [ ] 更新 `项目完整技术文档.txt`，补入 `windows_sim/`（当前完全没提）
- [ ] 修 `simple-cli/README.md`（已过期）
- [ ] 删死代码：`rst-control-fw/Core/Src/app_main.c`、`robot-viewer/test_render.py`、`fk_solver.py` 的 `MESH_FILES`/`get_link_transforms`

### 阶段 B：安全加固（2-3 天）
- [ ] P0-2 robot_viewer `!START`
- [ ] P0-3 RST 固件死锁 + Error_Handler + gpio.c 搬迁
- [ ] P1-3 关节限位单一真源 + 断言测试

### 阶段 C：RST 固件补齐核心（2-3 周，本项目当前主线 M3）
- [ ] 确认实物接线（P1-1）
- [ ] 一次性修完 .ioc（P1-2）
- [ ] 编码器 32 位扩展计数（修 B10），示波器验证 A/B 相位差 90°
- [ ] 启动 ADC DMA，校准电流标度（空载 0.1~0.3 A）
- [ ] **电流限幅优先于 PID 实现**（正常 1.0 A / 标定 0.3 A / 上限 2.0 A）
- [ ] 位置环 + 速度环串级 PID，参数存 EEPROM
- [ ] 上电堵转找零标定状态机（2~3 s，LED 指示）
- [ ] 堵转检测（超限 500 ms → 降 50% 维持电流）
- [ ] 指令超时保护（500 ms 保持 / 2 s 停止）+ IWDG
- [ ] 实现 `P<>U<>L<>` 协议解析器（与调试 shell 并存或分模式）
- [ ] 验收：静态 ±1°、阶跃 90% 到位 <500 ms、指令到动作 <50 ms

### 阶段 D：RST 机械 + 夹持验证（M4）
- [ ] 3D 打印 OpenRST 结构、绳驱装配、张紧
- [ ] 回程差测量与补偿标定
- [ ] 夹针测试

### 阶段 E：集成（M5）
- [ ] **先统一 OpenRST 自由度语义**（P2-1）
- [ ] J6 法兰适配件
- [ ] 抽公共 `dummy_link.py`（P2-2）
- [ ] 上位机统一控制台：同时管 Dummy + RST 两个串口
- [ ] `windows_sim` 的只读数字影子适配器 —— **必须独立实现，只允许 `#GETJPOS`**，不要复用现有 viewer 连接逻辑（`windows_sim/README.md:72-73`）

### 阶段 F：主从遥操作（M6）
- [ ] U-Arm 主臂搭建（当前零代码）
- [ ] 主从映射：`windows_sim/sim/teleop_mapper.py` 已实现相对 SE(3) 映射，可直接复用
- [ ] 端到端延迟预算验证 < 100 ms

### 阶段 G：训练平台化（M7）
- [ ] 数据记录与回放（`sim/recorder.py` 是基础，回放未实现）
- [ ] 标准训练任务：夹针 / 走线 / 打结 / 精细搬运
- [ ] 技能评估算法（可参考 GEARS 体系，`项目完整技术文档.txt:477`）

---

## 9. 我未验证 / 无法验证的部分（不要当事实用）

- **未编译任何固件**：无 `arm-none-eabi` 工具链、无 Keil。§5.2 和 §5.3 中关于 `rst-control-fw` 的结论全部来自子 Agent 的静态读码（引用了具体 file:line），我未逐行独立复核。
- **未连接任何真机 / COM 口**。所有串口协议结论是静态核对，`>`/`@` 的实际运动响应未验证。
- **无法判定 RST 实物接线**（无原理图/PCB 源文件）→ B18 只能说"代码与文档不一致"，不能断言哪边对。
- **无法确认 `firmware/` 是否就是烧在实机上的版本**。若实机跑别的分支，§4.3 的协议核对需重做。
- **未 colcon build 任何 ROS 包**。
- **未读源码**：`windows_sim/sim/signal_analysis.py`、`windows_sim/validate_kinematics.py`（只运行了后者）、`windows_sim/tests/` 全部 11 个测试文件的具体内容（只确认 92 个测试通过）。
- **未展开**：`hardware/`、`bom/`、`3d-model/`、`bbs_backup/`、`esp32-iot/tool/`、`OpenRST-main/CAD Files/`、`Moveit_ws-main/doc/`。
- **未 diff** 两份 `openrst.urdf` 副本（`URDF/openrst_description/` 与 `Control software/openrst_control/urdf/`），也未 diff `ros2/dummy_ws` 与 `Moveit_ws-main` 的重合文件。
- **`fk_solver.py` 与固件 DH 参数的 11 mm 差值**（`L_BASE=0.109` vs URDF 的 `0.0825+0.0375=0.120`）是否确为坐标系原点差异，需实测或对照 CAD。
- **许可证兼容性未核对**。`Moveit_ws-main` 多个包标 `TODO: License declaration`，`OpenRST-main/LICENSE.txt` 与根 `LICENSE` 各自独立。若要分发需单独过一遍。

---

## 10. 下一步行动清单

按顺序执行，每项都可独立验证完成：

```
□  1. cd E:\Robotic-Arm && git init && 写 .gitignore && 首次 commit
      验证：git status 干净，runs/ 和 __pycache__/ 不在待提交列表
□  2. 清理 windows_sim\runs\（保留最近 3 个），写 requirements.txt（pin 版本）
      验证：pip install -r requirements.txt 后 92 测试仍全绿
□  3. 修 robot-viewer\robot_viewer.py:145 —— 删 !START / #CMDMODE 2，只留 #GETJPOS
      给 stop() 补 !DISABLE
      验证：grep -n "!START" robot-viewer\ 无命中
□  4. 删 rst-control-fw\Core\Src\app_main.c 和 robot-viewer\test_render.py
□  5. 把 rst-control-fw\Core\Src\gpio.c:54-79 的手写配置搬到新函数 RST_GPIO_Init()，
      放在 USER CODE BEGIN 2 之后，main.c 里调用
      验证：Keil 重编译 0 Error，LED/按键/DIP 功能不变
□  6. 修 rst-control-fw ISR 架构：Console_RxCallback 只入队，主循环解析
      删所有 ISR 路径上的 HAL_Delay，cmd_line 用后清零
      验证：串口输入 "led 1 blink" 和 "reboot" 不再挂死
□  7. 修 Error_Handler：先 Motor_Sleep()×3，再点错误 LED，再挂起
□  8. 给 usart.c 加 #include "debug_console.h"
      验证：编译 0 Warning
□  9. 【需硬件】用万用表/原理图确认 Pitch PWM、上夹编码器、下夹编码器的实际引脚
      产出：一份《RST 实物引脚确认表》，覆盖 rst_config.h 的注释
□ 10. 一次性修完 .ioc：ADC Rank3→CH5、采样时间→239.5、CAN 重算 1Mbps、
      TIM2→PA15/PB3+remap、新增控制环定时器中断、加 IWDG、PWM 频率重定
      验证：CubeMX 生成后 Keil 编译通过，且第 5 步的 GPIO 代码没被清掉
□ 11. 修编码器 32 位扩展计数（debug_console.c:344 及未来控制环）
      验证：手动反转电机，enc 命令读数为负值且连续
□ 12. 启动 ADC DMA，校准三路电流标度
      验证：空载读数 0.1~0.3 A，堵转读数明显上升；PA5 有独立读数
□ 13. 实现电流限幅（先于 PID）
      验证：pwm 0 1000 堵转时电流被钳在设定值，不再无限上升
□ 14. 统一关节限位真源：streaming_control.py 从 hardware_mapping.py 导入
      加测试断言 SAFE_JOINT_LIMITS ⊆ dummy.urdf 限位
□ 15. 统一 OpenRST 自由度语义：sim 模型改为 pitch+upper_jaw+lower_jaw
      验证：92 测试更新后全绿，report.json 字段名同步更新
□ 16. 更新 项目完整技术文档.txt：补入 windows_sim，修正 M3~M7 状态
□ 17. 抽 dummy_link.py 公共模块，收敛 4 份重复的端口检测逻辑
```

**给接手 AI 的建议起点**：先做 1-8（纯软件、无需硬件、可独立验证），这 8 项完成后仓库就从"能跑"变成"可维护"。第 9 项是硬件依赖的分水岭，在它之前不要写 RST 控制算法。
