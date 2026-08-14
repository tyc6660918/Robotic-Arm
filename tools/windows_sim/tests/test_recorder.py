from __future__ import annotations

import csv
from datetime import datetime as RealDateTime
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

from windows_sim.sim.recorder import SimulationRecorder
from windows_sim.sim.types import Pose


POSE_FIELDS = {
    f"{pose}.{component}[{index}]"
    for pose in ("master_raw", "master_filtered", "target_flange", "actual_flange")
    for component, count in (("position", 3), ("orientation_xyzw", 4))
    for index in range(count)
}
JOINT_FIELDS = {
    f"{field}[{index}]"
    for field in (
        "target_joints_rad",
        "actual_joints_rad",
        "actual_joint_velocity_rad_s",
    )
    for index in range(6)
}
SCALAR_FIELDS = {
    "time_s",
    "wall_time_s",
    "cycle_period_s",
    "state",
    "fault_bits",
    "fault_reason",
    "message_age_s",
    "grasp",
    "deadman",
    "clutch",
    "ik_success",
    "position_error_m",
    "orientation_error_rad",
}
RUNTIME_CSV_FIELDS = POSE_FIELDS | JOINT_FIELDS | SCALAR_FIELDS


def runtime_sample(
    *,
    time_s: float,
    cycle_period_s: float,
    state: str,
    ik_success: bool,
    position_error_m: float,
    orientation_error_rad: float,
) -> dict[str, object]:
    identity = Pose.identity()
    offset = Pose(
        np.array([0.1, -0.2, 0.3]),
        np.array([0.0, 0.0, math.sin(math.pi / 8.0), math.cos(math.pi / 8.0)]),
    )
    return {
        "time_s": time_s,
        "wall_time_s": 1_700_000_000.0 + time_s,
        "cycle_period_s": cycle_period_s,
        "state": state,
        "fault_bits": np.int64(0),
        "fault_reason": None,
        "message_age_s": 0.002,
        "master_raw": offset,
        "master_filtered": identity,
        "target_flange": offset,
        "actual_flange": identity,
        "target_joints_rad": np.arange(6, dtype=float) * 0.1,
        "actual_joints_rad": np.arange(6, dtype=float) * -0.1,
        "actual_joint_velocity_rad_s": np.linspace(0.0, 0.5, 6),
        "grasp": 0.5,
        "deadman": True,
        "clutch": False,
        "ik_success": ik_success,
        "position_error_m": position_error_m,
        "orientation_error_rad": orientation_error_rad,
    }


class SimulationRecorderTests(unittest.TestCase):
    def test_automatic_run_names_remain_unique_on_timestamp_collision(self) -> None:
        class FrozenDateTime:
            @classmethod
            def now(cls) -> RealDateTime:
                return RealDateTime(2026, 8, 8, 4, 30, 0, 123456)

        with TemporaryDirectory() as temporary_directory:
            with patch("windows_sim.sim.recorder.datetime", FrozenDateTime):
                first = SimulationRecorder(Path(temporary_directory))
                second = SimulationRecorder(Path(temporary_directory))
            try:
                self.assertNotEqual(first.run_directory, second.run_directory)
                self.assertEqual(
                    second.run_directory.name, f"{first.run_directory.name}_1"
                )
            finally:
                first.close()
                second.close()

    def test_existing_explicit_run_name_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = SimulationRecorder(root, run_name="fixed")
            try:
                with self.assertRaises(FileExistsError):
                    SimulationRecorder(root, run_name="fixed")
            finally:
                first.close()

    def test_new_fields_after_header_are_rejected(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            recorder = SimulationRecorder(
                Path(temporary_directory),
                run_name="late_field",
            )
            try:
                sample = runtime_sample(
                    time_s=0.01,
                    cycle_period_s=0.01,
                    state="TELEOP",
                    ik_success=True,
                    position_error_m=0.0,
                    orientation_error_rad=0.0,
                )
                recorder.record(sample)
                sample["late_field"] = 1

                with self.assertRaisesRegex(ValueError, "late_field"):
                    recorder.record(sample)
            finally:
                recorder.close()

    def test_cycle_percentile_reservoir_has_a_fixed_bound(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            recorder = SimulationRecorder(
                Path(temporary_directory),
                run_name="bounded_reservoir",
                percentile_reservoir_size=5,
            )
            self.addCleanup(recorder.close)
            for index in range(100):
                recorder.record(
                    runtime_sample(
                        time_s=0.01 * index,
                        cycle_period_s=0.001 * index,
                        state="TELEOP",
                        ik_success=True,
                        position_error_m=0.0,
                        orientation_error_rad=0.0,
                    )
                )

            report = json.loads(
                recorder.finalize().read_text(encoding="utf-8")
            )
            metrics = report["metrics"]
            self.assertEqual(metrics["cycle_period_samples_seen"], 100)
            self.assertEqual(metrics["cycle_period_reservoir_size"], 5)

    def test_csv_contains_every_runtime_field_and_flattened_pose_value(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            recorder = SimulationRecorder(
                Path(temporary_directory),
                run_name="csv_fields",
            )
            self.addCleanup(recorder.close)
            recorder.record(
                runtime_sample(
                    time_s=0.01,
                    cycle_period_s=0.01,
                    state="TELEOP",
                    ik_success=True,
                    position_error_m=0.001,
                    orientation_error_rad=0.002,
                )
            )
            recorder.finalize()

            with recorder.csv_path.open(newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                rows = list(reader)

            self.assertEqual(set(reader.fieldnames or ()), RUNTIME_CSV_FIELDS)
            self.assertEqual(len(reader.fieldnames or ()), 59)
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertAlmostEqual(float(row["master_raw.position[0]"]), 0.1)
            self.assertAlmostEqual(float(row["master_raw.position[1]"]), -0.2)
            self.assertAlmostEqual(
                float(row["master_raw.orientation_xyzw[2]"]),
                math.sin(math.pi / 8.0),
            )
            self.assertAlmostEqual(float(row["target_joints_rad[5]"]), 0.5)
            self.assertAlmostEqual(
                float(row["actual_joint_velocity_rad_s[5]"]), 0.5
            )
            self.assertEqual(row["deadman"], "True")
            self.assertEqual(row["clutch"], "False")

    def test_finalize_writes_metadata_and_aggregate_metrics(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            recorder = SimulationRecorder(
                Path(temporary_directory),
                csv_name="samples.csv",
                report_name="metrics.json",
                run_name="metrics",
                metadata={"scenario": "unit_test", "filter_enabled": True},
            )
            self.addCleanup(recorder.close)
            recorder.record(
                runtime_sample(
                    time_s=0.01,
                    cycle_period_s=0.01,
                    state="READY",
                    ik_success=True,
                    position_error_m=0.003,
                    orientation_error_rad=0.04,
                )
            )
            recorder.record(
                runtime_sample(
                    time_s=0.02,
                    cycle_period_s=0.02,
                    state="TELEOP",
                    ik_success=False,
                    position_error_m=0.004,
                    orientation_error_rad=0.03,
                )
            )

            report_path = recorder.finalize(
                {"scenario_completed": True, "simulated_duration_s": 2.0}
            )
            report = json.loads(report_path.read_text(encoding="utf-8"))
            metrics = report["metrics"]

            self.assertEqual(report_path, recorder.report_path)
            self.assertEqual(report["metadata"], {"scenario": "unit_test", "filter_enabled": True})
            self.assertEqual(report["csv"], "samples.csv")
            self.assertIn("created_at", report)
            self.assertEqual(metrics["samples_written"], 2)
            self.assertAlmostEqual(
                metrics["position_error_rms_m"],
                math.sqrt((0.003**2 + 0.004**2) / 2.0),
            )
            self.assertAlmostEqual(
                metrics["orientation_error_rms_rad"],
                math.sqrt((0.04**2 + 0.03**2) / 2.0),
            )
            self.assertEqual(metrics["position_error_max_m"], 0.004)
            self.assertEqual(metrics["orientation_error_max_rad"], 0.04)
            self.assertEqual(metrics["ik_success_rate"], 0.5)
            self.assertAlmostEqual(metrics["cycle_period_p50_s"], 0.015)
            self.assertAlmostEqual(metrics["cycle_period_p99_s"], 0.0199)
            self.assertEqual(metrics["state_sample_counts"], {"READY": 1, "TELEOP": 1})
            self.assertTrue(metrics["scenario_completed"])
            self.assertEqual(metrics["simulated_duration_s"], 2.0)
            self.assertIsNone(
                metrics["acceptance"]["control_cycle_p99_under_20ms"]
            )
            self.assertFalse(
                metrics["acceptance"]["control_cycle_timing_evaluated"]
            )

    def test_finalize_without_samples_reports_empty_metrics(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            recorder = SimulationRecorder(
                Path(temporary_directory),
                run_name="empty",
            )
            self.addCleanup(recorder.close)

            report_path = recorder.finalize()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            metrics = report["metrics"]

            self.assertEqual(metrics["samples_written"], 0)
            self.assertIsNone(metrics["position_error_rms_m"])
            self.assertIsNone(metrics["orientation_error_rms_rad"])
            self.assertIsNone(metrics["ik_success_rate"])
            self.assertIsNone(metrics["cycle_period_p50_s"])
            self.assertIsNone(metrics["cycle_period_p99_s"])
            self.assertEqual(metrics["state_sample_counts"], {})
            self.assertEqual(recorder.csv_path.read_text(encoding="utf-8"), "")


if __name__ == "__main__":
    unittest.main()
