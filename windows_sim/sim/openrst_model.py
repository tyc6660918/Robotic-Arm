"""Ideal pitch/yaw/grasp kinematic model for the virtual OpenRST tool."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np
from scipy.spatial.transform import Rotation

from .types import Pose


def _translation(vector: np.ndarray) -> np.ndarray:
    transform = np.eye(4, dtype=float)
    transform[:3, 3] = vector
    return transform


def _rotation(rotation: Rotation) -> np.ndarray:
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = rotation.as_matrix()
    return transform


@dataclass
class OpenRSTGeometry:
    mount_offset: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=float))
    shaft_length: float = 0.18
    jaw_length: float = 0.018
    jaw_base_separation: float = 0.004
    max_jaw_angle: float = math.radians(30.0)

    def __post_init__(self) -> None:
        self.mount_offset = np.asarray(self.mount_offset, dtype=float).copy()
        if self.mount_offset.shape != (3,) or np.any(~np.isfinite(self.mount_offset)):
            raise ValueError("mount_offset must be a finite length-3 vector")
        lengths = (self.shaft_length, self.jaw_length, self.jaw_base_separation)
        if any(not math.isfinite(value) or value < 0.0 for value in lengths):
            raise ValueError("OpenRST lengths must be finite and non-negative")
        if not math.isfinite(self.max_jaw_angle) or not 0.0 <= self.max_jaw_angle <= math.pi:
            raise ValueError("max_jaw_angle must be in [0, pi]")


@dataclass(frozen=True)
class OpenRSTKinematicState:
    pitch: float
    yaw: float
    grasp: float
    mount_pose: Pose
    pitch_pose: Pose
    yaw_pose: Pose
    tcp_pose: Pose
    left_jaw_pose: Pose
    right_jaw_pose: Pose
    left_jaw_tip: np.ndarray
    right_jaw_tip: np.ndarray


class IdealOpenRSTModel:
    """An ideal tool model that deliberately excludes cable/motor dynamics.

    Pitch rotates about local Y, yaw about the resulting local Z, and the shaft
    extends along local Z. Grasp changes only the symmetric jaw geometry; the
    stable TCP is therefore independent of grasp.
    """

    PITCH_LIMIT = math.pi / 2.0
    YAW_LIMIT = math.pi / 2.0

    def __init__(
        self,
        geometry: OpenRSTGeometry | None = None,
        *,
        pitch_limit: float = PITCH_LIMIT,
        yaw_limit: float = YAW_LIMIT,
    ) -> None:
        self.geometry = OpenRSTGeometry() if geometry is None else geometry
        limits = np.asarray([pitch_limit, yaw_limit], dtype=float)
        if np.any(~np.isfinite(limits)) or np.any(limits <= 0.0) or np.any(limits > math.pi):
            raise ValueError("OpenRST pitch/yaw limits must be in (0, pi]")
        self.pitch_limit = float(pitch_limit)
        self.yaw_limit = float(yaw_limit)
        self.pitch = 0.0
        self.yaw = 0.0
        self.grasp = 0.0
        self.last_command_was_clipped = False

    def reset(self) -> None:
        self.pitch = 0.0
        self.yaw = 0.0
        self.grasp = 0.0
        self.last_command_was_clipped = False

    def set_command(self, pitch: float, yaw: float, grasp: float) -> None:
        values = np.asarray([pitch, yaw, grasp], dtype=float)
        if np.any(~np.isfinite(values)):
            raise ValueError("OpenRST commands must be finite")
        clipped = np.clip(
            values,
            [-self.pitch_limit, -self.yaw_limit, 0.0],
            [self.pitch_limit, self.yaw_limit, 1.0],
        )
        self.last_command_was_clipped = not np.array_equal(values, clipped)
        self.pitch, self.yaw, self.grasp = (float(value) for value in clipped)

    command = set_command

    def forward(self, flange_pose: Pose) -> OpenRSTKinematicState:
        flange = flange_pose.as_matrix()
        mount = flange @ _translation(self.geometry.mount_offset)
        pitch_frame = mount @ _rotation(Rotation.from_rotvec([0.0, self.pitch, 0.0]))
        yaw_frame = pitch_frame @ _rotation(Rotation.from_rotvec([0.0, 0.0, self.yaw]))
        tcp = yaw_frame @ _translation(
            np.array([0.0, 0.0, self.geometry.shaft_length], dtype=float)
        )

        jaw_angle = self.grasp * self.geometry.max_jaw_angle
        half_separation = 0.5 * self.geometry.jaw_base_separation
        left_jaw = (
            tcp
            @ _translation(np.array([half_separation, 0.0, 0.0]))
            @ _rotation(Rotation.from_rotvec([0.0, jaw_angle, 0.0]))
        )
        right_jaw = (
            tcp
            @ _translation(np.array([-half_separation, 0.0, 0.0]))
            @ _rotation(Rotation.from_rotvec([0.0, -jaw_angle, 0.0]))
        )
        jaw_tip_offset = np.array([0.0, 0.0, self.geometry.jaw_length, 1.0])
        left_tip = (left_jaw @ jaw_tip_offset)[:3]
        right_tip = (right_jaw @ jaw_tip_offset)[:3]

        return OpenRSTKinematicState(
            pitch=self.pitch,
            yaw=self.yaw,
            grasp=self.grasp,
            mount_pose=Pose.from_matrix(mount),
            pitch_pose=Pose.from_matrix(pitch_frame),
            yaw_pose=Pose.from_matrix(yaw_frame),
            tcp_pose=Pose.from_matrix(tcp),
            left_jaw_pose=Pose.from_matrix(left_jaw),
            right_jaw_pose=Pose.from_matrix(right_jaw),
            left_jaw_tip=left_tip,
            right_jaw_tip=right_tip,
        )

    def tcp_pose(self, flange_pose: Pose) -> Pose:
        return self.forward(flange_pose).tcp_pose


# Short alias for callers that do not need to distinguish future model types.
OpenRSTModel = IdealOpenRSTModel
