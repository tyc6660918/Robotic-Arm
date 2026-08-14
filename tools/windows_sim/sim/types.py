"""Shared, ROS-shaped value types for the offline simulator.

All positions are metres, all angles are radians, and quaternions use ROS'
``[x, y, z, w]`` ordering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.spatial.transform import Rotation


FloatArray = NDArray[np.float64]


def _vector(value: ArrayLike, size: int, name: str) -> FloatArray:
    result = np.asarray(value, dtype=float).copy()
    if result.shape != (size,):
        raise ValueError(f"{name} must have shape ({size},), got {result.shape}")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


@dataclass(slots=True)
class Pose:
    """Cartesian pose with a normalized ``xyzw`` quaternion."""

    position: FloatArray = field(default_factory=lambda: np.zeros(3, dtype=float))
    orientation: FloatArray = field(
        default_factory=lambda: np.array([0.0, 0.0, 0.0, 1.0], dtype=float)
    )

    def __post_init__(self) -> None:
        self.position = _vector(self.position, 3, "position")
        self.orientation = _vector(self.orientation, 4, "orientation")
        norm = float(np.linalg.norm(self.orientation))
        if norm <= np.finfo(float).eps:
            raise ValueError("orientation quaternion must be non-zero")
        self.orientation /= norm

    @classmethod
    def identity(cls) -> "Pose":
        return cls()

    def copy(self) -> "Pose":
        return Pose(self.position.copy(), self.orientation.copy())

    @property
    def orientation_xyzw(self) -> FloatArray:
        """Explicit quaternion-order alias used by recorders and ROS adapters."""

        return self.orientation

    def as_matrix(self) -> FloatArray:
        transform = np.eye(4, dtype=float)
        transform[:3, :3] = Rotation.from_quat(self.orientation).as_matrix()
        transform[:3, 3] = self.position
        return transform

    @classmethod
    def from_matrix(cls, transform: ArrayLike) -> "Pose":
        matrix = np.asarray(transform, dtype=float)
        if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
            raise ValueError("transform must be a finite 4x4 matrix")
        if not np.allclose(matrix[3], [0.0, 0.0, 0.0, 1.0], atol=1e-10):
            raise ValueError("transform has an invalid homogeneous bottom row")
        rotation = matrix[:3, :3]
        if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8):
            raise ValueError("transform rotation is not orthonormal")
        if not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-8):
            raise ValueError("transform rotation must have determinant +1")
        return cls(matrix[:3, 3], Rotation.from_matrix(rotation).as_quat())


@dataclass(slots=True)
class MasterState:
    """Latest virtual master sample; no history queue is implied."""

    timestamp: float = 0.0
    sequence: int = 0
    flange_pose: Pose = field(default_factory=Pose.identity)
    flange_twist: FloatArray = field(default_factory=lambda: np.zeros(6, dtype=float))
    grasp: float = 0.0
    deadman: bool = False
    clutch: bool = False
    validity_flags: int = 0

    def __post_init__(self) -> None:
        if not np.isfinite(self.timestamp):
            raise ValueError("timestamp must be finite")
        if self.sequence < 0:
            raise ValueError("sequence must be non-negative")
        self.flange_twist = _vector(self.flange_twist, 6, "flange_twist")
        if not np.isfinite(self.grasp) or not 0.0 <= self.grasp <= 1.0:
            raise ValueError("grasp must be in [0, 1]")

    @property
    def pose(self) -> Pose:
        """Compatibility alias for consumers that call the master pose ``pose``."""

        return self.flange_pose

    @pose.setter
    def pose(self, value: Pose) -> None:
        self.flange_pose = value


@dataclass(slots=True)
class RobotState:
    """Simulated slave feedback at one control instant."""

    timestamp: float = 0.0
    joint_positions: FloatArray = field(default_factory=lambda: np.zeros(6, dtype=float))
    joint_velocities: FloatArray = field(default_factory=lambda: np.zeros(6, dtype=float))
    flange_pose: Pose = field(default_factory=Pose.identity)
    target_joint_positions: FloatArray = field(
        default_factory=lambda: np.zeros(6, dtype=float)
    )

    def __post_init__(self) -> None:
        if not np.isfinite(self.timestamp):
            raise ValueError("timestamp must be finite")
        self.joint_positions = _vector(self.joint_positions, 6, "joint_positions")
        self.joint_velocities = _vector(self.joint_velocities, 6, "joint_velocities")
        self.target_joint_positions = _vector(
            self.target_joint_positions, 6, "target_joint_positions"
        )


class TeleopState(str, Enum):
    DISABLED = "DISABLED"
    READY = "READY"
    TELEOP = "TELEOP"
    HOLD = "HOLD"
    FAULT = "FAULT"


@dataclass(slots=True)
class TeleopStatus:
    """Observable control and safety status used by logs and the viewer."""

    state: TeleopState = TeleopState.DISABLED
    message_age: float = float("inf")
    position_error: float = 0.0
    orientation_error: float = 0.0
    ik_success: bool = False
    loop_period: float = 0.0
    scale: float = 1.0
    fault_bits: int = 0
    fault_reason: str = ""
