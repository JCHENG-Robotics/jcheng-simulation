"""ROS 2 mock plant node.

Publishes simulated joint states and a synthetic 2D scan under /sim. It never
opens a device, never joins domains 0/41/42 and never sends a motion command to
the system layer. The node is a thin wrapper around the ROS-free plant and scan
models.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import rclpy
import yaml
from ament_index_python.packages import get_package_share_directory
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import JointState, LaserScan
from std_msgs.msg import String

from .plant import JOINT_ORDER, JointPlant, load_joint_limits
from .scan import RoomModel, scan_ranges


class MockPlantNode(Node):
    """Deterministic plant behind the mock backend."""

    def __init__(self) -> None:
        super().__init__("jcheng_sim_mock_plant")
        share = Path(get_package_share_directory("jcheng_simulation_bringup"))
        self.declare_parameter("config_file", str(share / "config" / "sim.yaml"))
        self.declare_parameter("limits_file", str(share / "config" / "joint_limits.yaml"))

        config_path = Path(self.get_parameter("config_file").value)
        limits_path = Path(self.get_parameter("limits_file").value)
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        mock = config["backends"]["mock"]
        self._topics = config["topics"]
        self._truth_topic = config["truth"]["topic"]

        initial = {name: float(value) for name, value in mock.get("initial", {}).items()}
        self._plant = JointPlant(
            load_joint_limits(limits_path),
            time_constant_s=float(mock["joint_time_constant_s"]),
            initial=initial,
        )
        room_cfg = mock["room"]
        self._room = RoomModel(
            width_m=float(room_cfg["width_m"]),
            depth_m=float(room_cfg["depth_m"]),
            obstacle_x_m=float(room_cfg["obstacle_x_m"]),
            obstacle_y_m=float(room_cfg["obstacle_y_m"]),
            obstacle_radius_m=float(room_cfg["obstacle_radius_m"]),
        )
        self._beam_count = int(mock.get("beam_count", 360))
        self._max_range_m = float(mock.get("max_range_m", 8.0))
        self._command_timeout_s = float(mock["command_timeout_ms"]) / 1000.0
        self._last_command_at: float | None = None
        self._timed_out = False

        qos = QoSProfile(
            depth=1,
            history=HistoryPolicy.KEEP_LAST,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        truth_qos = QoSProfile(
            depth=1,
            history=HistoryPolicy.KEEP_LAST,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )

        self._joint_pub = self.create_publisher(
            JointState, self._topics["joint_states"], qos
        )
        self._scan_pub = self.create_publisher(LaserScan, self._topics["scan"], qos)
        self._truth_pub = self.create_publisher(String, self._truth_topic, truth_qos)
        self._command_sub = self.create_subscription(
            JointState, self._topics["joint_command"], self._on_command, qos
        )

        rate_hz = float(mock["rate_hz"])
        scan_rate_hz = float(mock["scan_rate_hz"])
        self._step_timer = self.create_timer(1.0 / rate_hz, self._step)
        self._scan_timer = self.create_timer(1.0 / scan_rate_hz, self._publish_scan)
        self._truth_timer = self.create_timer(5.0, self._publish_truth)
        self._publish_truth()

        self.get_logger().info(
            "mock plant ready: domain 43, %d joints, %.0f Hz step, %.0f Hz scan"
            % (len(JOINT_ORDER), rate_hz, scan_rate_hz)
        )

    def _publish_truth(self) -> None:
        message = String()
        message.data = "simulated"
        self._truth_pub.publish(message)

    def _on_command(self, message: JointState) -> None:
        names = list(message.name) if message.name else list(JOINT_ORDER)
        if len(names) != len(message.position):
            self.get_logger().warning(
                "joint_command name/position length mismatch; command ignored",
                throttle_duration_sec=5.0,
            )
            return
        targets = dict(zip(names, message.position))
        try:
            self._plant.set_targets(targets)
        except ValueError as exc:
            self.get_logger().warning(
                f"joint_command rejected: {exc}", throttle_duration_sec=5.0
            )
            return
        self._last_command_at = time.monotonic()
        self._timed_out = False

    def _step(self) -> None:
        if (
            self._last_command_at is not None
            and not self._timed_out
            and time.monotonic() - self._last_command_at > self._command_timeout_s
        ):
            self._timed_out = True
            self.get_logger().info(
                "joint_command idle beyond %.0f ms; holding the last targets"
                % (self._command_timeout_s * 1000.0)
            )
        dt = self._step_period_s()
        self._plant.step(dt)
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_link"
        message.name = list(JOINT_ORDER)
        message.position = [self._plant.positions[name] for name in JOINT_ORDER]
        message.velocity = [self._plant.velocities[name] for name in JOINT_ORDER]
        self._joint_pub.publish(message)

    def _step_period_s(self) -> float:
        return float(self._step_timer.timer_period_ns) / 1e9

    def _publish_scan(self) -> None:
        stamp = self.get_clock().now().to_msg()
        ranges = scan_ranges(self._room, self._beam_count, self._max_range_m)
        message = LaserScan()
        message.header.stamp = stamp
        message.header.frame_id = "laser_link"
        message.angle_min = -math.pi
        message.angle_max = math.pi
        message.angle_increment = (2.0 * math.pi) / self._beam_count
        message.time_increment = 0.0
        message.scan_time = float(self._scan_timer.timer_period_ns) / 1e9
        message.range_min = 0.05
        message.range_max = self._max_range_m
        message.ranges = ranges
        self._scan_pub.publish(message)


def main(args: list[str] | None = None) -> int:
    rclpy.init(args=args)
    node = MockPlantNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
