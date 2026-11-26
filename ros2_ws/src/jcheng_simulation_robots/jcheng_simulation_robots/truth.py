"""Publish the simulated-truth marker for a Gazebo plant.

The mock backend publishes ``/sim/truth/source`` from its own node. The Gazebo
backends need a separate publisher because ``gz_ros2_control`` and the bridge
own their processes. The value is the profile's ``truth.label`` (``simulated``).
"""

from __future__ import annotations

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


class TruthPublisher(Node):
    def __init__(self) -> None:
        super().__init__("jcheng_sim_truth")
        self.declare_parameter("topic", "/sim/truth/source")
        self.declare_parameter("label", "simulated")
        topic = self.get_parameter("topic").value
        self._label = self.get_parameter("label").value
        qos = QoSProfile(
            depth=1,
            history=HistoryPolicy.KEEP_LAST,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._publisher = self.create_publisher(String, topic, qos)
        self.create_timer(1.0, self._publish)
        self._publish()
        self.get_logger().info(f"truth source ready: {topic} = {self._label}")

    def _publish(self) -> None:
        message = String()
        message.data = self._label
        self._publisher.publish(message)


def main(args: list[str] | None = None) -> int:
    rclpy.init(args=args)
    node = TruthPublisher()
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
