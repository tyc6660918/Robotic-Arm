"""Bounded numerical inverse kinematics with deterministic warm starts."""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import least_squares

from .kinematics import (
    SerialKinematics,
    matrix_to_pose,
    pose_to_matrix,
    rotation_error_vector,
    so3_right_jacobian_inverse,
)
from .types import Pose


FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class IKResult:
    success: bool
    joints: FloatArray
    position_error: float
    orientation_error: float
    function_evaluations: int
    jacobian_evaluations: int
    kinematic_evaluations: int
    attempts: int
    solve_time_s: float
    status: int
    optimality: float
    cost: float
    message: str

    @property
    def iterations(self) -> int:
        """Backward-compatible alias; SciPy reports evaluations, not iterations."""

        return self.function_evaluations


class BoundedIKSolver:
    """SciPy least-squares IK constrained to the chain's safe limits."""

    def __init__(
        self,
        kinematics: SerialKinematics,
        *,
        position_tolerance: float = 1e-4,
        orientation_tolerance: float = np.deg2rad(0.05),
        orientation_weight: float = 1.0,
        centering_weight: float = 1e-10,
        continuity_weight: float = 1e-6,
        max_nfev: int = 15,
        bootstrap_max_nfev: int = 300,
        fallback_starts: int = 12,
    ) -> None:
        if position_tolerance <= 0.0 or orientation_tolerance <= 0.0:
            raise ValueError("IK tolerances must be positive")
        if (
            orientation_weight <= 0.0
            or centering_weight < 0.0
            or continuity_weight < 0.0
        ):
            raise ValueError("IK weights are invalid")
        if max_nfev <= 0:
            raise ValueError("max_nfev must be positive")
        if bootstrap_max_nfev <= 0:
            raise ValueError("bootstrap_max_nfev must be positive")
        if fallback_starts < 0:
            raise ValueError("fallback_starts must be non-negative")
        self.kinematics = kinematics
        self.position_tolerance = float(position_tolerance)
        self.orientation_tolerance = float(orientation_tolerance)
        self.orientation_weight = float(orientation_weight)
        self.centering_weight = float(centering_weight)
        self.continuity_weight = float(continuity_weight)
        self.max_nfev = int(max_nfev)
        self.bootstrap_max_nfev = int(bootstrap_max_nfev)
        self.fallback_starts = int(fallback_starts)
        self._last_solution: FloatArray | None = None

    @property
    def last_solution(self) -> FloatArray | None:
        return None if self._last_solution is None else self._last_solution.copy()

    def reset(self, joints: ArrayLike | None = None) -> None:
        if joints is None:
            self._last_solution = None
            return
        values = self.kinematics._joint_vector(joints, "joints")
        if not self.kinematics.within_limits(values):
            raise ValueError("warm-start joints are outside limits")
        self._last_solution = values

    def solve(
        self,
        target: Pose | ArrayLike,
        initial_guess: ArrayLike | None = None,
    ) -> IKResult:
        solve_started = time.perf_counter()
        target_matrix = (
            pose_to_matrix(target)
            if isinstance(target, Pose)
            else np.asarray(target, dtype=float)
        )
        if target_matrix.shape != (4, 4) or not np.all(np.isfinite(target_matrix)):
            raise ValueError("target must be a Pose or finite 4x4 transform")
        # Validate the homogeneous row and proper rotation before optimization.
        target_matrix = pose_to_matrix(matrix_to_pose(target_matrix))

        if initial_guess is not None:
            start = self.kinematics._joint_vector(initial_guess, "initial_guess")
        elif self._last_solution is not None:
            start = self._last_solution.copy()
        else:
            start = self.kinematics.joint_center
        start = np.clip(
            start,
            self.kinematics.lower_limits,
            self.kinematics.upper_limits,
        )

        center = self.kinematics.joint_center
        scale = self.kinematics.joint_range
        centering_scale = np.sqrt(self.centering_weight)
        continuity_scale = np.sqrt(self.continuity_weight)
        cached_joints: FloatArray | None = None
        cached_actual: FloatArray | None = None
        cached_geometric_jacobian: FloatArray | None = None
        kinematic_evaluations = 0

        def evaluate(joints: FloatArray) -> tuple[FloatArray, FloatArray]:
            nonlocal cached_joints
            nonlocal cached_actual
            nonlocal cached_geometric_jacobian
            nonlocal kinematic_evaluations
            if cached_joints is None or not np.array_equal(joints, cached_joints):
                cached_actual, cached_geometric_jacobian = (
                    self.kinematics.forward_with_geometric_jacobian(joints)
                )
                cached_joints = joints.copy()
                kinematic_evaluations += 1
            assert cached_actual is not None
            assert cached_geometric_jacobian is not None
            return cached_actual, cached_geometric_jacobian

        def residual(joints: FloatArray) -> FloatArray:
            actual, _ = evaluate(joints)
            position = actual[:3, 3] - target_matrix[:3, 3]
            orientation = rotation_error_vector(target_matrix, actual)
            terms = [position, self.orientation_weight * orientation]
            if centering_scale != 0.0:
                terms.append(centering_scale * (joints - center) / scale)
            if continuity_scale != 0.0:
                terms.append(continuity_scale * (joints - start) / scale)
            return np.concatenate(terms)

        def residual_jacobian(joints: FloatArray) -> FloatArray:
            actual, geometric = evaluate(joints)
            orientation = rotation_error_vector(target_matrix, actual)
            orientation_jacobian = (
                -self.orientation_weight
                * so3_right_jacobian_inverse(orientation)
                @ geometric[3:, :]
            )
            terms = [geometric[:3, :], orientation_jacobian]
            if centering_scale != 0.0:
                terms.append(np.diag(centering_scale / scale))
            if continuity_scale != 0.0:
                terms.append(np.diag(continuity_scale / scale))
            return np.vstack(terms)

        starts = [start]
        # Multistart is an offline/bootstrap aid. Once a caller supplies a
        # tracking seed (or a prior solution exists), one bounded solve keeps
        # the control-cycle cost deterministic and a failure goes to HOLD.
        needs_bootstrap = initial_guess is None and self._last_solution is None
        if self.fallback_starts and needs_bootstrap:
            random = np.random.default_rng(0xD00D)
            margin = np.minimum(1e-6, self.kinematics.joint_range * 1e-6)
            starts.extend(
                random.uniform(
                    self.kinematics.lower_limits + margin,
                    self.kinematics.upper_limits - margin,
                    size=(self.fallback_starts, self.kinematics.dof),
                )
            )

        best = None
        best_score = float("inf")
        total_function_evaluations = 0
        total_jacobian_evaluations = 0
        attempt_count = 0
        accepted = None
        accepted_errors = (float("inf"), float("inf"))
        evaluation_budget = (
            self.bootstrap_max_nfev if needs_bootstrap else self.max_nfev
        )
        for attempt_start in starts:
            attempt_count += 1
            optimized = least_squares(
                residual,
                attempt_start,
                jac=residual_jacobian,
                bounds=(self.kinematics.lower_limits, self.kinematics.upper_limits),
                method="trf",
                x_scale="jac",
                ftol=1e-12,
                xtol=1e-12,
                gtol=1e-12,
                max_nfev=evaluation_budget,
            )
            total_function_evaluations += int(optimized.nfev)
            total_jacobian_evaluations += int(optimized.njev or 0)
            candidate = np.asarray(optimized.x, dtype=float)
            actual, _ = evaluate(candidate)
            position_error = float(
                np.linalg.norm(actual[:3, 3] - target_matrix[:3, 3])
            )
            orientation_error = float(
                np.linalg.norm(rotation_error_vector(target_matrix, actual))
            )
            score = (
                position_error / self.position_tolerance
                + orientation_error / self.orientation_tolerance
            )
            if score < best_score:
                best = (optimized, candidate, position_error, orientation_error)
                best_score = score
            if (
                self.kinematics.within_limits(candidate, tolerance=1e-10)
                and position_error <= self.position_tolerance
                and orientation_error <= self.orientation_tolerance
            ):
                accepted = (optimized, candidate)
                accepted_errors = (position_error, orientation_error)
                break

        assert best is not None
        if accepted is not None:
            optimized, joints = accepted
            position_error, orientation_error = accepted_errors
            success = True
            self._last_solution = joints.copy()
            message = str(optimized.message)
            if not optimized.success:
                message += "; accepted by explicit IK error tolerances"
        else:
            optimized, _, position_error, orientation_error = best
            success = False
            # Consumers can command result.joints directly: a rejected IK result
            # therefore carries the last accepted target (or its safe start).
            joints = start if self._last_solution is None else self._last_solution.copy()
            message = (
                f"{optimized.message}; all {len(starts)} starts rejected; "
                f"position_error={position_error:.6g} m, "
                f"orientation_error={orientation_error:.6g} rad"
            )
        return IKResult(
            success=success,
            joints=joints.copy(),
            position_error=position_error,
            orientation_error=orientation_error,
            function_evaluations=total_function_evaluations,
            jacobian_evaluations=total_jacobian_evaluations,
            kinematic_evaluations=kinematic_evaluations,
            attempts=attempt_count,
            solve_time_s=time.perf_counter() - solve_started,
            status=int(optimized.status),
            optimality=float(optimized.optimality),
            cost=float(optimized.cost),
            message=message,
        )
