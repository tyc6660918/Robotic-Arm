"""Low-latency pose filtering and Cartesian motion limiting."""

from __future__ import annotations

import math

import numpy as np
from scipy.spatial.transform import Rotation

from .types import Pose


def _alpha(cutoff: float | np.ndarray, dt: float) -> float | np.ndarray:
    cutoff_array = np.asarray(cutoff, dtype=float)
    if np.any(~np.isfinite(cutoff_array)) or np.any(cutoff_array <= 0.0):
        raise ValueError("cutoff frequency must be finite and positive")
    tau = 1.0 / (2.0 * np.pi * cutoff_array)
    result = 1.0 / (1.0 + tau / dt)
    return float(result) if result.ndim == 0 else result


def _limit_norm(value: np.ndarray, maximum: float) -> np.ndarray:
    norm = float(np.linalg.norm(value))
    if norm <= maximum or norm <= np.finfo(float).eps:
        return value
    return value * (maximum / norm)


def _braking_velocity(
    error: np.ndarray,
    maximum_speed: float,
    maximum_acceleration: float,
    dt: float,
) -> np.ndarray:
    distance = float(np.linalg.norm(error))
    if distance <= np.finfo(float).eps:
        return np.zeros_like(error)
    acceleration_step = maximum_acceleration * dt
    stopping_speed = (
        math.sqrt(acceleration_step * acceleration_step + 2.0 * maximum_acceleration * distance)
        - acceleration_step
    )
    speed = min(maximum_speed, stopping_speed)
    return error * (speed / distance)


class OneEuroFilter:
    """One Euro filter for a scalar or fixed-size NumPy vector."""

    def __init__(
        self,
        min_cutoff: float = 2.0,
        beta: float = 0.05,
        derivative_cutoff: float = 1.0,
    ) -> None:
        if not math.isfinite(min_cutoff) or min_cutoff <= 0.0:
            raise ValueError("min_cutoff must be finite and positive")
        if not math.isfinite(beta) or beta < 0.0:
            raise ValueError("beta must be finite and non-negative")
        if not math.isfinite(derivative_cutoff) or derivative_cutoff <= 0.0:
            raise ValueError("derivative_cutoff must be finite and positive")
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.derivative_cutoff = float(derivative_cutoff)
        self._raw: np.ndarray | None = None
        self._filtered: np.ndarray | None = None
        self._derivative: np.ndarray | None = None
        self._timestamp: float | None = None

    @property
    def initialized(self) -> bool:
        return self._filtered is not None

    def reset(
        self,
        value: float | np.ndarray | None = None,
        timestamp: float | None = None,
    ) -> None:
        self._raw = None
        self._filtered = None
        self._derivative = None
        self._timestamp = None
        if value is not None:
            self.filter(value, 0.0 if timestamp is None else timestamp)

    def filter(
        self,
        value: float | np.ndarray,
        timestamp: float,
    ) -> float | np.ndarray:
        sample = np.asarray(value, dtype=float)
        if np.any(~np.isfinite(sample)) or not math.isfinite(timestamp):
            raise ValueError("filter samples and timestamps must be finite")

        if self._filtered is None:
            self._raw = sample.copy()
            self._filtered = sample.copy()
            self._derivative = np.zeros_like(sample)
            self._timestamp = float(timestamp)
            return self._format_result(self._filtered)

        if sample.shape != self._filtered.shape:
            raise ValueError("sample shape changed after filter initialization")
        dt = float(timestamp) - self._timestamp
        if dt < 0.0:
            raise ValueError("timestamps must be monotonic")
        if dt == 0.0:
            return self._format_result(self._filtered)

        raw_derivative = (sample - self._raw) / dt
        derivative_alpha = _alpha(self.derivative_cutoff, dt)
        self._derivative += derivative_alpha * (
            raw_derivative - self._derivative
        )
        cutoff = self.min_cutoff + self.beta * np.abs(self._derivative)
        value_alpha = _alpha(cutoff, dt)
        self._filtered += value_alpha * (sample - self._filtered)
        self._raw = sample.copy()
        self._timestamp = float(timestamp)
        return self._format_result(self._filtered)

    update = filter

    @staticmethod
    def _format_result(value: np.ndarray) -> float | np.ndarray:
        if value.ndim == 0:
            return float(value)
        return value.copy()


class OneEuroPoseFilter:
    """One Euro filter for position and quaternion orientation."""

    def __init__(
        self,
        position_min_cutoff: float = 2.0,
        position_beta: float = 0.05,
        orientation_min_cutoff: float = 2.0,
        orientation_beta: float = 0.05,
        derivative_cutoff: float = 1.0,
    ) -> None:
        self._position = OneEuroFilter(
            position_min_cutoff,
            position_beta,
            derivative_cutoff,
        )
        if not math.isfinite(orientation_min_cutoff) or orientation_min_cutoff <= 0.0:
            raise ValueError("orientation_min_cutoff must be finite and positive")
        if not math.isfinite(orientation_beta) or orientation_beta < 0.0:
            raise ValueError("orientation_beta must be finite and non-negative")
        if not math.isfinite(derivative_cutoff) or derivative_cutoff <= 0.0:
            raise ValueError("derivative_cutoff must be finite and positive")
        self.orientation_min_cutoff = float(orientation_min_cutoff)
        self.orientation_beta = float(orientation_beta)
        self.derivative_cutoff = float(derivative_cutoff)
        self._raw_rotation: Rotation | None = None
        self._filtered_rotation: Rotation | None = None
        self._angular_velocity = np.zeros(3, dtype=float)
        self._timestamp: float | None = None

    @property
    def initialized(self) -> bool:
        return self._filtered_rotation is not None

    def reset(self, pose: Pose | None = None, timestamp: float | None = None) -> None:
        self._position.reset()
        self._raw_rotation = None
        self._filtered_rotation = None
        self._angular_velocity = np.zeros(3, dtype=float)
        self._timestamp = None
        if pose is not None:
            self.filter(pose, 0.0 if timestamp is None else timestamp)

    def filter(self, pose: Pose, timestamp: float) -> Pose:
        if not math.isfinite(timestamp):
            raise ValueError("timestamp must be finite")
        raw_rotation = Rotation.from_quat(pose.orientation)

        if self._filtered_rotation is None:
            position = self._position.filter(pose.position, timestamp)
            self._raw_rotation = raw_rotation
            self._filtered_rotation = raw_rotation
            self._timestamp = float(timestamp)
            return Pose(position, raw_rotation.as_quat())

        dt = float(timestamp) - self._timestamp
        if dt < 0.0:
            raise ValueError("timestamps must be monotonic")
        if dt == 0.0:
            return Pose(
                self._position.filter(pose.position, timestamp),
                self._filtered_rotation.as_quat(),
            )

        position = self._position.filter(pose.position, timestamp)
        raw_delta = (self._raw_rotation.inv() * raw_rotation).as_rotvec()
        raw_angular_velocity = raw_delta / dt
        derivative_alpha = _alpha(self.derivative_cutoff, dt)
        self._angular_velocity += derivative_alpha * (
            raw_angular_velocity - self._angular_velocity
        )
        cutoff = self.orientation_min_cutoff + (
            self.orientation_beta * np.linalg.norm(self._angular_velocity)
        )
        orientation_alpha = _alpha(cutoff, dt)
        filter_delta = (
            self._filtered_rotation.inv() * raw_rotation
        ).as_rotvec()
        self._filtered_rotation = self._filtered_rotation * Rotation.from_rotvec(
            orientation_alpha * filter_delta
        )
        self._raw_rotation = raw_rotation
        self._timestamp = float(timestamp)
        return Pose(position, self._filtered_rotation.as_quat())

    update = filter


class PoseRateLimiter:
    """Limit Cartesian velocity and acceleration without Euler angles."""

    def __init__(
        self,
        max_linear_speed: float = 0.05,
        max_angular_speed: float = 0.5,
        max_linear_acceleration: float = 0.2,
        max_angular_acceleration: float = 2.0,
    ) -> None:
        values = (
            max_linear_speed,
            max_angular_speed,
            max_linear_acceleration,
            max_angular_acceleration,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError("all motion limits must be finite and positive")
        self.max_linear_speed = float(max_linear_speed)
        self.max_angular_speed = float(max_angular_speed)
        self.max_linear_acceleration = float(max_linear_acceleration)
        self.max_angular_acceleration = float(max_angular_acceleration)
        self._pose: Pose | None = None
        self._linear_velocity = np.zeros(3, dtype=float)
        self._angular_velocity = np.zeros(3, dtype=float)

    @property
    def initialized(self) -> bool:
        return self._pose is not None

    def reset(self, pose: Pose | None = None) -> None:
        self._pose = None if pose is None else pose.copy()
        self._linear_velocity = np.zeros(3, dtype=float)
        self._angular_velocity = np.zeros(3, dtype=float)

    def synchronize(self, pose: Pose, *, preserve_velocity: bool = True) -> None:
        """Align the limiter with a downstream-achievable pose.

        This keeps a joint-limited command from building a Cartesian backlog.
        """

        self._pose = pose.copy()
        if not preserve_velocity:
            self._linear_velocity.fill(0.0)
            self._angular_velocity.fill(0.0)

    def update(self, target: Pose, dt: float) -> Pose:
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be finite and positive")
        if self._pose is None:
            self.reset(target)
            return target.copy()

        current_rotation = Rotation.from_quat(self._pose.orientation)
        target_rotation = Rotation.from_quat(target.orientation)

        position_error = target.position - self._pose.position
        desired_linear_velocity = _braking_velocity(
            position_error,
            self.max_linear_speed,
            self.max_linear_acceleration,
            dt,
        )
        linear_acceleration = _limit_norm(
            (desired_linear_velocity - self._linear_velocity) / dt,
            self.max_linear_acceleration,
        )
        self._linear_velocity += linear_acceleration * dt
        self._linear_velocity = _limit_norm(
            self._linear_velocity,
            self.max_linear_speed,
        )

        rotation_error = (current_rotation.inv() * target_rotation).as_rotvec()
        desired_angular_velocity = _braking_velocity(
            rotation_error,
            self.max_angular_speed,
            self.max_angular_acceleration,
            dt,
        )
        angular_acceleration = _limit_norm(
            (desired_angular_velocity - self._angular_velocity) / dt,
            self.max_angular_acceleration,
        )
        self._angular_velocity += angular_acceleration * dt
        self._angular_velocity = _limit_norm(
            self._angular_velocity,
            self.max_angular_speed,
        )

        linear_step = self._linear_velocity * dt
        angular_step = self._angular_velocity * dt
        position = self._pose.position + linear_step
        rotation = current_rotation * Rotation.from_rotvec(angular_step)

        # The discrete braking profile reaches the target with a velocity that
        # can be removed in one acceleration-limited sample.
        if (
            np.linalg.norm(position_error) <= self.max_linear_acceleration * dt * dt
            and np.linalg.norm(self._linear_velocity)
            <= self.max_linear_acceleration * dt + 1e-12
        ):
            position = target.position.copy()
            self._linear_velocity.fill(0.0)
        if (
            np.linalg.norm(rotation_error) <= self.max_angular_acceleration * dt * dt
            and np.linalg.norm(self._angular_velocity)
            <= self.max_angular_acceleration * dt + 1e-12
        ):
            rotation = target_rotation
            self._angular_velocity.fill(0.0)

        self._pose = Pose(position, rotation.as_quat())
        return self._pose.copy()
