from pathlib import Path

from setuptools import setup

PACKAGE = "jcheng_simulation_robots"


def robot_data_files():
    """Install every catalog file under share/<package>/robots/<id>/... ."""

    files: dict[str, list[str]] = {}
    for path in sorted(Path("robots").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            files.setdefault(str(path.parent), []).append(str(path))
    return sorted(files.items())


setup(
    name=PACKAGE,
    version="0.1.0",
    packages=[PACKAGE],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE}"]),
        (f"share/{PACKAGE}", ["package.xml"]),
        (f"share/{PACKAGE}/launch", ["launch/robot.launch.py", "launch/display.launch.py"]),
        *[
            (f"share/{PACKAGE}/{directory}", paths)
            for directory, paths in robot_data_files()
        ],
    ],
    install_requires=["setuptools"],
    tests_require=["pytest", "PyYAML"],
    zip_safe=False,
    maintainer="JerichoCheng",
    maintainer_email="chengkewei77@gmail.com",
    description=(
        "Multi-robot offline simulation plant: robot catalog, deterministic "
        "mock plant and generic Gazebo Harmonic launch on domain 43."
    ),
    license="Proprietary (license review pending; no LICENSE file)",
    entry_points={
        "console_scripts": [
            "mock_plant = jcheng_simulation_robots.mock_node:main",
            "truth_publisher = jcheng_simulation_robots.truth:main",
        ],
    },
)
