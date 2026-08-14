from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

from windows_sim.sim.scenario import ScenarioPlayer


SCENARIO_DIRECTORY = Path(__file__).resolve().parents[1] / "scenarios"


class ScenarioPlayerTests(unittest.TestCase):
    def test_repository_scenarios_parse_with_declared_kind_and_duration(self) -> None:
        expected = {
            "axis_steps.json": ("axis_steps", "keyframes", 24.0),
            "circle.json": ("circle", "parametric", 20.0),
            "figure_eight.json": ("figure_eight", "parametric", 20.0),
            "soak_60min.json": ("soak_60min", "parametric", 3600.0),
            "tremor.json": ("tremor", "parametric", 30.0),
            "fault_injection.json": ("fault_injection", "faults", 30.0),
        }

        for filename, (name, kind, duration_s) in expected.items():
            with self.subTest(filename=filename):
                path = SCENARIO_DIRECTORY / filename
                player = ScenarioPlayer.from_file(path)
                self.assertEqual(player.source, path.resolve())
                self.assertEqual(player.name, name)
                self.assertEqual(player.kind, kind)
                self.assertEqual(player.duration_s, duration_s)

    def test_keyframes_interpolate_pose_grasp_and_discrete_controls(self) -> None:
        player = ScenarioPlayer(
            {
                "name": "interpolation",
                "type": "keyframes",
                "duration_s": 2.0,
                "keyframes": [
                    {
                        "time_s": 0.0,
                        "position_m": [0.0, 0.0, 0.0],
                        "rpy_deg": [0.0, 0.0, 0.0],
                        "grasp": 0.0,
                        "deadman": False,
                        "clutch": True,
                    },
                    {
                        "time_s": 2.0,
                        "position_m": [0.2, -0.1, 0.4],
                        "rpy_deg": [0.0, 0.0, 90.0],
                        "grasp": 1.0,
                        "deadman": True,
                        "clutch": False,
                    },
                ],
            }
        )

        before_start = player.sample(-10.0)
        midpoint = player.sample(1.0)
        after_end = player.sample(10.0)

        np.testing.assert_allclose(before_start.pose.position, [0.0, 0.0, 0.0])
        np.testing.assert_allclose(midpoint.pose.position, [0.1, -0.05, 0.2])
        np.testing.assert_allclose(after_end.pose.position, [0.2, -0.1, 0.4])
        expected_midpoint_rotation = Rotation.from_euler("z", 45.0, degrees=True)
        actual_midpoint_rotation = Rotation.from_quat(midpoint.pose.orientation_xyzw)
        np.testing.assert_allclose(
            actual_midpoint_rotation.as_matrix(),
            expected_midpoint_rotation.as_matrix(),
            atol=1e-12,
        )
        self.assertAlmostEqual(midpoint.grasp, 0.5)
        self.assertFalse(midpoint.deadman)
        self.assertTrue(midpoint.clutch)
        self.assertTrue(after_end.deadman)
        self.assertFalse(after_end.clutch)

    def test_parametric_circle_respects_warmup_plane_orientation_and_grasp(self) -> None:
        player = ScenarioPlayer(
            {
                "type": "parametric",
                "shape": "circle",
                "duration_s": 6.0,
                "warmup_s": 0.5,
                "center_m": [1.0, 2.0, 3.0],
                "radius_m": 0.2,
                "frequency_hz": 0.25,
                "plane": "xz",
                "rpy_amplitude_deg": [10.0, 0.0, 20.0],
                "grasp": 1.5,
                "deadman": True,
            }
        )

        warmup = player.sample(0.25)
        quarter_cycle = player.sample(1.5)

        np.testing.assert_allclose(warmup.pose.position, [1.0, 2.0, 3.0])
        self.assertFalse(warmup.deadman)
        np.testing.assert_allclose(
            quarter_cycle.pose.position,
            [0.8, 2.0, 3.2],
            atol=1e-12,
        )
        expected_rotation = Rotation.from_euler(
            "xyz", [10.0, 0.0, 20.0], degrees=True
        )
        np.testing.assert_allclose(
            Rotation.from_quat(quarter_cycle.pose.orientation_xyzw).as_matrix(),
            expected_rotation.as_matrix(),
            atol=1e-12,
        )
        self.assertEqual(quarter_cycle.grasp, 1.0)
        self.assertTrue(quarter_cycle.deadman)
        self.assertFalse(quarter_cycle.clutch)

    def test_parametric_tremor_combines_intentional_and_high_frequency_motion(self) -> None:
        player = ScenarioPlayer(
            {
                "type": "parametric",
                "shape": "tremor",
                "duration_s": 2.0,
                "center_m": [0.1, 0.2, 0.3],
                "axis": "y",
                "intentional_frequency_hz": 0.5,
                "intentional_amplitude_m": 0.03,
                "tremor_frequency_hz": 10.0,
                "tremor_amplitude_m": 0.001,
            }
        )

        sample = player.sample(0.5)

        np.testing.assert_allclose(sample.pose.position, [0.1, 0.23, 0.3], atol=1e-12)
        np.testing.assert_allclose(
            Rotation.from_quat(sample.pose.orientation_xyzw).as_matrix(),
            np.eye(3),
            atol=1e-12,
        )
        self.assertTrue(sample.deadman)

    def test_fault_windows_merge_overlapping_events_and_end_exclusively(self) -> None:
        player = ScenarioPlayer(
            {
                "type": "faults",
                "duration_s": 5.0,
                "base_motion": {
                    "shape": "circle",
                    "radius_m": 0.01,
                    "frequency_hz": 0.1,
                    "plane": "xy",
                },
                "events": [
                    {"time_s": 1.0, "duration_s": 2.0, "fault": "input_dropout"},
                    {
                        "time_s": 1.0,
                        "duration_s": 2.0,
                        "fault": "timestamp_out_of_order",
                    },
                    {
                        "time_s": 1.0,
                        "duration_s": 2.0,
                        "fault": "command_delay",
                        "value_s": 0.04,
                    },
                    {
                        "time_s": 1.0,
                        "duration_s": 2.0,
                        "fault": "command_delay",
                        "value_s": 0.08,
                    },
                    {
                        "time_s": 1.0,
                        "duration_s": 2.0,
                        "fault": "packet_dropout",
                        "probability": 0.1,
                    },
                    {
                        "time_s": 1.0,
                        "duration_s": 2.0,
                        "fault": "packet_dropout",
                        "probability": 0.25,
                    },
                    {
                        "time_s": 1.0,
                        "duration_s": 2.0,
                        "fault": "joint_stuck",
                        "joint_index": 4,
                    },
                    {
                        "time_s": 1.0,
                        "duration_s": 2.0,
                        "fault": "joint_stuck",
                        "joint_index": 2,
                    },
                    {
                        "time_s": 1.0,
                        "duration_s": 2.0,
                        "fault": "unreachable_target",
                        "offset_m": [0.0, 0.0, 2.0],
                    },
                    {"time_s": 1.0, "duration_s": 2.0, "fault": "fatal_fault"},
                    {"time_s": 1.0, "duration_s": 2.0, "fault": "clear_fault"},
                ],
            }
        )

        during_warmup = player.sample(0.5)
        active = player.sample(1.5)
        at_exclusive_end = player.sample(3.0)

        self.assertFalse(during_warmup.deadman)
        self.assertTrue(active.deadman)
        self.assertTrue(active.faults.input_dropout)
        self.assertTrue(active.faults.timestamp_out_of_order)
        self.assertEqual(active.faults.command_delay_s, 0.08)
        self.assertEqual(active.faults.command_drop_probability, 0.25)
        self.assertEqual(active.faults.stuck_joints, (2, 4))
        self.assertTrue(active.faults.unreachable_target)
        self.assertTrue(active.faults.fatal_fault)
        self.assertTrue(active.faults.clear_fault)
        self.assertFalse(at_exclusive_end.faults.input_dropout)
        self.assertFalse(at_exclusive_end.faults.timestamp_out_of_order)
        self.assertEqual(at_exclusive_end.faults.command_delay_s, 0.0)
        self.assertEqual(at_exclusive_end.faults.command_drop_probability, 0.0)
        self.assertEqual(at_exclusive_end.faults.stuck_joints, ())
        self.assertFalse(at_exclusive_end.faults.unreachable_target)
        self.assertFalse(at_exclusive_end.faults.fatal_fault)
        self.assertFalse(at_exclusive_end.faults.clear_fault)

    def test_invalid_scenario_configurations_are_rejected(self) -> None:
        for duration in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(duration=duration):
                with self.assertRaisesRegex(ValueError, "duration_s"):
                    ScenarioPlayer({"duration_s": duration})

        invalid_at_sample = (
            ({"duration_s": 1.0, "type": "unknown"}, "unsupported scenario type"),
            (
                {"duration_s": 1.0, "type": "keyframes", "keyframes": []},
                "non-empty keyframes",
            ),
            (
                {
                    "duration_s": 1.0,
                    "type": "parametric",
                    "shape": "circle",
                    "plane": "invalid",
                },
                "unsupported circle plane",
            ),
            (
                {
                    "duration_s": 1.0,
                    "type": "parametric",
                    "shape": "tremor",
                    "axis": "invalid",
                },
                "unsupported tremor axis",
            ),
            (
                {
                    "duration_s": 1.0,
                    "type": "parametric",
                    "shape": "invalid",
                },
                "unsupported parametric shape",
            ),
        )
        for specification, message in invalid_at_sample:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    ScenarioPlayer(specification).sample(0.0)

        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "invalid_root.json"
            path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "root must be a JSON object"):
                ScenarioPlayer.from_file(path)


if __name__ == "__main__":
    unittest.main()
