from __future__ import annotations

import time
import unittest

import numpy as np

from windows_sim.sim.ik_solver import BoundedIKSolver
from windows_sim.sim.kinematics import (
    create_dummy_kinematics,
    rotation_error_vector,
    so3_right_jacobian_inverse,
)


class AnalyticIKTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.kinematics = create_dummy_kinematics()

    def test_geometric_jacobian_matches_central_difference(self) -> None:
        rng = np.random.default_rng(20260808)
        joint_range = self.kinematics.joint_range
        lower = self.kinematics.lower_limits + 0.05 * joint_range
        upper = self.kinematics.upper_limits - 0.05 * joint_range
        for _ in range(50):
            joints = rng.uniform(lower, upper)
            transform, analytic = (
                self.kinematics.forward_with_geometric_jacobian(joints)
            )
            numerical = self.kinematics.numerical_jacobian(joints, step=1e-7)
            np.testing.assert_allclose(
                transform,
                self.kinematics.forward(joints),
                atol=1e-12,
            )
            np.testing.assert_allclose(analytic, numerical, rtol=2e-6, atol=2e-7)

    def test_orientation_residual_jacobian_matches_finite_difference(self) -> None:
        rng = np.random.default_rng(90210)
        joint_range = self.kinematics.joint_range
        lower = self.kinematics.lower_limits + 0.05 * joint_range
        upper = self.kinematics.upper_limits - 0.05 * joint_range
        step = 1e-7
        for _ in range(30):
            joints = rng.uniform(lower, upper)
            target_joints = np.clip(
                joints + rng.normal(0.0, 0.01, self.kinematics.dof),
                lower,
                upper,
            )
            target = self.kinematics.forward(target_joints)
            actual, geometric = (
                self.kinematics.forward_with_geometric_jacobian(joints)
            )
            error = rotation_error_vector(target, actual)
            analytic = -so3_right_jacobian_inverse(error) @ geometric[3:, :]
            numerical = np.empty_like(analytic)
            for index in range(self.kinematics.dof):
                plus = joints.copy()
                minus = joints.copy()
                plus[index] += step
                minus[index] -= step
                numerical[:, index] = (
                    rotation_error_vector(target, self.kinematics.forward(plus))
                    - rotation_error_vector(target, self.kinematics.forward(minus))
                ) / (2.0 * step)
            np.testing.assert_allclose(analytic, numerical, rtol=2e-6, atol=2e-7)

    def test_tracking_statistics_and_failed_solution_hold(self) -> None:
        solver = BoundedIKSolver(self.kinematics)
        self.assertEqual(solver.max_nfev, 15)
        self.assertEqual(solver.bootstrap_max_nfev, 300)
        accepted_joints = np.array([0.15, -0.35, 0.28, 0.2, 0.35, -0.15])
        accepted = solver.solve(
            self.kinematics.forward(accepted_joints),
            initial_guess=accepted_joints,
        )
        self.assertTrue(accepted.success, accepted.message)
        self.assertEqual(accepted.attempts, 1)
        self.assertGreater(accepted.function_evaluations, 0)
        self.assertGreater(accepted.jacobian_evaluations, 0)
        self.assertLessEqual(accepted.function_evaluations, solver.max_nfev)
        self.assertLessEqual(
            accepted.kinematic_evaluations,
            accepted.function_evaluations + accepted.jacobian_evaluations,
        )
        self.assertEqual(accepted.iterations, accepted.function_evaluations)
        self.assertGreater(accepted.solve_time_s, 0.0)

        unreachable = self.kinematics.forward(accepted_joints)
        unreachable[:3, 3] += [0.5, 0.5, 0.5]
        rejected = solver.solve(unreachable)
        self.assertFalse(rejected.success)
        self.assertEqual(rejected.attempts, 1)
        self.assertLessEqual(rejected.function_evaluations, solver.max_nfev)
        np.testing.assert_allclose(rejected.joints, accepted.joints)
        np.testing.assert_allclose(solver.last_solution, accepted.joints)

    def test_bootstrap_multistart_uses_separate_budget(self) -> None:
        solver = BoundedIKSolver(
            self.kinematics,
            max_nfev=15,
            bootstrap_max_nfev=5,
            fallback_starts=2,
        )
        unreachable = np.eye(4, dtype=float)
        unreachable[:3, 3] = [5.0, 5.0, 5.0]
        result = solver.solve(unreachable)
        self.assertFalse(result.success)
        self.assertEqual(result.attempts, 3)
        self.assertLessEqual(result.function_evaluations, 15)
        np.testing.assert_allclose(result.joints, self.kinematics.joint_center)

    def test_1000_rate_limited_tracking_steps_meet_timing_target(self) -> None:
        rate_hz = 100.0
        sample_count = 1000
        times = np.arange(sample_count, dtype=float) / rate_hz
        center = np.array([0.15, -0.35, 0.28, 0.2, 0.35, -0.15])
        amplitudes = np.array([0.12, 0.10, 0.08, 0.15, 0.10, 0.14])
        frequencies = np.array([0.17, 0.13, 0.19, 0.23, 0.11, 0.29])
        phases = np.array([0.0, 0.7, 1.1, 0.4, 1.8, 2.0])
        expected_joints = center + amplitudes * np.sin(
            2.0 * np.pi * times[:, None] * frequencies + phases
        )
        self.assertTrue(
            np.all(expected_joints >= self.kinematics.lower_limits)
            and np.all(expected_joints <= self.kinematics.upper_limits)
        )
        targets = [self.kinematics.forward(joints) for joints in expected_joints]
        position_steps = [
            np.linalg.norm(targets[index][:3, 3] - targets[index - 1][:3, 3])
            for index in range(1, sample_count)
        ]
        orientation_steps = [
            np.linalg.norm(rotation_error_vector(targets[index], targets[index - 1]))
            for index in range(1, sample_count)
        ]
        self.assertLess(max(position_steps), 0.0005)
        self.assertLess(max(orientation_steps), 0.005)

        solver = BoundedIKSolver(self.kinematics, fallback_starts=0)
        seed = expected_joints[0].copy()
        solver.reset(seed)
        elapsed_ms: list[float] = []
        successes = 0
        maximum_position_error = 0.0
        maximum_orientation_error = 0.0
        for target in targets:
            started = time.perf_counter_ns()
            result = solver.solve(target, initial_guess=seed)
            elapsed_ms.append((time.perf_counter_ns() - started) * 1e-6)
            successes += int(result.success)
            maximum_position_error = max(
                maximum_position_error, result.position_error
            )
            maximum_orientation_error = max(
                maximum_orientation_error, result.orientation_error
            )
            seed = result.joints

        p99_ms = float(np.percentile(elapsed_ms, 99.0))
        self.assertEqual(successes, sample_count)
        self.assertLess(maximum_position_error, 1e-4)
        self.assertLess(maximum_orientation_error, np.deg2rad(0.05))
        self.assertLess(
            p99_ms,
            20.0,
            f"tracking IK P99 was {p99_ms:.3f} ms",
        )

    def test_warm_started_ik_crosses_wrist_singularity_without_branch_jump(self) -> None:
        wrist_angles_deg = np.linspace(10.0, -10.0, 41)
        expected_path = [
            np.deg2rad([0.0, -30.0, 45.0, 0.0, wrist_angle, 0.0])
            for wrist_angle in wrist_angles_deg
        ]
        solver = BoundedIKSolver(self.kinematics, fallback_starts=0)
        seed = expected_path[0].copy()
        solver.reset(seed)
        minimum_singular_value = float("inf")
        solutions: list[np.ndarray] = []

        for expected in expected_path:
            target, jacobian = self.kinematics.forward_with_geometric_jacobian(expected)
            minimum_singular_value = min(
                minimum_singular_value,
                float(np.linalg.svd(jacobian, compute_uv=False)[-1]),
            )
            result = solver.solve(target, initial_guess=seed)
            self.assertTrue(result.success, result.message)
            self.assertTrue(self.kinematics.within_limits(result.joints))
            self.assertLess(result.position_error, 1e-4)
            self.assertLess(result.orientation_error, np.deg2rad(0.05))
            seed = result.joints
            solutions.append(seed.copy())

        solution_deg = np.rad2deg(np.asarray(solutions))
        maximum_step_deg = float(np.max(np.abs(np.diff(solution_deg, axis=0))))
        self.assertLess(minimum_singular_value, 1e-12)
        self.assertLess(maximum_step_deg, 0.55)
        self.assertLess(
            float(np.max(np.abs(solution_deg[:, 4] - wrist_angles_deg))),
            0.05,
        )
        self.assertLess(float(np.max(np.abs(solution_deg[:, [3, 5]]))), 0.1)


if __name__ == "__main__":
    unittest.main()
