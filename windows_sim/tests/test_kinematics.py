from __future__ import annotations

import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from windows_sim.sim.ik_solver import BoundedIKSolver
from windows_sim.sim.kinematics import (
    create_dummy_kinematics,
    matrix_to_pose,
    pose_to_matrix,
)
from windows_sim.sim.urdf_model import load_dummy_urdf, load_openrst_urdf


class URDFAndForwardKinematicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = load_dummy_urdf()
        cls.kinematics = create_dummy_kinematics()

    def test_static_urdf_chain(self) -> None:
        self.assertEqual(self.model.name, "dummy-ros2")
        self.assertEqual(self.model.root_links, ("world",))
        chain = self.model.chain("base_link", "link6_1_1")
        self.assertEqual(tuple(joint.name for joint in chain), self.kinematics.joint_names)
        self.assertEqual(self.kinematics.dof, 6)

    def test_openrst_static_urdf_is_structurally_valid(self) -> None:
        model = load_openrst_urdf()
        self.assertEqual(model.name, "openrst_description")
        self.assertEqual(model.root_links, ("forceps_base_link",))
        self.assertEqual(len(model.links), 6)
        self.assertEqual(len(model.joints), 5)
        self.assertEqual(
            tuple(
                joint.name
                for joint in model.chain("forceps_base_link", "ee_link")
            ),
            ("joint_interface", "joint_pitch", "joint_finger_left", "joint_ee"),
        )

    def test_zero_configuration_matches_urdf_origins(self) -> None:
        result = self.kinematics.forward(np.zeros(6))
        np.testing.assert_allclose(
            result[:3, 3],
            np.array([-0.016, -0.290517, 0.318]),
            atol=1e-12,
        )
        np.testing.assert_allclose(result[:3, :3], np.eye(3), atol=1e-12)

    def test_forward_all_returns_full_rigid_transforms(self) -> None:
        joints = np.deg2rad([30.0, -20.0, 40.0, 25.0, -35.0, 60.0])
        transforms = self.kinematics.forward_all(joints)
        self.assertEqual(
            tuple(transforms),
            (
                "base_link",
                "link1_1_1",
                "link2_1_1",
                "link3_1_1",
                "link4_1_1",
                "link5_1_1",
                "link6_1_1",
            ),
        )
        for transform in transforms.values():
            self.assertEqual(transform.shape, (4, 4))
            np.testing.assert_allclose(transform[3], [0.0, 0.0, 0.0, 1.0])
            np.testing.assert_allclose(
                transform[:3, :3].T @ transform[:3, :3],
                np.eye(3),
                atol=1e-12,
            )
            self.assertAlmostEqual(np.linalg.det(transform[:3, :3]), 1.0, places=12)

    def test_pose_matrix_round_trip(self) -> None:
        transform = np.eye(4)
        transform[:3, :3] = Rotation.from_euler("xyz", [0.3, -0.2, 1.1]).as_matrix()
        transform[:3, 3] = [0.1, -0.25, 0.33]
        np.testing.assert_allclose(pose_to_matrix(matrix_to_pose(transform)), transform, atol=1e-12)
        np.testing.assert_allclose(matrix_to_pose(transform).as_matrix(), transform, atol=1e-12)

    def test_pose_rejects_non_rigid_matrix(self) -> None:
        invalid = np.eye(4)
        invalid[0, 0] = 2.0
        with self.assertRaisesRegex(ValueError, "orthonormal"):
            matrix_to_pose(invalid)

    def test_fk_ik_fk_round_trip(self) -> None:
        rng = np.random.default_rng(90210)
        solver = BoundedIKSolver(self.kinematics)
        margins = np.deg2rad([5.0, 5.0, 5.0, 5.0, 5.0, 5.0])
        lower = self.kinematics.lower_limits + margins
        upper = self.kinematics.upper_limits - margins
        for _ in range(30):
            expected_joints = rng.uniform(lower, upper)
            target = self.kinematics.forward(expected_joints)
            guess = np.clip(
                expected_joints + rng.normal(0.0, np.deg2rad(3.0), 6),
                lower,
                upper,
            )
            result = solver.solve(target, initial_guess=guess)
            self.assertTrue(result.success, result.message)
            actual = self.kinematics.forward(result.joints)
            self.assertLess(np.linalg.norm(actual[:3, 3] - target[:3, 3]), 1e-4)
            rotation_delta = Rotation.from_matrix(
                target[:3, :3] @ actual[:3, :3].T
            ).magnitude()
            self.assertLess(rotation_delta, np.deg2rad(0.05))

    def test_ik_uses_last_success_as_warm_start(self) -> None:
        solver = BoundedIKSolver(self.kinematics)
        target_joints = np.deg2rad([20.0, -20.0, 25.0, 10.0, 15.0, -30.0])
        first = solver.solve(self.kinematics.forward(target_joints), target_joints)
        self.assertTrue(first.success, first.message)
        nearby = target_joints + np.deg2rad([0.5, -0.3, 0.2, 0.4, -0.2, 0.3])
        second = solver.solve(self.kinematics.forward(nearby))
        self.assertTrue(second.success, second.message)
        np.testing.assert_allclose(solver.last_solution, second.joints)

    def test_ik_rejects_invalid_target_rotation(self) -> None:
        target = np.eye(4)
        target[:3, :3] *= 2.0
        with self.assertRaisesRegex(ValueError, "orthonormal"):
            BoundedIKSolver(self.kinematics).solve(target)


if __name__ == "__main__":
    unittest.main()
