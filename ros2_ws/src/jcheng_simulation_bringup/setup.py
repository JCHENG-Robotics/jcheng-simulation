from glob import glob

from setuptools import setup

PACKAGE = "jcheng_simulation_bringup"

setup(
    name=PACKAGE,
    version="0.1.0",
    packages=[PACKAGE],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE}"]),
        (f"share/{PACKAGE}", ["package.xml"]),
        (f"share/{PACKAGE}/launch", glob("launch/*.launch.py")),
        (f"share/{PACKAGE}/urdf", glob("urdf/*.xacro")),
        (f"share/{PACKAGE}/worlds", glob("worlds/*.sdf")),
        (f"share/{PACKAGE}/config", glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    tests_require=["pytest", "PyYAML"],
    zip_safe=False,
    maintainer="JerichoCheng",
    maintainer_email="chengkewei77@gmail.com",
    description=(
        "Offline simulation plant for the JCHENG ecosystem: mock joint/scan "
        "plant and Gazebo Harmonic bringup on domain 43."
    ),
    license="Proprietary (license review pending; no LICENSE file)",
    entry_points={
        "console_scripts": [
            "mock_plant = jcheng_simulation_bringup.node:main",
        ],
    },
)
