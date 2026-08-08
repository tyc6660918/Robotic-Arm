from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.spatial.transform import Rotation


WINDOWS_SIM = Path(__file__).resolve().parents[1]
if str(WINDOWS_SIM) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SIM))

from sim.motion_filter import OneEuroPoseFilter, PoseRateLimiter
from sim.teleop_mapper import TeleopMapper
from sim.types import Pose


def pose(
    position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_vector: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> Pose:
    return Pose(
        np.asarray(position, dtype=float),
        Rotation.from_rotvec(rotation_vector).as_quat(),
    )


class TeleopMappingTests(unittest.TestCase):
    def test_translation_scale_on_all_axes(self) -> None:
        mapper = TeleopMapper(translation_scale=0.3, rotation_scale=0.5)
        mapper.capture(Pose.identity(), Pose.identity())

        for axis in range(3):
            with self.subTest(axis=axis):
                displacement = np.zeros(3)
                displacement[axis] = 0.05
                target = mapper.map_pose(Pose(displacement, [0.0, 0.0, 0.0, 1.0]))
                expected = np.zeros(3)
                expected[axis] = 0.015
                np.testing.assert_allclose(target.position, expected, atol=1e-12)

    def test_rotation_scale_on_all_axes(self) -> None:
        mapper = TeleopMapper(translation_scale=0.3, rotation_scale=0.5)
        mapper.capture(Pose.identity(), Pose.identity())
        master_angle = np.deg2rad(20.0)

        for axis in range(3):
            with self.subTest(axis=axis):
                rotation_vector = np.zeros(3)
                rotation_vector[axis] = master_angle
                target = mapper.map_pose(
                    Pose(np.zeros(3), Rotation.from_rotvec(rotation_vector).as_quat())
                )
                result = Rotation.from_quat(target.orientation).as_rotvec()
                expected = np.zeros(3)
                expected[axis] = np.deg2rad(10.0)
                np.testing.assert_allclose(result, expected, atol=1e-12)

    def test_mapping_is_relative_to_captured_frames(self) -> None:
        quarter_turn = Rotation.from_euler("z", 90.0, degrees=True)
        master_reference = Pose([1.0, 2.0, 3.0], quarter_turn.as_quat())
        slave_reference = Pose([-0.2, 0.4, 0.1], quarter_turn.as_quat())
        mapper = TeleopMapper(translation_scale=0.3)
        mapper.capture(master_reference, slave_reference)

        master_local_x = master_reference.position + quarter_turn.apply([0.05, 0.0, 0.0])
        target = mapper.map_pose(Pose(master_local_x, quarter_turn.as_quat()))
        expected = slave_reference.position + quarter_turn.apply([0.015, 0.0, 0.0])
        np.testing.assert_allclose(target.position, expected, atol=1e-12)

    def test_axis_map_must_be_a_proper_rotation(self) -> None:
        reflection = np.diag([-1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            TeleopMapper(axis_map=reflection)


class MotionFilterTests(unittest.TestCase):
    def test_pose_filter_handles_equivalent_quaternion_signs(self) -> None:
        filter_ = OneEuroPoseFilter()
        first = Pose([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])
        equivalent = Pose([0.0, 0.0, 0.0], [0.0, 0.0, 0.0, -1.0])
        filter_.filter(first, 0.0)
        result = filter_.filter(equivalent, 0.01)
        error = (
            Rotation.from_quat(result.orientation).inv()
            * Rotation.from_quat(first.orientation)
        ).magnitude()
        self.assertLess(error, 1e-12)

    def test_rate_limiter_respects_first_acceleration_step(self) -> None:
        limiter = PoseRateLimiter(
            max_linear_speed=0.05,
            max_angular_speed=0.5,
            max_linear_acceleration=0.2,
            max_angular_acceleration=2.0,
        )
        limiter.reset(Pose.identity())
        target = pose((1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        result = limiter.update(target, 0.01)
        self.assertLessEqual(result.position[0], 0.2 * 0.01**2 + 1e-12)
        angle = Rotation.from_quat(result.orientation).magnitude()
        self.assertLessEqual(angle, 2.0 * 0.01**2 + 1e-12)

    def test_rate_limiter_brakes_without_overshoot(self) -> None:
        dt = 0.01
        limiter = PoseRateLimiter(
            max_linear_speed=0.05,
            max_angular_speed=0.5,
            max_linear_acceleration=0.2,
            max_angular_acceleration=2.0,
        )
        limiter.reset(Pose.identity())
        target = Pose(
            np.array([0.001, 0.0, 0.0]),
            Rotation.from_euler("z", 0.01).as_quat(),
        )
        positions = [0.0]
        angles = [0.0]
        for _ in range(100):
            result = limiter.update(target, dt)
            positions.append(float(result.position[0]))
            angles.append(float(Rotation.from_quat(result.orientation).magnitude()))

        linear_velocity = np.diff(positions) / dt
        linear_acceleration = np.diff(linear_velocity) / dt
        angular_velocity = np.diff(angles) / dt
        angular_acceleration = np.diff(angular_velocity) / dt
        self.assertLessEqual(max(positions), 0.001 + 1e-12)
        self.assertLessEqual(max(angles), 0.01 + 1e-12)
        self.assertAlmostEqual(positions[-1], 0.001, places=12)
        self.assertAlmostEqual(angles[-1], 0.01, places=12)
        self.assertLessEqual(np.max(np.abs(linear_velocity)), 0.05 + 1e-12)
        self.assertLessEqual(np.max(np.abs(linear_acceleration)), 0.2 + 1e-10)
        self.assertLessEqual(np.max(np.abs(angular_velocity)), 0.5 + 1e-12)
        self.assertLessEqual(np.max(np.abs(angular_acceleration)), 2.0 + 1e-10)


if __name__ == "__main__":
    unittest.main()
