"""Minimal, strict URDF parser for serial kinematic chains."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]


def _vector(text: str | None, default: tuple[float, float, float]) -> FloatArray:
    if text is None:
        return np.asarray(default, dtype=float)
    parts = text.split()
    if len(parts) != 3:
        raise ValueError(f"expected a three-component URDF vector, got {text!r}")
    result = np.asarray([float(part) for part in parts], dtype=float)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"URDF vector must be finite, got {text!r}")
    return result


@dataclass(frozen=True, slots=True)
class JointLimit:
    lower: float
    upper: float
    velocity: float | None = None
    effort: float | None = None

    def __post_init__(self) -> None:
        if not np.isfinite(self.lower) or not np.isfinite(self.upper):
            raise ValueError("joint bounds must be finite")
        if self.lower > self.upper:
            raise ValueError("joint lower bound exceeds upper bound")


@dataclass(frozen=True, slots=True)
class Joint:
    name: str
    joint_type: str
    parent: str
    child: str
    origin_xyz: FloatArray
    origin_rpy: FloatArray
    axis: FloatArray
    limit: JointLimit | None = None

    @property
    def movable(self) -> bool:
        return self.joint_type in {"revolute", "continuous", "prismatic"}


@dataclass(frozen=True, slots=True)
class URDFModel:
    name: str
    links: tuple[str, ...]
    joints: tuple[Joint, ...]

    def __post_init__(self) -> None:
        link_set = set(self.links)
        if len(link_set) != len(self.links):
            raise ValueError("URDF contains duplicate link names")
        if len({joint.name for joint in self.joints}) != len(self.joints):
            raise ValueError("URDF contains duplicate joint names")
        children: set[str] = set()
        for joint in self.joints:
            if joint.parent not in link_set or joint.child not in link_set:
                raise ValueError(f"joint {joint.name!r} references an unknown link")
            if joint.child in children:
                raise ValueError(f"link {joint.child!r} has multiple parent joints")
            children.add(joint.child)

    @property
    def root_links(self) -> tuple[str, ...]:
        children = {joint.child for joint in self.joints}
        return tuple(link for link in self.links if link not in children)

    def joint(self, name: str) -> Joint:
        for joint in self.joints:
            if joint.name == name:
                return joint
        raise KeyError(name)

    def chain(self, base_link: str, tip_link: str) -> tuple[Joint, ...]:
        """Return the unique ordered joint path from ``base_link`` to ``tip_link``."""

        if base_link not in self.links:
            raise KeyError(f"unknown base link {base_link!r}")
        if tip_link not in self.links:
            raise KeyError(f"unknown tip link {tip_link!r}")
        by_child = {joint.child: joint for joint in self.joints}
        reverse_path: list[Joint] = []
        current = tip_link
        visited: set[str] = set()
        while current != base_link:
            if current in visited:
                raise ValueError("cycle detected in URDF kinematic tree")
            visited.add(current)
            try:
                joint = by_child[current]
            except KeyError as exc:
                raise ValueError(
                    f"{tip_link!r} is not a descendant of {base_link!r}"
                ) from exc
            reverse_path.append(joint)
            current = joint.parent
        return tuple(reversed(reverse_path))


def parse_urdf(path: str | Path) -> URDFModel:
    source = Path(path)
    try:
        root = ET.parse(source).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError(f"unable to parse URDF {source}: {exc}") from exc
    if root.tag != "robot":
        raise ValueError("URDF root element must be <robot>")

    links = tuple(
        element.attrib["name"]
        for element in root.findall("link")
        if "name" in element.attrib
    )
    joints: list[Joint] = []
    supported_types = {"fixed", "revolute", "continuous", "prismatic"}
    for element in root.findall("joint"):
        name = element.attrib.get("name")
        joint_type = element.attrib.get("type")
        parent_element = element.find("parent")
        child_element = element.find("child")
        if not name or not joint_type or parent_element is None or child_element is None:
            raise ValueError("every URDF joint needs name, type, parent, and child")
        if joint_type not in supported_types:
            raise ValueError(f"unsupported URDF joint type {joint_type!r}")
        try:
            parent = parent_element.attrib["link"]
            child = child_element.attrib["link"]
        except KeyError as exc:
            raise ValueError(f"joint {name!r} has an incomplete parent/child") from exc

        origin = element.find("origin")
        xyz = _vector(None if origin is None else origin.attrib.get("xyz"), (0.0, 0.0, 0.0))
        rpy = _vector(None if origin is None else origin.attrib.get("rpy"), (0.0, 0.0, 0.0))
        axis_element = element.find("axis")
        axis = _vector(
            None if axis_element is None else axis_element.attrib.get("xyz"),
            (1.0, 0.0, 0.0),
        )
        if joint_type != "fixed":
            norm = float(np.linalg.norm(axis))
            if norm <= np.finfo(float).eps:
                raise ValueError(f"joint {name!r} has a zero axis")
            axis = axis / norm

        limit_element = element.find("limit")
        limit = None
        if joint_type in {"revolute", "prismatic"}:
            if limit_element is None:
                raise ValueError(f"joint {name!r} requires a limit element")
            try:
                lower = float(limit_element.attrib["lower"])
                upper = float(limit_element.attrib["upper"])
            except (KeyError, ValueError) as exc:
                raise ValueError(f"joint {name!r} has invalid limits") from exc
            velocity_text = limit_element.attrib.get("velocity")
            effort_text = limit_element.attrib.get("effort")
            limit = JointLimit(
                lower=lower,
                upper=upper,
                velocity=None if velocity_text is None else float(velocity_text),
                effort=None if effort_text is None else float(effort_text),
            )

        joints.append(
            Joint(
                name=name,
                joint_type=joint_type,
                parent=parent,
                child=child,
                origin_xyz=xyz,
                origin_rpy=rpy,
                axis=axis,
                limit=limit,
            )
        )
    if not links:
        raise ValueError("URDF contains no links")
    return URDFModel(root.attrib.get("name", source.stem), links, tuple(joints))


def default_dummy_urdf_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "Moveit_ws-main"
        / "dummy-ros2_description"
        / "urdf"
        / "dummy.urdf"
    )


def default_openrst_urdf_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "OpenRST-main"
        / "URDF"
        / "openrst_description"
        / "urdf"
        / "openrst.urdf"
    )


def load_dummy_urdf(path: str | Path | None = None) -> URDFModel:
    return parse_urdf(default_dummy_urdf_path() if path is None else path)


def load_openrst_urdf(path: str | Path | None = None) -> URDFModel:
    return parse_urdf(default_openrst_urdf_path() if path is None else path)
