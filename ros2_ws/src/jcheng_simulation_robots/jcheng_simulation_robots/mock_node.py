"""Generic ROS 2 mock plant node driven by a robot profile.

Publishes simulated joint states (and, when the profile declares a lidar, a
synthetic scan) under ``/sim``. It never opens a device, never joins domains
0/41/42 and never sends a motion command to the system layer. The node is a
thin wrapper around the ROS-free plant and scan models.
"""

from __future__ import annotations

import math
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import JointState, LaserScan
from std_msgs.msg import String

from .plant import JointLimit, JointPlant
from .profile import Profile, load_profile
from .scan import RoomModel, scan_ranges


class MockPlantNode(Node):
    """Deterministic plant behind the mock backend for any catalog robot."""

    def __init__(self) -> None:
        super().__init__("jcheng_sim_mock_plant")
        self.declare_parameter("profile_file", "")
        profile_path = self.get_parameter("profile_file").value
        if not profile_path:
            raise RuntimeError("profile_file parameter is required")
        self._profile: Profile = load_profile(profile_path)
        self._joint_names = self._profile.joint_names

        limits = {
            joint.name: JointLimit(joint.lower, joint.upper, joint.velocity)
            for joint in self._profile.joints
        }
        mock = self._profile.mock
        self._plant = JointPlant(
            limits,
            self._joint_names,
            time_constant_s=mock.time_constant_s,
            initial=mock.initial,
        )
        self._command_timeout_s = mock.command_timeout_ms / 1000.0
        self._last_command_at: float | None = None
        self._timed_out = False

        scan = mock.scan
        self._scan = scan
        self._room = RoomModel.from_mapping(dict(scan.room)) if scan is not None else None

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
            JointState, self._profile.joint_states_topic, qos
        )
        self._truth_pub = self.create_publisher(
            String, self._profile.truth_topic, truth_qos
        )
        self._command_sub = self.create_subscription(
            JointState, self._profile.joint_command_topic, self._on_command, qos
        )
        self._scan_pub = None
        if scan is not None:
            self._scan_pub = self.create_publisher(LaserScan, scan.topic, qos)

        self._step_timer = self.create_timer(1.0 / mock.rate_hz, self._step)
        self._truth_timer = self.create_timer(5.0, self._publish_truth)
        self._publish_truth()
        if scan is not None:
            self._scan_timer = self.create_timer(1.0 / scan.rate_hz, self._publish_scan)

        self.get_logger().info(
            "mock plant ready: robot=%s, %d joints, %.0f Hz step%s"
            % (
                self._profile.robot_id,
                len(self._joint_names),
                mock.rate_hz,
                "" if scan is None else f", {scan.rate_hz:.0f} Hz scan",
            )
        )

    def _publish_truth(self) -> None:
        message = String()
        message.data = self._profile.truth_label
        self._truth_pub.publish(message)

    def _on_command(self, message: JointState) -> None:
        names = list(message.name) if message.name else list(self._joint_names)
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
        dt = float(self._step_timer.timer_period_ns) / 1e9
        self._plant.step(dt)
        message = JointState()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "base_link"
        message.name = list(self._joint_names)
        message.position = [self._plant.positions[name] for name in self._joint_names]
        message.velocity = [self._plant.velocities[name] for name in self._joint_names]
        self._joint_pub.publish(message)

    def _publish_scan(self) -> None:
        scan = self._scan
        room = self._room
        assert scan is not None and room is not None
        message = LaserScan()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = scan.frame
        message.angle_min = scan.angle_min_rad
        message.angle_max = scan.angle_max_rad
        message.angle_increment = (scan.angle_max_rad - scan.angle_min_rad) / scan.beam_count
        message.time_increment = 0.0
        message.scan_time = 1.0 / scan.rate_hz
        message.range_min = scan.range_min_m
        message.range_max = scan.max_range_m
        message.ranges = scan_ranges(
            room,
            scan.beam_count,
            scan.max_range_m,
            angle_min_rad=scan.angle_min_rad,
            angle_max_rad=scan.angle_max_rad,
        )
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
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
