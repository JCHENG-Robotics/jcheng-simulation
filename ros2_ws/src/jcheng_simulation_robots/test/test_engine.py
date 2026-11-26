"""Engine tests: profile loading, controller selection and launch wiring.

The resolver tests run without ROS. The launch-wiring tests need
``launch``/``launch_ros``/``ament_index_python``/``xacro`` and are skipped in a
bare Python environment.
"""

import importlib.util
import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import yaml

from jcheng_simulation_robots.controller_config import ControllerConfigError
from jcheng_simulation_robots.model import ensure_inertials, ensure_joint_dynamics
from jcheng_simulation_robots.profile import load_profile

PACKAGE = Path(__file__).resolve().parents[1]


def _ros_available():
    try:
        import ament_index_python  # noqa: F401
        import launch  # noqa: F401
        import launch_ros  # noqa: F401
        import xacro  # noqa: F401
    except ImportError:
        return False
    return True


class ResolverTest(unittest.TestCase):
    def setUp(self):
        self.gate2 = load_profile(PACKAGE / "robots" / "gate2_arm" / "robot.yaml")
        self.armpi = load_profile(PACKAGE / "robots" / "armpi_ultra" / "robot.yaml")
        self.piper = load_profile(PACKAGE / "robots" / "piper_x" / "robot.yaml")

    def test_default_profiles_and_hashes(self):
        self.assertEqual(
            self.armpi.resolve_controller().sha256,
            "8e1fc2d6d86339215e181302aa07d62de4507e8306074fe4f67173771357373f",
        )
        self.assertEqual(
            self.gate2.resolve_controller().sha256,
            "b0c1ad43dbc4d46d0e553034e4c47ec50ed64e945bef5b0065fb2e78fe7c730e",
        )
        low = self.gate2.resolve_controller("gain_0p1")
        high = self.gate2.resolve_controller("gain_0p2")
        self.assertEqual(
            low.sha256, "3016246edf65af20fa8afa315d447573d990be67693b4b20636207869be3fbec"
        )
        self.assertEqual(
            high.sha256, "8b0c43656a4b83e5d2f6e0d8f8b5b68f73de15fd276db3e53d816754b775e7e3"
        )
        self.assertEqual(low.gain, 0.1)
        self.assertEqual(high.gain, 0.2)
        self.assertIsNone(self.gate2.resolve_controller("default").gain)
        self.assertEqual(self.piper.resolve_controller().gain, 10.0)

    def test_gain_profiles_differ_in_the_gain_byte_only(self):
        low = self.gate2.resolve_controller("gain_0p1").realpath.read_bytes()
        high = self.gate2.resolve_controller("gain_0p2").realpath.read_bytes()
        self.assertEqual(low.count(b"position_proportional_gain: 0.1"), 1)
        self.assertEqual(
            low.replace(
                b"position_proportional_gain: 0.1", b"position_proportional_gain: 0.2"
            ),
            high,
        )

    def test_strict_yaml_features_are_rejected(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        cases = {
            "duplicate.yaml": "controller_manager: {}\ncontroller_manager: {}\n",
            "multiple.yaml": "---\n{}\n---\n{}\n",
            "anchor.yaml": "controller_manager: &same {}\narm_controller: *same\n",
            "tag.yaml": "!unsafe {}\n",
        }
        for name, body in cases.items():
            path = Path(directory.name) / name
            path.write_text(body, encoding="utf-8")
            with self.subTest(name=name), self.assertRaises(ControllerConfigError):
                self.gate2.resolve_controller("default", str(path))

    def test_paths_are_robot_relative_and_expand_user(self):
        relative = self.gate2.resolve_controller("gain_0p1", "config/arm_controllers_gain_0p1.yaml")
        self.assertEqual(
            relative.realpath,
            (PACKAGE / "robots" / "gate2_arm" / "config" / "arm_controllers_gain_0p1.yaml").resolve(),
        )
        home = Path.home() / "controller-config-test.yaml"
        self.addCleanup(lambda: home.unlink(missing_ok=True))
        shutil.copy(relative.realpath, home)
        self.assertEqual(
            self.gate2.resolve_controller("gain_0p1", "~/controller-config-test.yaml").realpath,
            home.resolve(),
        )
        for raw in (" bad.yaml", "bad.yaml ", "bad\n.yaml", "$HOME/x.yaml", "missing.yaml"):
            with self.subTest(raw=raw), self.assertRaises(ControllerConfigError):
                self.gate2.resolve_controller("gain_0p1", raw)

    def test_schema_mismatches_are_rejected(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        source = (PACKAGE / "robots" / "gate2_arm" / "config" / "arm_controllers_gain_0p1.yaml").read_text(
            encoding="utf-8"
        )
        cases = {
            "unqualified": source.replace("/sim/arm_controller:", "arm_controller:"),
            "integer_gain": source.replace(
                "position_proportional_gain: 0.1", "position_proportional_gain: 1"
            ),
            "wrong_joints": source.replace("- joint2", "- joint3"),
            "extra_key": source.replace(
                "    open_loop_control: false", "    open_loop_control: false\n    unexpected: 1"
            ),
            "missing_gain": source.split("/sim/gz_ros_control:")[0],
        }
        for name, body in cases.items():
            path = Path(directory.name) / f"{name}.yaml"
            path.write_text(body, encoding="utf-8")
            with self.subTest(name=name), self.assertRaises(ControllerConfigError):
                self.gate2.resolve_controller("gain_0p1", str(path))

    def test_armpi_controller_config_rejects_a_gain_block(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        data = yaml.safe_load(
            (PACKAGE / "robots" / "armpi_ultra" / "config" / "controllers.yaml").read_text(
                encoding="utf-8"
            )
        )
        data["/sim/gz_ros_control"] = {"ros__parameters": {"position_proportional_gain": 0.1}}
        path = Path(directory.name) / "with_gain.yaml"
        path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        with self.assertRaises(ControllerConfigError):
            self.armpi.resolve_controller("default", str(path))


class ModelNormalisationTest(unittest.TestCase):
    def test_missing_inertials_get_a_placeholder(self):
        xml = (
            '<robot name="r">'
            '<link name="world"/>'
            '<link name="base"><inertial><mass value="2"/></inertial></link>'
            "</robot>"
        )
        result, inserted = ensure_inertials(xml)
        self.assertEqual(inserted, ("world",))
        root = ET.fromstring(result)
        world = root.find("link[@name='world']")
        self.assertIsNotNone(world.find("inertial"))
        self.assertAlmostEqual(float(world.find("inertial/mass").get("value")), 0.001)
        base = root.find("link[@name='base']")
        self.assertEqual(base.find("inertial/mass").get("value"), "2")

    def test_complete_models_are_returned_unchanged(self):
        xml = (
            '<robot name="r"><link name="base">'
            '<inertial><mass value="1"/></inertial></link></robot>'
        )
        result, inserted = ensure_inertials(xml)
        self.assertEqual(inserted, ())
        self.assertEqual(result, xml)

    def test_joint_dynamics_are_added_only_when_missing(self):
        xml = (
            '<robot name="r">'
            '<joint name="j1" type="revolute"/>'
            '<joint name="j2" type="revolute"><dynamics damping="0.5"/></joint>'
            '<joint name="fix" type="fixed"/>'
            "</robot>"
        )
        result, changed = ensure_joint_dynamics(xml, 1.0)
        self.assertEqual(changed, ("j1",))
        root = ET.fromstring(result)
        j1 = root.find("joint[@name='j1']")
        self.assertEqual(j1.find("dynamics").get("damping"), "1.0")
        j2 = root.find("joint[@name='j2']")
        self.assertEqual(j2.find("dynamics").get("damping"), "0.5")
        self.assertIsNone(root.find("joint[@name='fix']").find("dynamics"))


@unittest.skipUnless(_ros_available(), "ROS 2 launch/xacro not sourced")
class ExternalModelTest(unittest.TestCase):
    """Expand the external Piper X model and compare it with the profile."""

    @classmethod
    def setUpClass(cls):
        import xacro

        cls.profile = load_profile(PACKAGE / "robots" / "piper_x" / "robot.yaml")
        if not cls.profile.model_available:
            raise unittest.SkipTest(
                f"Piper X assets not materialised: {cls.profile.missing_assets}"
            )
        current = os.environ.get("AMENT_PREFIX_PATH", "")
        os.environ["AMENT_PREFIX_PATH"] = (
            f"{cls.profile.asset_prefix}:{current}"
            if current
            else str(cls.profile.asset_prefix)
        )
        cls.xacro = xacro

    def test_external_model_expands_and_matches_the_profile(self):
        selection = self.profile.resolve_controller()
        xml = self.xacro.process_file(
            str(self.profile.urdf),
            mappings={"controller_config": str(selection.realpath)},
        ).toxml()
        self.assertIn("<namespace>/sim</namespace>", xml)
        self.assertIn("gz_ros2_control::GazeboSimROS2ControlPlugin", xml)
        root = ET.fromstring(xml)
        # Model joints are direct children; <ros2_control> joints are nested.
        joints = {joint.get("name"): joint for joint in root.findall("joint")}
        for spec in self.profile.joints:
            self.assertIn(spec.name, joints)
            urdf_joint = joints[spec.name]
            self.assertEqual(urdf_joint.get("type"), spec.type, spec.name)
            limit = urdf_joint.find("limit")
            self.assertIsNotNone(limit, spec.name)
            self.assertGreaterEqual(spec.lower, float(limit.get("lower")) - 1e-9, spec.name)
            self.assertLessEqual(spec.upper, float(limit.get("upper")) + 1e-9, spec.name)
            self.assertLessEqual(spec.velocity, float(limit.get("velocity")) + 1e-9, spec.name)
        # The gripper fingers are mimic joints, not command joints.
        self.assertIn("gripper_joint1", joints)
        self.assertIn("mimic", xml)
        # Upstream omits inertials on the dummy master link and the world link.
        _, inserted = ensure_inertials(xml)
        self.assertEqual(inserted, ("world", "gripper_link"))


@unittest.skipUnless(_ros_available(), "ROS 2 launch/xacro not sourced")
class LaunchWiringTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        launch_path = PACKAGE / "launch" / "robot.launch.py"
        spec = importlib.util.spec_from_file_location("engine_launch", launch_path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_success_starts_the_next_stage_with_its_own_deadline(self):
        next_action = object()
        context = SimpleNamespace(launch_configurations={})
        result = self.module._after_success("spawn", ("jsb", next_action), 12.5)(
            SimpleNamespace(returncode=0, process_name="spawn"), context
        )
        self.assertEqual(context.launch_configurations["robot_startup_spawn_completed"], "true")
        self.assertIs(result[0], next_action)
        self.assertEqual(result[1].period, 12.5)

    def test_nonzero_exit_does_not_start_the_next_stage(self):
        context = SimpleNamespace(launch_configurations={})
        result = self.module._after_success("jsb", ("arm", object()), 12.5)(
            SimpleNamespace(returncode=3, process_name="jsb"), context
        )
        self.assertEqual(len(result), 2)
        self.assertNotIn("robot_startup_jsb_completed", context.launch_configurations)

    def test_completed_stage_watchdog_is_inert(self):
        timer = self.module._watchdog("arm_controller", 12.5)
        callback = timer.actions[0].execute
        context = SimpleNamespace(
            launch_configurations={"robot_startup_arm_controller_completed": "true"}
        )
        self.assertEqual(callback(context), [])

    def test_gazebo_include_requests_shutdown_on_exit(self):
        source = (PACKAGE / "launch" / "robot.launch.py").read_text(encoding="utf-8")
        self.assertIn('"on_exit_shutdown": "true"', source)


if __name__ == "__main__":
    unittest.main()
