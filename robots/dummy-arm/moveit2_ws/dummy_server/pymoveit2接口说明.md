# pymoveit2 接口说明

基于ROS 2动作与服务构建的MoveIt 2基础Python接口。

> 注意：MoveIt 2官方Python库`moveit_py`现已发布。相关公告参见[此处](https://picknik.ai/moveit/ros/python/google/2023/04/28/GSOC-MoveIt-2-Python-Bindings.html)。

<div align="center" class="tg-wrap">
<table>
<tbody>
  <tr>
    <td width="25%"><img width="100%" src="https://user-images.githubusercontent.com/22929099/147369355-5f1b33ef-2e18-4042-9ea3-cd85b1a78fa0.gif" alt="Animation of ex_joint_goal.py"/></td>
    <td width="25%"><img width="100%" src="https://user-images.githubusercontent.com/22929099/147369356-b8ad2f4c-1996-47ac-9bfb-7fccd243fd56.gif" alt="Animation of ex_pose_goal.py"/></td>
    <td width="25%"><img width="100%" src="https://user-images.githubusercontent.com/22929099/147369354-640831e2-4661-4f3d-8fc2-3e97d7766e1a.gif" alt="Animation of ex_gripper.py"/></td>
    <td width="25%"><img width="100%" src="https://user-images.githubusercontent.com/22929099/147374152-50128188-ab73-4d55-a537-b641325ce9c6.gif" alt="Animation of ex_servo.py"/></td>
  </tr>
  <tr>
    <td width="25%"><div align="center">关节目标</div></td>
    <td width="25%"><div align="center">位姿目标</div></td>
    <td width="25%"><div align="center">夹爪动作</div></td>
    <td width="25%"><div align="center">MoveIt 2 Servo</div></td>
  </tr>
</tbody>
</table>
</div>

## 使用说明

### 依赖项

使用本项目所需的核心依赖项如下。

- ROS 2 [Galactic](https://docs.ros.org/en/galactic/Installation.html)、[Humble](https://docs.ros.org/en/humble/Installation.html)或[Iron](https://docs.ros.org/en/iron/Installation.html)
- 与所选ROS 2发行版对应的[MoveIt 2](https://moveit.ros.org/install-moveit2/binary)

其余依赖项将在后续构建过程中通过[rosdep](https://wiki.ros.org/rosdep)自动安装。

### 构建

克隆本仓库，安装依赖项，并使用[colcon](https://colcon.readthedocs.io)进行构建。

```bash
# 将本仓库克隆至用户所需的ROS 2工作空间
git clone https://github.com/AndrejOrsula/pymoveit2.git
# 安装依赖项
rosdep install -y -r -i --rosdistro ${ROS_DISTRO} --from-paths .
# 构建
colcon build --merge-install --symlink-install --cmake-args "-DCMAKE_BUILD_TYPE=Release"
```

### 环境配置

在使用本软件包前，需完成ROS 2工作空间的环境配置。

```bash
source install/local_setup.bash
```

该命令支持从外部工作空间导入`pymoveit2`模块。

## 使用示例

为演示`pymoveit2`的用法，[examples](./examples)目录包含若干脚本以展示其基础功能。更多示例可参见[ign_moveit2_examples](https://github.com/AndrejOrsula/ign_moveit2_examples)仓库。

运行示例前，需完成MoveIt 2机器人控制环境的配置。例如，可使用[panda_ign_moveit2](https://github.com/AndrejOrsula/panda_ign_moveit2)仓库中的以下启动脚本之一。

```bash
# RViz（仿真）ROS 2控制
ros2 launch panda_moveit_config ex_fake_control.launch.py
# Gazebo（仿真）ROS 2控制
ros2 launch panda_moveit_config ex_ign_control.launch.py
```

环境就绪后，即可运行各示例脚本。

```bash
# 移动至指定关节构型
ros2 run pymoveit2 ex_joint_goal.py --ros-args -p joint_positions:="[1.57, -1.57, 0.0, -1.57, 0.0, 1.57, 0.7854]"
# 移动至笛卡儿位姿（关节空间或笛卡儿空间运动）
ros2 run pymoveit2 ex_pose_goal.py --ros-args -p position:="[0.25, 0.0, 1.0]" -p quat_xyzw:="[0.0, 0.0, 0.0, 1.0]" -p cartesian:=False
# 重复切换夹爪状态（或使用"open"/"close"动作）
ros2 run pymoveit2 ex_gripper.py --ros-args -p action:="toggle"
# 使用MoveIt 2 Servo使末端执行器做圆周运动的示例
ros2 run pymoveit2 ex_servo.py
# 向MoveIt 2规划场景添加基础几何碰撞体的示例
ros2 run pymoveit2 ex_collision_primitive.py --ros-args -p shape:="sphere" -p position:="[0.5, 0.0, 0.5]" -p dimensions:="[0.04]"
# 向MoveIt 2规划场景添加网格几何碰撞体的示例
ros2 run pymoveit2 ex_collision_mesh.py --ros-args -p action:="add" -p position:="[0.5, 0.0, 0.5]" -p quat_xyzw:="[0.0, 0.0, -0.707, 0.707]"
```

## 目录结构

本软件包采用如下目录结构。

```bash
.
├── examples/              # [目录] 演示`pymoveit2`用法的示例脚本
├── pymoveit2/             # [目录] ROS 2启动脚本
    ├── robots/            # [目录] 机器人预设配置（可从URDF/SRDF提取的数据）
    ├── gripper_command.py # 由GripperCommand控制的夹爪接口
    ├── moveit2_gripper.py # 由JointTrajectoryController控制的MoveIt 2夹爪接口
    ├── moveit2_servo.py   # 支持笛卡儿空间实时控制的MoveIt 2 Servo接口
    └── moveit2.py         # 支持轨迹规划与执行的MoveIt 2接口
├── CMakeLists.txt         # 支持Colcon的CMake构建脚本
└── package.xml            # ROS 2软件包元数据
```
