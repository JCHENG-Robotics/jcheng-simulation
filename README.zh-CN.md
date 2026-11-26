# jcheng-simulation

[English](README.md) | **简体中文**

JCHENG 生态的离线仿真被控对象。它是一个**多机器人引擎**：一套实现、一个设备目录、两种后端。
每个设备由 `robots/<id>/robot.yaml` 描述；`robot.launch.py robot:=<id>` 依据 profile 构建
确定性 mock 植物或 Gazebo Harmonic 植物。一切都限制在 ROS 域 43。不打开设备、不加入域
0/41/42，也绝不向真实系统层发送运动命令。

> 状态：**实验性**，截至 2026-11-26，v0.1.0，离线仿真部分验证。mock 与 Gazebo 后端已在
> Jazzy/Harmonic 上通过离线运行，但这里没有任何硬件验证：几何是简化的临时模型，没有第二个
> 夹爪手指、深度流或移动底盘。目录中已有两个机器人；新增设备只需一个目录加一份 profile ——
> 见 [docs/MULTI_ROBOT.md](docs/MULTI_ROBOT.md)。
> 本文为英文主文档的中文对照；如有歧义，以 [README.md](README.md) 为准。

## 范围与边界

| 项 | 本仓库 |
|---|---|
| 层 | SIM（离线，位于 L0–L4 运行时依赖图之外） |
| 域 | **仅 43**。每个 launch 拒绝其他任何 `ROS_DOMAIN_ID`。 |
| 输入 | Mock：profile 的 `joint_command`（`sensor_msgs/JointState` 位置设定值）。Gazebo：`/sim/<controller>/follow_joint_trajectory`。 |
| 输出 | `/sim/joint_states`、profile 声明的传感器话题（ArmPi：`/sim/scan`、`/sim/camera/image`、`/sim/camera/camera_info`）、`/sim/truth/source`；Gazebo 还会发布 `/clock`。 |
| 硬件访问 | `none`（`capability.yaml`） |
| 拥有设备 | 无。没有 `/dev/*`、串口、CAN、GPIO 或相机设备。 |
| 运动授权 | 对真实硬件无。植物只做仿真，绝不是 `jcheng-system` 的 `motion_source`。 |
| 禁止 | 域 0/41/42、厂商话题、设备访问、真实运动、厂商网格、模型权重。 |

植物的每个**数据**话题都是 `/clock` 或位于 `/sim/` 下；标准 ROS 话题 `/tf`、
`/tf_static`、`/rosout`、`/parameter_events` 与 `/robot_description` 也会存在。
`/sim/truth/source` 携带字面量 `simulated`；从本仓库读到的一切都是**仿真真值**，
不是测量值。mock 与 Gazebo 结果从不作为硬件验证报告。

## 机器人目录

| Id | 模型 | 后端 | 命令关节 | 传感器 | 用途 |
|---|---|---|---|---|---|
| `armpi_ultra` | ArmPi Ultra 简化 5 自由度模型 | mock、gz | `joint1…joint5`、`r_joint` | LiDAR、腕部相机 | 生态植物：扫描、相机、限位、真值 |
| `gate2_arm` | 迁移的 2 自由度 Gate-2 机械臂 | mock、gz | `joint1`、`joint2` | 无 | `ros2_control` 接线、控制器配置、fail-closed 启动 |
| `piper_x` | Piper X 6 自由度 + 平行夹爪（外部 MIT URDF） | mock、gz | `joint1…joint6`、`gripper` | 无 | 外部资产示例；真实厂商描述保留在仓库外 |

`piper_x` 需要已物化的资产包（`JCHENG_ASSET_ROOT`）及其 ament prefix；缺失时它仍会被
目录收录并通过校验，但拒绝启动。见 [docs/robots/piper_x/](docs/robots/piper_x/README.md)。

`/sim` 命名、`jcheng-sim` Gazebo 分区与域 43 对每个机器人都适用。**一次只运行一个
植物**：每个植物都占用 `/sim/controller_manager` 及其控制器 action。Gazebo 后端发布
`/sim/truth/source`，mock 后端也发布。

### 新增设备

1. 新建 `ros2_ws/src/jcheng_simulation_robots/robots/<id>/`，放入 `robot.yaml`、纯文本
   URDF 和控制器 YAML。
2. 让 `model.urdf` 指向 URDF（相对路径、绝对路径，或用 `$JCHENG_ASSET_ROOT` 指向仓库外
   的资产包）。
3. 运行 `bash scripts/check_repo_gate.sh`；它会校验每个 profile 以及 URDF/控制器一致性。

不需要复制任何 Python、launch 或测试文件。schema 参考、示例与资产规则见
[docs/MULTI_ROBOT.md](docs/MULTI_ROBOT.md)。

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
├── docs/                           # 架构、多机器人 schema、模型、ADR
├── evidence/20261126_offline_validation/
├── evidence/20261126_migrated_arm/
├── evidence/20261126_multi_robot_engine/
├── scripts/check_repo_gate.sh
├── tests/                          # 契约、目录、边界、植物、扫描、文档
└── ros2_ws/src/
    ├── jcheng_simulation_robots/    # 引擎本体
    │   ├── jcheng_simulation_robots/  # profile、控制器配置、植物、扫描
    │   ├── launch/robot.launch.py     # robot:=...，backend:=mock|gz
    │   ├── launch/display.launch.py   # RViz，gui:=true
    │   ├── robots/armpi_ultra/        # profile + URDF + 控制器 + 世界 + bridge
    │   ├── robots/gate2_arm/          # profile + URDF + 控制器配置 + 世界
    │   ├── robots/piper_x/            # profile + wrapper + 控制器 + 世界（外部模型）
    │   └── test/test_engine.py
    ├── jcheng_simulation_bringup/   # 兼容入口：ArmPi
    └── jcheng_simulation_arm/       # 兼容入口：Gate-2 机械臂
```

## 依赖

- **仿真主机：** ROS 2 Jazzy 与 Gazebo Sim（Harmonic，`gz sim` 8.x），用于 `gz`
  后端。主机是操作员笔记本/工作站，不是机器人。
- **Mock 后端：** 具有 `rclpy`、`sensor_msgs`、`std_msgs` 的 ROS 2；不需要 Gazebo。
- **Gazebo 后端软件包：** `ros_gz_sim`、`ros_gz_bridge`、`gz_ros2_control`、
  `joint_state_broadcaster`、`joint_trajectory_controller`、
  `robot_state_publisher`、`xacro`。
- **引擎构建/测试：** `ament_cmake_python`；`joint_state_publisher_gui` 与 `rviz2`
  仅用于 `display.launch.py gui:=true`。
- **契约：** `jcheng-interfaces` `>=0.1,<0.2`，契约哈希
  `sha256:0b8d72ce…f24b42`。
- 不需要也不访问硬件。机器人上的 Humble 栈不被本仓库使用。

## 快速开始

```bash
cd jcheng-simulation
colcon build --base-paths ros2_ws/src \
  --packages-select jcheng_simulation_robots \
                   jcheng_simulation_bringup \
                   jcheng_simulation_arm
source install/setup.bash
```

### Mock 后端（确定性，无 Gazebo）

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=armpi_ultra backend:=mock
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

mock 植物把设定值夹到 profile 限位内，以受限速度移动，并在命令中断 500 ms 后保持最后
目标。profile 声明扫描时，它以 10 Hz 发布 360 束合成扫描；`gate2_arm` 未声明扫描。

### Gazebo 后端（默认 headless）

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=armpi_ultra backend:=gz headless:=true
```

启动是 fail-closed 的：`spawn` → `joint_state_broadcaster` → `arm_controller` →
`gripper_controller`（即 profile 的 `startup_order`）。只有前一个进程以 0 退出，下一阶段
才启动；每阶段有墙钟截止时间（默认 60 秒）；支撑进程退出会关闭整个 launch。所选控制器
YAML、解析路径与 SHA-256 会在 Gazebo 启动前写入日志。

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

### 2 自由度机械臂

先停掉 ArmPi 植物：两者都占用 `/sim/controller_manager`。

```bash
ros2 launch jcheng_simulation_robots robot.launch.py \
  robot:=gate2_arm backend:=gz headless:=true
```

```bash
export ROS_DOMAIN_ID=43
ros2 action send_goal /sim/arm_controller/follow_joint_trajectory \
  control_msgs/action/FollowJointTrajectory \
  "{trajectory: {joint_names: [joint1, joint2],
     points: [{positions: [0.3, -0.2],
               time_from_start: {sec: 3, nanosec: 0}}]}}"
```

`controller_profile:=gain_0p1|gain_0p2` 选择 profile 声明的另一份控制器 YAML（V2 配置
设置 `gz_ros2_control` 的 `position_proportional_gain`）。`controller_config:=<path>`
可覆盖 YAML（绝对路径或机器人目录相对路径），启动前做 schema 校验。

### 显示

```bash
ros2 launch jcheng_simulation_robots display.launch.py robot:=gate2_arm gui:=true
```

显示始终留在域 43，仿真的机器人 TF 不会出现在机器人图里。

### 兼容入口

旧命令仍然可用；它们以固定机器人 id 包含引擎：

```bash
ros2 launch jcheng_simulation_bringup sim.launch.py backend:=mock
ros2 launch jcheng_simulation_arm gazebo.launch.py
```

新工作请优先使用引擎形式。

## 测试

```bash
python3 -m pytest -q tests
python3 -m pytest -q ros2_ws/src/jcheng_simulation_robots/test
bash scripts/check_repo_gate.sh
```

仓库测试覆盖清单契约、机器人目录与 profile schema、域隔离、无硬件/厂商资产扫描、
关节/扫描模型、profile 与 URDF/控制器 YAML 的限位一致性、fail-closed launch 接线，
以及文档集。引擎包测试覆盖严格的控制器配置选择器；其中 launch 接线用例只在 ROS 2
已 source 时运行，否则跳过。

## 验证状态

| 声明 | 级别 | 结果 | 证据 |
|---|---|---|---|
| 契约、目录、边界与单元测试 | L0/L1 | 通过 | `tests/` |
| 仓库 gate（两个目录 profile） | L0 | 通过 | `scripts/check_repo_gate.sh` |
| 目录 URDF/SDF（两个机器人） | L0 | 通过 | [证据](evidence/20261126_multi_robot_engine/README.md) |
| `armpi_ultra` mock 后端端到端 | L2 | 通过 | 同上 |
| `armpi_ultra` Gazebo 后端与 JTC 轨迹 | L2 | 通过 | 同上 |
| `gate2_arm` Gazebo 后端与 JTC 轨迹 | L2 | 通过 | 同上 |
| `piper_x` mock 后端（7 关节、真值） | L2 | 通过 | 同上 |
| `piper_x` Gazebo 后端（外部 MIT 模型，arm + gripper 目标） | L2 | 部分验证（跟踪精度未标定） | 同上 |
| 早期单包运行 | L2 | 历史记录 | [2026-11-26 离线验证](evidence/20261126_offline_validation/README.md)、[迁移机械臂](evidence/20261126_migrated_arm/README.md) |
| 硬件验证 | L5 | **不适用** | 不存在硬件路径 |

Gazebo 运行发生在操作员主机的 Jazzy/Harmonic 上，不在机器人上。未命令任何硬件
运动。完整报告：[ACCEPTANCE.md](ACCEPTANCE.md)。

## 相关仓库

- `JCHENG-Robotics/jcheng-interfaces` — 契约 schema、哈希与证据记录 schema。
- `JCHENG-Robotics/jcheng-system` — 安全、控制权、运动与硬件桥；它也在域 43 上
  拥有场景运行器 `jcheng_testkit`。
- `JCHENG-Robotics/jcheng-perception` — 建议性感知；未来集成中会消费仿真传感器流。
- `JCHENG-Robotics/jcheng-ops` — 运维；与仿真无关。
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — 为什么它是独立 SIM 层，以及引擎如何
  保持在运行时图之外。

## 许可

**待定。** 在组织审查关闭前，本仓库有意不提供 `LICENSE`，与 `jcheng-interfaces`、
`jcheng-system`、`jcheng-perception`、`jcheng-ops` 和 `.github` 一致。见
[LICENSE-REVIEW.md](LICENSE-REVIEW.md)。从 MIT 许可的 `jcheng-manipulation` 基线
迁移的代码保留其 MIT 声明，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)；
仓库中不含任何厂商资产。
