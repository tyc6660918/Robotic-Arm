"""Single source of truth for Dummy ROS/hardware joint conventions."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


FloatArray = NDArray[np.float64]
DUMMY_JOINT_NAMES = ("Joint1", "Joint2", "Joint3", "Joint4", "Joint5", "Joint6")

# These are the deliberate intersection of the model and firmware envelopes.
SAFE_JOINT_LIMITS_RAD = np.array(
    [
        np.deg2rad([-170.0, 170.0]),
        np.deg2rad([-73.0, 90.0]),
        np.deg2rad([-55.0, 90.0]),
        [-3.14, 3.14],
        np.deg2rad([-90.0, 90.0]),
        [-3.14, 3.14],
    ],
    dtype=float,
)
SAFE_JOINT_LIMITS_DEG = np.rad2deg(SAFE_JOINT_LIMITS_RAD)

# hw_deg = rad2deg((q_ros + offset) * direction)
ROS_TO_HARDWARE_OFFSET_RAD = np.deg2rad(
    np.array([0.0, 0.0, 90.0, 0.0, 0.0, 0.0], dtype=float)
)
ROS_TO_HARDWARE_DIRECTION = np.array([1.0, 1.0, 1.0, 1.0, -1.0, -1.0])


def _joint_vector(joints: ArrayLike, name: str = "joints") -> FloatArray:
    result = np.asarray(joints, dtype=float)
    if result.shape != (6,):
        raise ValueError(f"{name} must have shape (6,), got {result.shape}")
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values")
    return result


def safe_lower_limits() -> FloatArray:
    return SAFE_JOINT_LIMITS_RAD[:, 0].copy()


def safe_upper_limits() -> FloatArray:
    return SAFE_JOINT_LIMITS_RAD[:, 1].copy()


def ros_to_hardware_degrees(ros_joints: ArrayLike) -> FloatArray:
    """Convert six ROS joint angles in radians to hardware angles in degrees."""

    ros = _joint_vector(ros_joints, "ros_joints")
    return np.rad2deg((ros + ROS_TO_HARDWARE_OFFSET_RAD) * ROS_TO_HARDWARE_DIRECTION)


def hardware_degrees_to_ros(hardware_joints: ArrayLike) -> FloatArray:
    """Convert six hardware joint angles in degrees to ROS radians."""

    hardware = _joint_vector(hardware_joints, "hardware_joints")
    return (
        np.deg2rad(hardware) / ROS_TO_HARDWARE_DIRECTION
        - ROS_TO_HARDWARE_OFFSET_RAD
    )


def within_safe_limits(joints: ArrayLike, tolerance: float = 0.0) -> bool:
    values = _joint_vector(joints)
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be a finite non-negative value")
    return bool(
        np.all(values >= SAFE_JOINT_LIMITS_RAD[:, 0] - tolerance)
        and np.all(values <= SAFE_JOINT_LIMITS_RAD[:, 1] + tolerance)
    )


def clamp_to_safe_limits(joints: ArrayLike) -> FloatArray:
    values = _joint_vector(joints)
    return np.clip(
        values,
        SAFE_JOINT_LIMITS_RAD[:, 0],
        SAFE_JOINT_LIMITS_RAD[:, 1],
    )


def require_safe_joints(joints: ArrayLike) -> FloatArray:
    values = _joint_vector(joints).copy()
    if not within_safe_limits(values):
        bad = np.flatnonzero(
            (values < SAFE_JOINT_LIMITS_RAD[:, 0])
            | (values > SAFE_JOINT_LIMITS_RAD[:, 1])
        )
        names = ", ".join(DUMMY_JOINT_NAMES[index] for index in bad)
        raise ValueError(f"joint values outside safe limits: {names}")
    return values
