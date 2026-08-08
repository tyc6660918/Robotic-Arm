from __future__ import annotations

import unittest

import numpy as np

from windows_sim.sim.hardware_mapping import (
    SAFE_JOINT_LIMITS_DEG,
    clamp_to_safe_limits,
    hardware_degrees_to_ros,
    require_safe_joints,
    ros_to_hardware_degrees,
    within_safe_limits,
)
from windows_sim.sim.ik_solver import BoundedIKSolver
from windows_sim.sim.kinematics import create_dummy_kinematics


class JointLimitAndMappingTests(unittest.TestCase):
    def test_safe_limits_match_declared_intersection(self) -> None:
        np.testing.assert_allclose(
            SAFE_JOINT_LIMITS_DEG,
            np.array(
                [
                    [-170.0, 170.0],
                    [-73.0, 90.0],
                    [-55.0, 90.0],
                    np.rad2deg([-3.14, 3.14]),
                    [-90.0, 90.0],
                    np.rad2deg([-3.14, 3.14]),
                ]
            ),
        )

    def test_ros_hardware_mapping_and_inverse(self) -> None:
        ros = np.deg2rad([10.0, -20.0, -55.0, 40.0, 50.0, -60.0])
        hardware = ros_to_hardware_degrees(ros)
        np.testing.assert_allclose(hardware, [10.0, -20.0, 35.0, 40.0, -50.0, 60.0])
        np.testing.assert_allclose(hardware_degrees_to_ros(hardware), ros, atol=1e-14)

    def test_mapping_round_trip_random_safe_samples(self) -> None:
        rng = np.random.default_rng(1234)
        lower = np.deg2rad(SAFE_JOINT_LIMITS_DEG[:, 0])
        upper = np.deg2rad(SAFE_JOINT_LIMITS_DEG[:, 1])
        for _ in range(100):
            ros = rng.uniform(lower, upper)
            np.testing.assert_allclose(
                hardware_degrees_to_ros(ros_to_hardware_degrees(ros)),
                ros,
                atol=1e-14,
            )

    def test_limit_check_includes_endpoints(self) -> None:
        self.assertTrue(within_safe_limits(np.deg2rad(SAFE_JOINT_LIMITS_DEG[:, 0])))
        self.assertTrue(within_safe_limits(np.deg2rad(SAFE_JOINT_LIMITS_DEG[:, 1])))
        outside = np.zeros(6)
        outside[2] = np.deg2rad(-55.01)
        self.assertFalse(within_safe_limits(outside))
        with self.assertRaisesRegex(ValueError, "Joint3"):
            require_safe_joints(outside)

    def test_clamp_never_exceeds_safe_limits(self) -> None:
        values = np.deg2rad([-999.0, 999.0, -999.0, 999.0, -999.0, 999.0])
        clamped = clamp_to_safe_limits(values)
        self.assertTrue(within_safe_limits(clamped))
        np.testing.assert_allclose(
            np.rad2deg(clamped),
            [-170.0, 90.0, -55.0, 180.0, -90.0, 180.0],
            atol=0.1,
        )

    def test_ik_unreachable_target_fails_inside_bounds(self) -> None:
        kinematics = create_dummy_kinematics()
        solver = BoundedIKSolver(kinematics, max_nfev=80)
        unreachable = np.eye(4)
        unreachable[:3, 3] = [5.0, 5.0, 5.0]
        result = solver.solve(unreachable)
        self.assertFalse(result.success)
        self.assertTrue(kinematics.within_limits(result.joints, tolerance=1e-10))
        self.assertIsNone(solver.last_solution)

    def test_failed_ik_holds_last_accepted_target(self) -> None:
        kinematics = create_dummy_kinematics()
        solver = BoundedIKSolver(kinematics, max_nfev=80, fallback_starts=2)
        accepted_joints = np.deg2rad([5.0, -10.0, 20.0, 5.0, -5.0, 10.0])
        accepted = solver.solve(
            kinematics.forward(accepted_joints), initial_guess=accepted_joints
        )
        self.assertTrue(accepted.success, accepted.message)
        unreachable = np.eye(4)
        unreachable[:3, 3] = [5.0, 5.0, 5.0]
        rejected = solver.solve(unreachable)
        self.assertFalse(rejected.success)
        np.testing.assert_allclose(rejected.joints, accepted.joints)
        np.testing.assert_allclose(solver.last_solution, accepted.joints)

    def test_bad_joint_shapes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ros_to_hardware_degrees(np.zeros(5))
        with self.assertRaises(ValueError):
            within_safe_limits(np.full(6, np.nan))


if __name__ == "__main__":
    unittest.main()
