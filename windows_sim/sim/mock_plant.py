"""Deterministic joint-space plant with bounded dynamics and fault injection."""

from __future__ import annotations

from dataclasses import dataclass, field
import math

import numpy as np

from .types import Pose, RobotState


_DEFAULT_LOWER = np.deg2rad([-170.0, -73.0, -55.0, -180.0, -90.0, -180.0])
_DEFAULT_UPPER = np.deg2rad([170.0, 90.0, 90.0, 180.0, 90.0, 180.0])


def _vector(value: float | np.ndarray, size: int, name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.ndim == 0:
        array = np.full(size, float(array), dtype=float)
    if array.shape != (size,) or np.any(~np.isfinite(array)):
        raise ValueError(f"{name} must be a finite scalar or length-{size} vector")
    return array.copy()


@dataclass
class PlantConfig:
    lower_limits: np.ndarray = field(default_factory=lambda: _DEFAULT_LOWER.copy())
    upper_limits: np.ndarray = field(default_factory=lambda: _DEFAULT_UPPER.copy())
    velocity_limits: float | np.ndarray = 1.0
    acceleration_limits: float | np.ndarray = 4.0
    jerk_limits: float | np.ndarray = 40.0
    response_time: float = 0.1

    def __post_init__(self) -> None:
        self.lower_limits = np.asarray(self.lower_limits, dtype=float).copy()
        self.upper_limits = np.asarray(self.upper_limits, dtype=float).copy()
        if (
            self.lower_limits.ndim != 1
            or self.lower_limits.shape != self.upper_limits.shape
            or np.any(~np.isfinite(self.lower_limits))
            or np.any(~np.isfinite(self.upper_limits))
            or np.any(self.lower_limits >= self.upper_limits)
        ):
            raise ValueError("joint limits must be finite, ordered vectors")
        size = self.lower_limits.size
        self.velocity_limits = _vector(self.velocity_limits, size, "velocity_limits")
        self.acceleration_limits = _vector(
            self.acceleration_limits,
            size,
            "acceleration_limits",
        )
        self.jerk_limits = _vector(self.jerk_limits, size, "jerk_limits")
        if (
            np.any(self.velocity_limits <= 0.0)
            or np.any(self.acceleration_limits <= 0.0)
            or np.any(self.jerk_limits <= 0.0)
        ):
            raise ValueError("dynamic limits must be positive")
        if not math.isfinite(self.response_time) or self.response_time <= 0.0:
            raise ValueError("response_time must be finite and positive")
        self.response_time = float(self.response_time)


@dataclass
class FaultConfig:
    command_delay: float = 0.0
    command_drop_probability: float = 0.0
    feedback_noise_std: float | np.ndarray = 0.0
    feedback_drop_probability: float = 0.0
    feedback_frozen: bool = False
    stuck_joints: tuple[int, ...] = ()

    def validate(self, joint_count: int) -> None:
        if not math.isfinite(self.command_delay) or self.command_delay < 0.0:
            raise ValueError("command_delay must be finite and non-negative")
        for name, probability in (
            ("command_drop_probability", self.command_drop_probability),
            ("feedback_drop_probability", self.feedback_drop_probability),
        ):
            if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        noise = _vector(self.feedback_noise_std, joint_count, "feedback_noise_std")
        if np.any(noise < 0.0):
            raise ValueError("feedback_noise_std must be non-negative")
        invalid = [index for index in self.stuck_joints if not 0 <= index < joint_count]
        if invalid:
            raise ValueError(f"stuck joint indices out of range: {invalid}")


@dataclass(frozen=True)
class PlantState:
    timestamp: float
    positions: np.ndarray
    velocities: np.ndarray
    accelerations: np.ndarray
    target_positions: np.ndarray


class MockJointPlant:
    """Jerk-limited first-order joint servo with a latest-only command slot."""

    def __init__(
        self,
        config: PlantConfig | None = None,
        initial_positions: np.ndarray | None = None,
        faults: FaultConfig | None = None,
        random_seed: int | None = 0,
    ) -> None:
        self.config = PlantConfig() if config is None else config
        self.joint_count = self.config.lower_limits.size
        if initial_positions is None:
            initial = np.clip(
                np.zeros(self.joint_count, dtype=float),
                self.config.lower_limits,
                self.config.upper_limits,
            )
        else:
            initial = _vector(initial_positions, self.joint_count, "initial_positions")
            if np.any(initial < self.config.lower_limits) or np.any(
                initial > self.config.upper_limits
            ):
                raise ValueError("initial_positions violate joint limits")

        self.positions = initial.copy()
        self.velocities = np.zeros(self.joint_count, dtype=float)
        self.accelerations = np.zeros(self.joint_count, dtype=float)
        self.target_positions = initial.copy()
        self.time = 0.0
        self.last_command_was_clipped = False
        self.accepted_command_count = 0
        self.dropped_command_count = 0
        self.dropped_feedback_count = 0

        self.faults = FaultConfig() if faults is None else faults
        self.faults.validate(self.joint_count)
        self._rng = np.random.default_rng(random_seed)
        self._pending_target: np.ndarray | None = None
        self._pending_due: float | None = None
        self._frozen_feedback: PlantState | None = None

    @property
    def has_pending_command(self) -> bool:
        return self._pending_target is not None

    def configure_faults(self, faults: FaultConfig) -> None:
        faults.validate(self.joint_count)
        was_frozen = self.faults.feedback_frozen
        self.faults = faults
        if was_frozen and not faults.feedback_frozen:
            self._frozen_feedback = None

    def set_stuck_joint(self, index: int, stuck: bool = True) -> None:
        if not 0 <= index < self.joint_count:
            raise IndexError("joint index out of range")
        stuck_joints = set(self.faults.stuck_joints)
        if stuck:
            stuck_joints.add(index)
        else:
            stuck_joints.discard(index)
        self.faults.stuck_joints = tuple(sorted(stuck_joints))

    def set_target(
        self,
        target_positions: np.ndarray,
        timestamp: float | None = None,
    ) -> bool:
        command_time = self.time if timestamp is None else float(timestamp)
        if not math.isfinite(command_time):
            raise ValueError("command timestamp must be finite")
        command = _vector(target_positions, self.joint_count, "target_positions")
        if self._rng.random() < self.faults.command_drop_probability:
            self.dropped_command_count += 1
            return False

        clipped = np.clip(
            command,
            self.config.lower_limits,
            self.config.upper_limits,
        )
        self.last_command_was_clipped = not np.array_equal(command, clipped)
        self.accepted_command_count += 1

        if self.faults.command_delay <= 0.0:
            self.target_positions = clipped
            self._pending_target = None
            self._pending_due = None
        else:
            self._pending_target = clipped
            # Replacing a pending value does not postpone its delivery. This
            # preserves a depth-one buffer even under a continuous command rate.
            if self._pending_due is None:
                self._pending_due = command_time + self.faults.command_delay
        return True

    command = set_target

    def _activate_pending(self) -> None:
        if (
            self._pending_target is not None
            and self._pending_due is not None
            and self.time >= self._pending_due
        ):
            self.target_positions = self._pending_target
            self._pending_target = None
            self._pending_due = None

    def step(self, dt: float, timestamp: float | None = None) -> PlantState:
        if not math.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt must be finite and positive")
        next_time = self.time + dt if timestamp is None else float(timestamp)
        if not math.isfinite(next_time) or next_time < self.time:
            raise ValueError("plant timestamps must be finite and monotonic")
        if next_time <= self.time:
            raise ValueError("plant time must advance on every step")
        self.time = next_time
        self._activate_pending()

        error = self.target_positions - self.positions
        desired_velocity = np.clip(
            error / self.config.response_time,
            -self.config.velocity_limits,
            self.config.velocity_limits,
        )
        desired_acceleration = np.clip(
            (desired_velocity - self.velocities) / self.config.response_time,
            -self.config.acceleration_limits,
            self.config.acceleration_limits,
        )
        desired_jerk = np.clip(
            (desired_acceleration - self.accelerations) / dt,
            -self.config.jerk_limits,
            self.config.jerk_limits,
        )

        acceleration = np.clip(
            self.accelerations + desired_jerk * dt,
            -self.config.acceleration_limits,
            self.config.acceleration_limits,
        )
        velocity = np.clip(
            self.velocities + acceleration * dt,
            -self.config.velocity_limits,
            self.config.velocity_limits,
        )
        position = self.positions + velocity * dt

        stuck = np.zeros(self.joint_count, dtype=bool)
        if self.faults.stuck_joints:
            stuck[np.asarray(self.faults.stuck_joints, dtype=int)] = True
            position[stuck] = self.positions[stuck]
            velocity[stuck] = 0.0
            acceleration[stuck] = 0.0

        position = np.clip(
            position,
            self.config.lower_limits,
            self.config.upper_limits,
        )

        self.positions = position
        self.velocities = velocity
        self.accelerations = acceleration
        return self.state()

    update = step

    def state(self) -> PlantState:
        return PlantState(
            self.time,
            self.positions.copy(),
            self.velocities.copy(),
            self.accelerations.copy(),
            self.target_positions.copy(),
        )

    def feedback(self) -> PlantState | None:
        if self._rng.random() < self.faults.feedback_drop_probability:
            self.dropped_feedback_count += 1
            return None

        current = self.state()
        if self.faults.feedback_frozen:
            if self._frozen_feedback is None:
                self._frozen_feedback = current
            current = self._frozen_feedback
        else:
            self._frozen_feedback = None

        noise_std = _vector(
            self.faults.feedback_noise_std,
            self.joint_count,
            "feedback_noise_std",
        )
        noisy_positions = current.positions + self._rng.normal(
            0.0,
            noise_std,
            self.joint_count,
        )
        noisy_positions = np.clip(
            noisy_positions,
            self.config.lower_limits,
            self.config.upper_limits,
        )
        return PlantState(
            current.timestamp,
            noisy_positions,
            current.velocities.copy(),
            current.accelerations.copy(),
            current.target_positions.copy(),
        )

    def robot_state(self, flange_pose: Pose) -> RobotState | None:
        feedback = self.feedback()
        if feedback is None:
            return None
        return RobotState(
            timestamp=feedback.timestamp,
            joint_positions=feedback.positions,
            joint_velocities=feedback.velocities,
            flange_pose=flange_pose,
            target_joint_positions=feedback.target_positions,
        )
