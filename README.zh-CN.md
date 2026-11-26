# jcheng-simulation

[English](README.md) | **简体中文**

JCHENG 生态的离线仿真被控对象：一个确定性的 mock 关节/扫描植物，以及一个基于
Gazebo Harmonic 的 ArmPi Ultra 简化模型 bringup，两者都限制在 ROS 域 43。它在开发
和 CI 期间充当厂商硬件世界的替身。它不打开设备、不加入域 0/41/42，也绝不向真实
系统层发送运动命令。

> 状态：**实验性**，截至 2026-11-26，v0.1.0，离线仿真部分验证。mock 与 Gazebo
> 后端已在 Jazzy/Harmonic 上通过离线运行，但这里没有任何硬件验证：几何是简化的
> 临时模型，移动底盘、第二个夹爪手指与外部相机尚未建模。
> 本文为英文主文档的中文对照；如有歧义，以 [README.md](README.md) 为准。

## 范围与边界

| 项 | 本仓库 |
|---|---|
| 层 | SIM（离线，位于 L0–L4 运行时依赖图之外） |
| 域 | **仅 43**。launch 拒绝其他任何 `ROS_DOMAIN_ID`。 |
| 输入 | Mock：`/sim/joint_command`（`sensor_msgs/JointState` 位置设定值）。Gazebo：`/sim/arm_controller/follow_joint_trajectory`、`/sim/gripper_controller/follow_joint_trajectory`。 |
| 输出 | `/sim/joint_states`、`/sim/scan`、`/sim/camera/image`、`/sim/camera/camera_info`、`/sim/truth/source`；Gazebo 还会发布 `/clock`。 |
| 硬件访问 | `none`（`capability.yaml`） |
| 拥有设备 | 无。没有 `/dev/*`、串口、CAN、GPIO 或相机设备。 |
| 运动授权 | 对真实硬件无。植物只做仿真，绝不是 `jcheng-system` 的 `motion_source`。 |
| 禁止 | 域 0/41/42、厂商话题、设备访问、真实运动、厂商网格、模型权重。 |

植物发布的每个 ROS 话题都是 `/clock` 或位于 `/sim/` 下。
`/sim/truth/source` 携带字面量 `simulated`；从本仓库读到的一切都是**仿真真值**，
不是测量值。mock 与 Gazebo 结果从不作为硬件验证报告。

### 清单说明

`capability-manifest.v1`（interfaces v0.1.0）把 `runtime.ros_domains` 钉死为
`[42]`，并要求 `safety.requires_lease: true`。本仓库是**离线植物**，因此有意声明
`ros_domains: [43]`、`requires_lease: false`、`safety.class: offline`。该偏差由
`tests/test_contract.py` 显式断言，并在 [ROADMAP.md](ROADMAP.md) 的 M3 中跟踪；
它不是静默的 schema 违规。

## 仓库结构

```text
jcheng-simulation/
├── capability.yaml                 # 离线清单；域 43
├── docs/                           # 架构、模型、失败模式、ADR
├── evidence/20261126_offline_validation/
├── scripts/check_repo_gate.sh
├── tests/                          # 契约、边界、植物、扫描、文档
└── ros2_ws/src/jcheng_simulation_bringup/
    ├── config/                     # 仿真、限位、控制器、ros_gz bridge
    ├── launch/sim.launch.py        # backend:=mock|gz，域守卫
    ├── urdf/jcheng_armpi_sim.urdf.xacro
    ├── worlds/jcheng_lab.sdf
    └── jcheng_simulation_bringup/  # 无 ROS 依赖的植物/扫描核心 + mock 节点
```

## 依赖

- **仿真主机：** ROS 2 Jazzy 与 Gazebo Sim（Harmonic，`gz sim` 8.x），用于 `gz`
  后端。主机是操作员笔记本/工作站，不是机器人。
- **Mock 后端：** 具有 `rclpy`、`sensor_msgs`、`std_msgs` 的 ROS 2；不需要 Gazebo。
- **Gazebo 后端软件包：** `ros_gz_sim`、`ros_gz_bridge`、`gz_ros2_control`、
  `joint_state_broadcaster`、`joint_trajectory_controller`、
  `robot_state_publisher`、`xacro`。
- **契约：** `jcheng-interfaces` `>=0.1,<0.2`，契约哈希
  `sha256:0b8d72ce…f24b42`。
- 不需要也不访问硬件。机器人上的 Humble 栈不被本仓库使用。

## 快速开始

```bash
cd jcheng-simulation
colcon build --base-paths ros2_ws/src --packages-select jcheng_simulation_bringup
source install/setup.bash
```

### Mock 后端（确定性，无 Gazebo）

```bash
ros2 launch jcheng_simulation_bringup sim.launch.py backend:=mock
```

在域 43 的另一个终端：

```bash
export ROS_DOMAIN_ID=43
ros2 topic list | grep /sim
ros2 topic echo /sim/truth/source --once          # data: simulated
ros2 topic pub --once /sim/joint_command sensor_msgs/msg/JointState \
  "{name: ['joint1','r_joint'], position: [0.5,-1.0]}"
ros2 topic echo /sim/joint_states --once
```

mock 植物会把设定值夹到关节限位内，以受限速度移动，并在命令中断 500 ms 后保持
最后目标。它以 10 Hz 发布 360 束合成扫描。

### Gazebo 后端（默认 headless）

```bash
ros2 launch jcheng_simulation_bringup sim.launch.py backend:=gz headless:=true
```

控制器 spawner 完成（约 8–12 秒墙钟时间）后，可通过仿真控制器 action 命令机械臂：

```bash
export ROS_DOMAIN_ID=43
ros2 action send_goal /sim/arm_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {joint_names: [joint1,joint2,joint3,joint4,joint5],
     points: [{positions: [0.3,0.2,-0.2,0.1,0.0],
               time_from_start: {sec: 2, nanosec: 0}}]}}"
```

GUI 运行传 `headless:=false`（CI 不使用）。launch 拒绝 `43` 以外的任何
`domain_id`；不要覆盖域。

## 测试

```bash
python3 -m pytest -q tests
bash scripts/check_repo_gate.sh
```

测试覆盖清单契约、域隔离、无硬件/厂商资产扫描、关节/扫描模型、YAML/URDF/控制器
限位一致性，以及文档集。

## 验证状态

| 声明 | 级别 | 结果 | 证据 |
|---|---|---|---|
| 契约、边界、域与单元测试 | L0/L1 | 通过 | `tests/` |
| 仓库 gate | L0 | 通过 | `scripts/check_repo_gate.sh` |
| URDF 展开与 `gz sdf -p` | L0 | 通过 | [证据](evidence/20261126_offline_validation/README.md) |
| mock 后端端到端 | L2 | 通过 | 同上 |
| Gazebo 后端端到端（headless） | L2 | 通过 | 同上 |
| 通过 JTC 的仿真关节轨迹 | L2 | 通过 | 同上 |
| 硬件验证 | L5 | **不适用** | 不存在硬件路径 |

Gazebo 运行发生在操作员主机的 Jazzy/Harmonic 上，不在机器人上。未命令任何硬件
运动。完整报告：[ACCEPTANCE.md](ACCEPTANCE.md)。

## 相关仓库

- `JCHENG-Robotics/jcheng-interfaces` — 契约 schema、哈希与证据记录 schema。
- `JCHENG-Robotics/jcheng-system` — 安全、控制权、运动与硬件桥；它也在域 43 上
  拥有场景运行器 `jcheng_testkit`。
- `JCHENG-Robotics/jcheng-perception` — 建议性感知；未来集成中会消费仿真传感器流。
- `JCHENG-Robotics/jcheng-ops` — 运维；与仿真无关。
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 为什么它是独立 SIM 层，以及如何
  保持在运行时图之外。

## 许可

**待定。** 在组织审查关闭前，本仓库有意不提供 `LICENSE`，与 `jcheng-interfaces`、
`jcheng-system`、`jcheng-perception`、`jcheng-ops` 和 `.github` 一致。见
[LICENSE-REVIEW.md](LICENSE-REVIEW.md)。
