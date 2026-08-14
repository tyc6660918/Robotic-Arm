"""Relative Cartesian mapping and teleoperation safety state handling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag
import math

import numpy as np
from scipy.spatial.transform import Rotation

from .types import MasterState, Pose, TeleopState


class SafetyFault(IntFlag):
    """Bit mask used by :class:`TeleopSafetyStateMachine`."""

    NONE = 0
    INPUT_TIMEOUT = 1 << 0
    INVALID_INPUT = 1 << 1
    TIMESTAMP_ORDER = 1 << 2
    IK_FAILURE = 1 << 3
    JOINT_LIMIT = 1 << 4
    DEADMAN_RELEASED = 1 << 5
    CLUTCH_ACTIVE = 1 << 6
    INTERNAL = 1 << 7
    FEEDBACK_TIMEOUT = 1 << 8
    TRACKING_ERROR = 1 << 9


@dataclass(frozen=True)
class SafetySnapshot:
    """Small immutable result returned on every safety update."""

    state: TeleopState
    message_age: float
    fault_bits: int = 0
    reason: str = ""

    @property
    def motion_allowed(self) -> bool:
        return self.state is TeleopState.TELEOP


class TeleopMapper:
    """Map master motion relative to a captured master/slave pose pair.

    Translation is expressed in the captured master frame and replayed in the
    captured slave frame. Rotation is computed with SO(3) log/exp operations,
    avoiding Euler-angle discontinuities.
    """

    def __init__(
        self,
        translation_scale: float = 0.3,
        rotation_scale: float = 0.5,
        axis_map: np.ndarray | None = None,
    ) -> None:
        if not math.isfinite(translation_scale) or translation_scale < 0.0:
            raise ValueError("translation_scale must be finite and non-negative")
        if not math.isfinite(rotation_scale) or rotation_scale < 0.0:
            raise ValueError("rotation_scale must be finite and non-negative")

        mapping = np.eye(3) if axis_map is None else np.asarray(axis_map, dtype=float)
        if mapping.shape != (3, 3) or not np.all(np.isfinite(mapping)):
            raise ValueError("axis_map must be a finite 3x3 matrix")
        if not np.allclose(mapping.T @ mapping, np.eye(3), atol=1e-9):
            raise ValueError("axis_map must be orthonormal")
        if np.linalg.det(mapping) < 0.0:
            raise ValueError("axis_map must be a proper rotation")

        self.translation_scale = float(translation_scale)
        self.rotation_scale = float(rotation_scale)
        self.axis_map = mapping.copy()
        self._master_reference: np.ndarray | None = None
        self._slave_reference: np.ndarray | None = None
        self._last_target: Pose | None = None
        self._clutch_active = False

    @property
    def captured(self) -> bool:
        return self._master_reference is not None

    @property
    def clutch_active(self) -> bool:
        return self._clutch_active

    @property
    def last_target(self) -> Pose | None:
        return None if self._last_target is None else self._last_target.copy()

    def clear(self) -> None:
        self._master_reference = None
        self._slave_reference = None
        self._last_target = None
        self._clutch_active = False

    def capture(self, master_pose: Pose, slave_pose: Pose) -> Pose:
        """Capture a new relative-motion origin and return a zero-jump target."""

        self._master_reference = master_pose.as_matrix()
        self._slave_reference = slave_pose.as_matrix()
        self._last_target = slave_pose.copy()
        return self._last_target.copy()

    def map_pose(self, master_pose: Pose) -> Pose:
        """Map a pose using the current references without changing state."""

        if self._master_reference is None or self._slave_reference is None:
            raise RuntimeError("capture() must be called before map_pose()")

        master = master_pose.as_matrix()
        master_ref = self._master_reference
        slave_ref = self._slave_reference

        master_delta_local = master_ref[:3, :3].T @ (
            master[:3, 3] - master_ref[:3, 3]
        )
        slave_delta_local = (
            self.translation_scale * self.axis_map @ master_delta_local
        )

        master_rotation_delta = master_ref[:3, :3].T @ master[:3, :3]
        rotation_vector = Rotation.from_matrix(master_rotation_delta).as_rotvec()
        slave_rotation_delta = Rotation.from_rotvec(
            self.rotation_scale * self.axis_map @ rotation_vector
        ).as_matrix()

        target = slave_ref.copy()
        target[:3, 3] = (
            slave_ref[:3, 3] + slave_ref[:3, :3] @ slave_delta_local
        )
        target[:3, :3] = slave_ref[:3, :3] @ slave_rotation_delta
        return Pose.from_matrix(target)

    def update(
        self,
        master_pose: Pose,
        slave_pose: Pose,
        clutch: bool = False,
    ) -> Pose:
        """Update the mapper, applying clutch capture and hold semantics."""

        if not self.captured:
            self._clutch_active = bool(clutch)
            return self.capture(master_pose, slave_pose)

        if clutch:
            if not self._clutch_active:
                # Command the current feedback pose so the plant stops promptly.
                self._last_target = slave_pose.copy()
            self._clutch_active = True
            return self._last_target.copy()

        if self._clutch_active:
            self._clutch_active = False
            return self.capture(master_pose, slave_pose)

        self._last_target = self.map_pose(master_pose)
        return self._last_target.copy()

    def update_master(self, master: MasterState, slave_pose: Pose) -> Pose:
        return self.update(master.flange_pose, slave_pose, clutch=master.clutch)


class TeleopSafetyStateMachine:
    """Deadman/watchdog state machine with explicit recovery after a hold."""

    def __init__(self, input_timeout: float = 0.05) -> None:
        if not math.isfinite(input_timeout) or input_timeout <= 0.0:
            raise ValueError("input_timeout must be finite and positive")
        self.input_timeout = float(input_timeout)
        self.state = TeleopState.DISABLED
        self._last_input_timestamp: float | None = None
        self._needs_rearm = False
        self._rearm_seen = False
        self._latched_fault_bits = int(SafetyFault.NONE)
        self._latched_fault_reason = ""

    def enable(self) -> SafetySnapshot:
        self.state = TeleopState.READY
        self._last_input_timestamp = None
        self._needs_rearm = False
        self._rearm_seen = False
        self._latched_fault_bits = int(SafetyFault.NONE)
        self._latched_fault_reason = ""
        return SafetySnapshot(self.state, math.inf)

    def disable(self) -> SafetySnapshot:
        self.state = TeleopState.DISABLED
        self._last_input_timestamp = None
        self._needs_rearm = False
        self._rearm_seen = False
        self._latched_fault_bits = int(SafetyFault.NONE)
        self._latched_fault_reason = ""
        return SafetySnapshot(self.state, math.inf)

    def fault(self, reason: str, fault_bits: int = int(SafetyFault.INTERNAL)) -> SafetySnapshot:
        self.state = TeleopState.FAULT
        self._needs_rearm = True
        self._rearm_seen = False
        self._latched_fault_bits = int(fault_bits)
        self._latched_fault_reason = str(reason)
        return SafetySnapshot(
            self.state,
            math.inf,
            self._latched_fault_bits,
            self._latched_fault_reason,
        )

    def clear_fault(self) -> SafetySnapshot:
        if self.state is not TeleopState.FAULT:
            raise RuntimeError("clear_fault() is only valid in FAULT")
        self.state = TeleopState.READY
        self._needs_rearm = True
        self._rearm_seen = False
        self._latched_fault_bits = int(SafetyFault.NONE)
        self._latched_fault_reason = ""
        return SafetySnapshot(self.state, math.inf, reason="rearm required")

    def require_rearm(self, reason: str = "rearm required") -> SafetySnapshot:
        """Enter HOLD without accepting a synthetic input as the rearm edge."""

        return self._hold(0.0, SafetyFault.NONE, str(reason), reset_observed=False)

    def _hold(
        self,
        age: float,
        fault: SafetyFault,
        reason: str,
        reset_observed: bool = False,
    ) -> SafetySnapshot:
        if self.state is not TeleopState.HOLD:
            self._rearm_seen = False
        self.state = TeleopState.HOLD
        self._needs_rearm = True
        self._rearm_seen = self._rearm_seen or reset_observed
        return SafetySnapshot(self.state, age, int(fault), reason)

    def update(
        self,
        now: float,
        input_timestamp: float,
        deadman: bool,
        clutch: bool,
        *,
        validity_flags: int = 1,
        ik_success: bool = True,
        joints_within_limits: bool = True,
        feedback_fresh: bool = True,
        tracking_ok: bool = True,
    ) -> SafetySnapshot:
        if self.state is TeleopState.DISABLED:
            return SafetySnapshot(self.state, math.inf, reason="disabled")
        if self.state is TeleopState.FAULT:
            return SafetySnapshot(
                self.state,
                math.inf,
                self._latched_fault_bits,
                self._latched_fault_reason or "fault must be cleared explicitly",
            )
        if not math.isfinite(now) or not math.isfinite(input_timestamp):
            return self.fault("non-finite clock or input timestamp")

        if input_timestamp > now + 1e-9:
            return self._hold(
                0.0,
                SafetyFault.TIMESTAMP_ORDER,
                "input timestamp is in the future",
                reset_observed=False,
            )
        age = max(0.0, float(now) - float(input_timestamp))
        if (
            self._last_input_timestamp is not None
            and input_timestamp < self._last_input_timestamp - 1e-12
        ):
            return self._hold(
                age,
                SafetyFault.TIMESTAMP_ORDER,
                "out-of-order input timestamp",
                reset_observed=False,
            )

        if validity_flags == 0:
            return self._hold(
                age,
                SafetyFault.INVALID_INPUT,
                "master input is invalid",
                reset_observed=False,
            )
        if age > self.input_timeout:
            return self._hold(
                age,
                SafetyFault.INPUT_TIMEOUT,
                "master input timed out",
                reset_observed=False,
            )
        self._last_input_timestamp = float(input_timestamp)
        if not feedback_fresh:
            return self._hold(
                age,
                SafetyFault.FEEDBACK_TIMEOUT,
                "robot feedback timed out",
                reset_observed=False,
            )
        if not tracking_ok:
            return self._hold(
                age,
                SafetyFault.TRACKING_ERROR,
                "joint tracking error persisted",
                reset_observed=False,
            )
        if not ik_success:
            return self._hold(
                age,
                SafetyFault.IK_FAILURE,
                "inverse kinematics failed",
                reset_observed=False,
            )
        if not joints_within_limits:
            return self._hold(
                age,
                SafetyFault.JOINT_LIMIT,
                "joint target is outside the safe limits",
                reset_observed=False,
            )

        if not deadman:
            if self.state is TeleopState.READY and not self._needs_rearm:
                return SafetySnapshot(self.state, age, reason="waiting for deadman")
            return self._hold(
                age,
                SafetyFault.DEADMAN_RELEASED,
                "deadman released",
                reset_observed=True,
            )
        if clutch:
            return self._hold(
                age,
                SafetyFault.CLUTCH_ACTIVE,
                "clutch active",
                reset_observed=True,
            )

        if self._needs_rearm and not self._rearm_seen:
            return self._hold(age, SafetyFault.NONE, "rearm required")

        self.state = TeleopState.TELEOP
        self._needs_rearm = False
        self._rearm_seen = False
        return SafetySnapshot(self.state, age)

    def update_master(
        self,
        master: MasterState,
        now: float,
        *,
        ik_success: bool = True,
        joints_within_limits: bool = True,
        feedback_fresh: bool = True,
        tracking_ok: bool = True,
    ) -> SafetySnapshot:
        return self.update(
            now,
            master.timestamp,
            master.deadman,
            master.clutch,
            validity_flags=master.validity_flags,
            ik_success=ik_success,
            joints_within_limits=joints_within_limits,
            feedback_fresh=feedback_fresh,
            tracking_ok=tracking_ok,
        )
