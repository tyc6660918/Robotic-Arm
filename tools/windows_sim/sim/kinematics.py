"""Homogeneous-transform forward kinematics for the Dummy arm."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.spatial.transform import Rotation

from .hardware_mapping import (
    DUMMY_JOINT_NAMES,
    SAFE_JOINT_LIMITS_RAD,
    require_safe_joints,
)
from .types import Pose
from .urdf_model import Joint, URDFModel, load_dummy_urdf, parse_urdf


FloatArray = NDArray[np.float64]


def _skew_symmetric(vector: ArrayLike) -> FloatArray:
    values = np.asarray(vector, dtype=float)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise ValueError("vector must be finite with shape (3,)")
    x, y, z = values
    return np.array(
        [[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]],
        dtype=float,
    )


def so3_right_jacobian_inverse(rotation_vector: ArrayLike) -> FloatArray:
    """Return the inverse SO(3) right Jacobian for a rotation vector."""

    vector = np.asarray(rotation_vector, dtype=float)
    if vector.shape != (3,) or not np.all(np.isfinite(vector)):
        raise ValueError("rotation_vector must be finite with shape (3,)")
    skew = _skew_symmetric(vector)
    angle_squared = float(vector @ vector)
    if angle_squared < 1e-10:
        # The next non-zero coefficient is angle_squared / 720. Retaining it
        # avoids cancellation while keeping derivatives smooth at zero.
        coefficient = 1.0 / 12.0 + angle_squared / 720.0
    else:
        angle = float(np.sqrt(angle_squared))
        coefficient = (1.0 - 0.5 * angle / np.tan(0.5 * angle)) / angle_squared
    return np.eye(3, dtype=float) + 0.5 * skew + coefficient * (skew @ skew)


def _validate_transform(transform: ArrayLike) -> FloatArray:
    result = np.asarray(transform, dtype=float)
    if result.shape != (4, 4):
        raise ValueError(f"transform must have shape (4, 4), got {result.shape}")
    if not np.all(np.isfinite(result)):
        raise ValueError("transform must contain only finite values")
    if not np.allclose(result[3], [0.0, 0.0, 0.0, 1.0], atol=1e-10):
        raise ValueError("transform has an invalid homogeneous bottom row")
    rotation = result[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-8):
        raise ValueError("transform rotation is not orthonormal")
    if not np.isclose(np.linalg.det(rotation), 1.0, atol=1e-8):
        raise ValueError("transform rotation must have determinant +1")
    return result


def transform_from_xyz_rpy(xyz: ArrayLike, rpy: ArrayLike) -> FloatArray:
    xyz_array = np.asarray(xyz, dtype=float)
    rpy_array = np.asarray(rpy, dtype=float)
    if xyz_array.shape != (3,) or rpy_array.shape != (3,):
        raise ValueError("xyz and rpy must each have shape (3,)")
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = Rotation.from_euler("xyz", rpy_array).as_matrix()
    transform[:3, 3] = xyz_array
    return transform


def rotation_transform(axis: ArrayLike, angle: float) -> FloatArray:
    axis_array = np.asarray(axis, dtype=float)
    if axis_array.shape != (3,) or not np.all(np.isfinite(axis_array)):
        raise ValueError("axis must be a finite vector with shape (3,)")
    norm = float(np.linalg.norm(axis_array))
    if norm <= np.finfo(float).eps or not np.isfinite(angle):
        raise ValueError("axis must be non-zero and angle must be finite")
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = Rotation.from_rotvec(axis_array / norm * angle).as_matrix()
    return transform


def translation_transform(axis: ArrayLike, distance: float) -> FloatArray:
    axis_array = np.asarray(axis, dtype=float)
    norm = float(np.linalg.norm(axis_array))
    if axis_array.shape != (3,) or norm <= np.finfo(float).eps:
        raise ValueError("axis must be a non-zero vector with shape (3,)")
    if not np.isfinite(distance):
        raise ValueError("distance must be finite")
    transform = np.eye(4, dtype=float)
    transform[:3, 3] = axis_array / norm * distance
    return transform


def pose_to_matrix(pose: Pose) -> FloatArray:
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = Rotation.from_quat(pose.orientation).as_matrix()
    transform[:3, 3] = pose.position
    return transform


def matrix_to_pose(transform: ArrayLike) -> Pose:
    matrix = _validate_transform(transform)
    return Pose(matrix[:3, 3].copy(), Rotation.from_matrix(matrix[:3, :3]).as_quat())


def rotation_error_vector(target: ArrayLike, actual: ArrayLike) -> FloatArray:
    target_matrix = _validate_transform(target)
    actual_matrix = _validate_transform(actual)
    delta = target_matrix[:3, :3] @ actual_matrix[:3, :3].T
    return Rotation.from_matrix(delta).as_rotvec()


class SerialKinematics:
    """A serial URDF chain with complete 4x4 link transforms."""

    def __init__(
        self,
        model: URDFModel,
        base_link: str,
        tip_link: str,
        lower_limits: ArrayLike | None = None,
        upper_limits: ArrayLike | None = None,
    ) -> None:
        self.model = model
        self.base_link = base_link
        self.tip_link = tip_link
        self.chain: tuple[Joint, ...] = model.chain(base_link, tip_link)
        self.movable_joints: tuple[Joint, ...] = tuple(
            joint for joint in self.chain if joint.movable
        )
        self.joint_names = tuple(joint.name for joint in self.movable_joints)
        if not self.movable_joints:
            raise ValueError("kinematic chain contains no movable joints")
        self._origin_transforms = tuple(
            transform_from_xyz_rpy(joint.origin_xyz, joint.origin_rpy)
            for joint in self.chain
        )
        normalized_axes: list[FloatArray] = []
        for joint in self.chain:
            axis = np.asarray(joint.axis, dtype=float)
            norm = float(np.linalg.norm(axis))
            if joint.movable and (
                axis.shape != (3,) or not np.all(np.isfinite(axis)) or norm <= 0.0
            ):
                raise ValueError(f"joint {joint.name!r} has an invalid motion axis")
            normalized_axes.append(
                axis / norm if joint.movable else np.zeros(3, dtype=float)
            )
        self._normalized_axes = tuple(normalized_axes)

        parsed_lower = np.array(
            [
                -np.pi if joint.limit is None else joint.limit.lower
                for joint in self.movable_joints
            ],
            dtype=float,
        )
        parsed_upper = np.array(
            [
                np.pi if joint.limit is None else joint.limit.upper
                for joint in self.movable_joints
            ],
            dtype=float,
        )
        self.lower_limits = self._joint_vector(
            parsed_lower if lower_limits is None else lower_limits,
            "lower_limits",
        )
        self.upper_limits = self._joint_vector(
            parsed_upper if upper_limits is None else upper_limits,
            "upper_limits",
        )
        if np.any(self.lower_limits >= self.upper_limits):
            raise ValueError("each lower joint limit must be below its upper limit")

    @classmethod
    def from_urdf(
        cls,
        path: str | Path,
        base_link: str,
        tip_link: str,
        lower_limits: ArrayLike | None = None,
        upper_limits: ArrayLike | None = None,
    ) -> "SerialKinematics":
        return cls(
            parse_urdf(path),
            base_link,
            tip_link,
            lower_limits,
            upper_limits,
        )

    @property
    def dof(self) -> int:
        return len(self.movable_joints)

    @property
    def joint_center(self) -> FloatArray:
        return (self.lower_limits + self.upper_limits) * 0.5

    @property
    def joint_range(self) -> FloatArray:
        return self.upper_limits - self.lower_limits

    def _joint_vector(self, joints: ArrayLike, name: str = "joints") -> FloatArray:
        values = np.asarray(joints, dtype=float)
        if values.shape != (len(self.movable_joints),):
            raise ValueError(
                f"{name} must have shape ({len(self.movable_joints)},), got {values.shape}"
            )
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{name} must contain only finite values")
        return values.copy()

    def within_limits(self, joints: ArrayLike, tolerance: float = 0.0) -> bool:
        values = self._joint_vector(joints)
        return bool(
            np.all(values >= self.lower_limits - tolerance)
            and np.all(values <= self.upper_limits + tolerance)
        )

    @staticmethod
    def _joint_motion(joint: Joint, value: float) -> FloatArray:
        if joint.joint_type in {"revolute", "continuous"}:
            return rotation_transform(joint.axis, value)
        if joint.joint_type == "prismatic":
            return translation_transform(joint.axis, value)
        return np.eye(4, dtype=float)

    def forward_all(self, joints: ArrayLike) -> dict[str, FloatArray]:
        """Return base-relative transforms for every link along the chain."""

        values = self._joint_vector(joints)
        transforms: dict[str, FloatArray] = {self.base_link: np.eye(4, dtype=float)}
        transform = np.eye(4, dtype=float)
        movable_index = 0
        for joint, origin_transform in zip(self.chain, self._origin_transforms):
            transform = transform @ origin_transform
            if joint.movable:
                transform = transform @ self._joint_motion(
                    joint, float(values[movable_index])
                )
                movable_index += 1
            transforms[joint.child] = transform.copy()
        return transforms

    def forward(self, joints: ArrayLike) -> FloatArray:
        """Return the base-to-tip 4x4 transform."""

        values = self._joint_vector(joints)
        transform = np.eye(4, dtype=float)
        movable_index = 0
        for joint, origin_transform in zip(self.chain, self._origin_transforms):
            transform = transform @ origin_transform
            if joint.movable:
                transform = transform @ self._joint_motion(
                    joint, float(values[movable_index])
                )
                movable_index += 1
        return transform

    def forward_with_geometric_jacobian(
        self, joints: ArrayLike
    ) -> tuple[FloatArray, FloatArray]:
        """Return the tip transform and 6xN space geometric Jacobian."""

        values = self._joint_vector(joints)
        transform = np.eye(4, dtype=float)
        joint_origins = np.empty((self.dof, 3), dtype=float)
        joint_axes = np.empty((self.dof, 3), dtype=float)
        joint_types: list[str] = []
        movable_index = 0
        for joint, origin_transform, local_axis in zip(
            self.chain, self._origin_transforms, self._normalized_axes
        ):
            transform = transform @ origin_transform
            if not joint.movable:
                continue
            joint_origins[movable_index] = transform[:3, 3]
            joint_axes[movable_index] = transform[:3, :3] @ local_axis
            joint_types.append(joint.joint_type)
            transform = transform @ self._joint_motion(
                joint, float(values[movable_index])
            )
            movable_index += 1

        tip_position = transform[:3, 3]
        jacobian = np.zeros((6, self.dof), dtype=float)
        for index, joint_type in enumerate(joint_types):
            axis = joint_axes[index]
            if joint_type in {"revolute", "continuous"}:
                jacobian[:3, index] = np.cross(
                    axis, tip_position - joint_origins[index]
                )
                jacobian[3:, index] = axis
            elif joint_type == "prismatic":
                jacobian[:3, index] = axis
        return transform, jacobian

    def flange_pose(self, joints: ArrayLike) -> Pose:
        return matrix_to_pose(self.forward(joints))

    def numerical_jacobian(self, joints: ArrayLike, step: float = 1e-7) -> FloatArray:
        """Return a 6xN position/rotation-vector central-difference Jacobian."""

        values = self._joint_vector(joints)
        if not np.isfinite(step) or step <= 0.0:
            raise ValueError("step must be finite and positive")
        jacobian = np.empty((6, self.dof), dtype=float)
        for index in range(self.dof):
            plus = values.copy()
            minus = values.copy()
            plus[index] += step
            minus[index] -= step
            forward_plus = self.forward(plus)
            forward_minus = self.forward(minus)
            jacobian[:3, index] = (
                forward_plus[:3, 3] - forward_minus[:3, 3]
            ) / (2.0 * step)
            jacobian[3:, index] = rotation_error_vector(
                forward_plus, forward_minus
            ) / (2.0 * step)
        return jacobian


def create_dummy_kinematics(path: str | Path | None = None) -> SerialKinematics:
    model = load_dummy_urdf(path)
    kinematics = SerialKinematics(
        model,
        base_link="base_link",
        tip_link="link6_1_1",
        lower_limits=SAFE_JOINT_LIMITS_RAD[:, 0],
        upper_limits=SAFE_JOINT_LIMITS_RAD[:, 1],
    )
    if kinematics.joint_names != DUMMY_JOINT_NAMES:
        raise ValueError(
            "Dummy URDF joint order changed: "
            f"expected {DUMMY_JOINT_NAMES}, got {kinematics.joint_names}"
        )
    return kinematics


def dummy_forward_kinematics(joints: ArrayLike) -> Mapping[str, FloatArray]:
    """Convenience one-shot FK using the repository's static Dummy URDF."""

    require_safe_joints(joints)
    return create_dummy_kinematics().forward_all(joints)
