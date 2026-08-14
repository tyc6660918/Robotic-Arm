from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.spatial.transform import Rotation


WINDOWS_SIM = Path(__file__).resolve().parents[1]
if str(WINDOWS_SIM) not in sys.path:
    sys.path.insert(0, str(WINDOWS_SIM))

from sim.teleop_mapper import TeleopMapper
from sim.types import Pose


class ClutchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapper = TeleopMapper(translation_scale=0.3, rotation_scale=0.5)
        self.origin = Pose.identity()
        self.mapper.update(self.origin, self.origin, clutch=False)

    def test_clutch_holds_feedback_pose_while_master_moves(self) -> None:
        moved_master = Pose([0.05, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])
        active_target = self.mapper.update(moved_master, self.origin, clutch=False)
        np.testing.assert_allclose(active_target.position, [0.015, 0.0, 0.0])

        actual_at_clutch = Pose([0.01, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0])
        held = self.mapper.update(moved_master, actual_at_clutch, clutch=True)
        moved_while_clutched = Pose([0.20, -0.10, 0.05], [0.0, 0.0, 0.0, 1.0])
        held_again = self.mapper.update(
            moved_while_clutched,
            actual_at_clutch,
            clutch=True,
        )
        np.testing.assert_allclose(held.position, actual_at_clutch.position)
        np.testing.assert_allclose(held_again.position, actual_at_clutch.position)

    def test_release_recaptures_without_a_target_jump(self) -> None:
        self.mapper.update(
            Pose([0.05, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0]),
            self.origin,
            clutch=False,
        )
        actual = Pose([0.012, -0.003, 0.004], [0.0, 0.0, 0.0, 1.0])
        self.mapper.update(self.origin, actual, clutch=True)
        relocated_master = Pose([0.3, 0.2, -0.1], [0.0, 0.0, 0.0, 1.0])
        released = self.mapper.update(relocated_master, actual, clutch=False)

        np.testing.assert_allclose(released.position, actual.position, atol=1e-12)
        self.assertLess(np.linalg.norm(released.position - actual.position), 0.0002)

        next_master = Pose(
            relocated_master.position + np.array([0.01, 0.0, 0.0]),
            relocated_master.orientation,
        )
        next_target = self.mapper.update(next_master, actual, clutch=False)
        np.testing.assert_allclose(
            next_target.position,
            actual.position + np.array([0.003, 0.0, 0.0]),
            atol=1e-12,
        )

    def test_release_recaptures_orientation_without_a_jump(self) -> None:
        actual = Pose(
            [0.01, -0.02, 0.03],
            Rotation.from_euler("xyz", [25.0, -10.0, 40.0], degrees=True).as_quat(),
        )
        before_clutch = Pose(
            [0.0, 0.0, 0.0],
            Rotation.from_euler("xyz", [15.0, 20.0, -30.0], degrees=True).as_quat(),
        )
        relocated = Pose(
            [0.2, -0.1, 0.05],
            Rotation.from_euler("xyz", [-80.0, 35.0, 120.0], degrees=True).as_quat(),
        )
        self.mapper.update(before_clutch, actual, clutch=False)
        self.mapper.update(before_clutch, actual, clutch=True)

        released = self.mapper.update(relocated, actual, clutch=False)

        error = (
            Rotation.from_quat(actual.orientation).inv()
            * Rotation.from_quat(released.orientation)
        ).magnitude()
        self.assertLess(error, np.deg2rad(0.2))


if __name__ == "__main__":
    unittest.main()
