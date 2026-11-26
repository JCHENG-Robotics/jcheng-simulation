"""URDF normalisation shared by the launch and the tests.

Vendor URDFs often omit ``<inertial>`` on geometry-less links (a dummy master
link, a ``world`` root). URDF itself requires the block; Gazebo's URDF→SDF
converter warns and drops the link, which can also drop the joint that hangs
off it and break mimic joints. The engine inserts a tiny placeholder inertial
in memory for exactly those links; the external asset is never modified.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

PLACEHOLDER_MASS_KG = 0.001
PLACEHOLDER_INERTIA = 1.0e-7


def ensure_inertials(
    xml: str, *, mass: float = PLACEHOLDER_MASS_KG
) -> tuple[str, tuple[str, ...]]:
    """Return ``(xml, inserted_link_names)`` with placeholder inertials added.

    Only direct ``<link>`` children without an ``<inertial>`` are touched. A
    link that already has one is left byte-for-byte intact (apart from the
    surrounding serialisation).
    """

    root = ET.fromstring(xml)
    inserted: list[str] = []
    for link in root.findall("link"):
        if link.find("inertial") is not None:
            continue
        inertial = ET.SubElement(link, "inertial")
        ET.SubElement(inertial, "origin", xyz="0 0 0", rpy="0 0 0")
        ET.SubElement(inertial, "mass", value=str(mass))
        ET.SubElement(
            inertial,
            "inertia",
            ixx=str(PLACEHOLDER_INERTIA),
            ixy="0.0",
            ixz="0.0",
            iyy=str(PLACEHOLDER_INERTIA),
            iyz="0.0",
            izz=str(PLACEHOLDER_INERTIA),
        )
        inserted.append(link.get("name") or "")
    if not inserted:
        return xml, ()
    return ET.tostring(root, encoding="unicode"), tuple(inserted)


def ensure_joint_dynamics(
    xml: str, damping: float, friction: float = 0.0
) -> tuple[str, tuple[str, ...]]:
    """Add ``<dynamics>`` to movable joints that do not declare one.

    Vendor descriptions often omit joint damping. Without it a position
    controller under gravity oscillates; the profile opts in per device with
    ``model.joint_damping``. Joints that already declare dynamics are left
    untouched.
    """

    if damping < 0.0 or friction < 0.0:
        raise ValueError("damping and friction must be >= 0")
    root = ET.fromstring(xml)
    changed: list[str] = []
    for joint in root.findall("joint"):
        if joint.get("type") not in {"revolute", "prismatic", "continuous"}:
            continue
        if joint.find("dynamics") is not None:
            continue
        ET.SubElement(joint, "dynamics", damping=str(damping), friction=str(friction))
        changed.append(joint.get("name") or "")
    if not changed:
        return xml, ()
    return ET.tostring(root, encoding="unicode"), tuple(changed)
