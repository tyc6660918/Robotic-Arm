from __future__ import annotations

import csv
import json
import math
from tempfile import TemporaryDirectory
import time
import unittest
from unittest.mock import patch

import numpy as np

from windows_sim.run_sim import ROOT, SimulationApp, _load_config
from windows_sim.sim.scenario import ScenarioPlayer
from windows_sim.sim.types import Pose


class SimulationIntegrationTests(unittest.TestCase):
    def test_attenuation_metric_uses_positive_db_for_reduction(self) -> None:
        self.assertAlmostEqual(SimulationApp._attenuation_db(0.1, 1.0), 20.0)
        self.assertAlmostEqual(SimulationApp._attenuation_db(1.0, 0.1), -20.0)
        self.assertIsNone(SimulationApp._attenuation_db(0.0, 1.0))

    def _config(self, output_directory: str) -> dict[str, object]:
        config = _load_config(ROOT / "config.json")
        config["logging"]["output_directory"] = output_directory
        return config

    def test_fast_run_has_exact_duration_and_truthful_ik_metrics(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            scenario = ScenarioPlayer.from_file(
                ROOT / "scenarios" / "axis_steps.json"
            )
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=scenario,
                realtime=False,
            )
            app.start_scenario()
            app.run_fast(2.0)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            metrics = report["metrics"]

            self.assertEqual(metrics["samples_written"], 200)
            self.assertAlmostEqual(metrics["simulated_duration_s"], 2.0, places=12)
            self.assertEqual(metrics["joint_limit_violation_count"], 0)
            self.assertNotIn("HOLD", metrics["state_sample_counts"])
            self.assertGreater(metrics["ik_attempts"], 0)
            self.assertEqual(metrics["ik_success_rate"], 1.0)
            self.assertTrue(report["metadata"]["offline_only"])
            self.assertFalse(report["metadata"]["serial_access"])

            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))
            self.assertAlmostEqual(float(rows[-1]["time_s"]), 2.0, places=12)
            attempts = [row for row in rows if row["ik_success"] != ""]
            self.assertEqual(len(attempts), metrics["ik_attempts"])
            self.assertTrue(
                all(row["ik_attempted"] == "True" for row in attempts)
            )
            for row in rows:
                target = np.array(
                    [float(row[f"target_joints_rad[{i}]"]) for i in range(6)]
                )
                actual = np.array(
                    [float(row[f"actual_joints_rad[{i}]"]) for i in range(6)]
                )
                self.assertAlmostEqual(
                    float(row["joint_tracking_error_rad"]),
                    float(np.max(np.abs(target - actual))),
                    places=12,
                )

    def test_render_geometry_is_throttled_to_the_configured_display_rate(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=None,
                realtime=False,
            )
            with patch.object(
                app,
                "_points_for_joints",
                wraps=app._points_for_joints,
            ) as points_for_joints:
                app.run_fast(0.1)

            maximum_snapshots = math.ceil(0.1 * app.render_rate_hz) + 1
            self.assertGreater(points_for_joints.call_count, 0)
            self.assertLessEqual(
                points_for_joints.call_count,
                2 * maximum_snapshots,
            )
            self.assertLessEqual(len(app._trajectory), maximum_snapshots + 1)
            app.stop()

    def test_configured_axis_map_is_used_by_the_application_mapper(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            config = self._config(temporary_directory)
            config["master_to_slave_axis_map"] = [
                [0.0, -1.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
            app = SimulationApp(config, scenario=None, realtime=False)
            app.mapper.capture(Pose.identity(), Pose.identity())

            mapped = app.mapper.map_pose(
                Pose(np.array([0.1, 0.0, 0.0]), np.array([0.0, 0.0, 0.0, 1.0]))
            )

            np.testing.assert_allclose(mapped.position, [0.0, 0.03, 0.0], atol=1e-12)
            app.stop()

    def test_openrst_command_is_gated_by_teleop_safety(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=None,
                realtime=False,
            )
            zeros = np.zeros(3, dtype=float)
            app.set_interactive_input(zeros, zeros, 1.0, False, False)
            app.run_fast(0.01)
            self.assertAlmostEqual(app.openrst.grasp, 0.0)

            app.set_interactive_input(zeros, zeros, 1.0, True, False)
            app.run_fast(0.01)
            self.assertAlmostEqual(app.openrst.grasp, 1.0)

            app.set_interactive_input(zeros, zeros, 0.0, True, True)
            app.run_fast(0.01)
            self.assertAlmostEqual(app.openrst.grasp, 1.0)

            app.set_interactive_input(zeros, zeros, 0.0, True, False)
            app.run_fast(0.01)
            self.assertAlmostEqual(app.openrst.grasp, 0.0)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))
            self.assertEqual(rows[0]["openrst_command_accepted"], "False")
            self.assertEqual(rows[1]["openrst_command_accepted"], "True")
            self.assertEqual(rows[2]["openrst_command_accepted"], "False")

    def test_mixed_session_reports_scenario_segment_boundaries(self) -> None:
        scenario = ScenarioPlayer(
            {
                "name": "short_segment",
                "type": "parametric",
                "duration_s": 0.05,
                "shape": "circle",
                "radius_m": 0.001,
                "frequency_hz": 0.1,
                "plane": "xy",
            }
        )
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=scenario,
                realtime=False,
            )
            app.run_fast(0.1)
            app.start_scenario()
            app.run_fast(0.1)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))

            self.assertEqual(report["metadata"]["scenario"], "mixed_session")
            self.assertEqual(report["metadata"]["session_scope"], "entire_simulation_app_lifetime")
            runs = report["metadata"]["scenario_runs"]
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["name"], "short_segment")
            self.assertTrue(runs[0]["finished"])
            self.assertAlmostEqual(runs[0]["start_time_s"], 0.1, places=12)
            self.assertAlmostEqual(runs[0]["end_time_s"], 0.15, places=12)
            self.assertEqual(report["metrics"]["samples_written"], 15)
            self.assertAlmostEqual(
                report["metrics"]["latest_scenario_duration_s"], 0.05, places=12
            )

    def test_ik_failure_requires_rearm_then_recovers(self) -> None:
        specification = {
            "name": "ik_recovery",
            "type": "faults",
            "duration_s": 2.0,
            "base_motion": {
                "shape": "circle",
                "radius_m": 0.005,
                "frequency_hz": 0.1,
                "plane": "xy",
            },
            "events": [
                {
                    "time_s": 1.2,
                    "duration_s": 0.05,
                    "fault": "force_ik_failure",
                },
                {"time_s": 1.25, "duration_s": 0.1, "fault": "rearm"},
            ],
        }
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=ScenarioPlayer(specification),
                realtime=False,
            )
            app.start_scenario()
            app.run_fast(1.8)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            failures = [row for row in rows if row["ik_success"] == "False"]
            self.assertEqual(len(failures), 1)
            self.assertEqual(failures[0]["state"], "HOLD")
            self.assertEqual(
                failures[0]["fault_reason"], "inverse kinematics failed"
            )
            self.assertTrue(
                any(
                    float(row["time_s"]) > 1.4 and row["state"] == "TELEOP"
                    for row in rows
                )
            )
            metrics = report["metrics"]
            attempt_count = sum(row["ik_success"] != "" for row in rows)
            self.assertEqual(metrics["ik_attempts"], attempt_count)
            self.assertLess(metrics["ik_success_rate"], 1.0)
            self.assertGreater(metrics["ik_success_rate"], 0.9)
            failure_index = rows.index(failures[0])
            self.assertGreater(failure_index, 0)
            previous = rows[failure_index - 1]
            for joint_index in range(6):
                field = f"target_joints_rad[{joint_index}]"
                self.assertAlmostEqual(
                    float(failures[0][field]),
                    float(previous[field]),
                    places=12,
                )

    def test_unreachable_target_reaches_ik_and_requires_rearm(self) -> None:
        specification = {
            "name": "unreachable_recovery",
            "type": "faults",
            "duration_s": 2.0,
            "base_motion": {
                "shape": "circle",
                "radius_m": 0.005,
                "frequency_hz": 0.1,
                "plane": "xy",
            },
            "events": [
                {
                    "time_s": 1.2,
                    "duration_s": 0.1,
                    "fault": "unreachable_target",
                    "offset_m": [0.0, 0.0, 2.0],
                },
                {"time_s": 1.3, "duration_s": 0.2, "fault": "rearm"},
            ],
        }
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=ScenarioPlayer(specification),
                realtime=False,
            )
            app.start_scenario()
            app.run_fast(1.8)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            injected_failures = [
                row
                for row in rows
                if row["unreachable_target_injected"] == "True"
                and row["ik_success"] == "False"
            ]
            self.assertGreaterEqual(len(injected_failures), 1)
            self.assertTrue(
                all(row["state"] == "HOLD" for row in injected_failures)
            )
            self.assertTrue(
                any(
                    float(row["time_s"]) > 1.55 and row["state"] == "TELEOP"
                    for row in rows
                )
            )

    def test_fatal_fault_latches_until_clear_and_fresh_rearm(self) -> None:
        specification = {
            "name": "fatal_fault_recovery",
            "type": "faults",
            "duration_s": 2.5,
            "base_motion": {
                "shape": "circle",
                "radius_m": 0.005,
                "frequency_hz": 0.1,
                "plane": "xy",
            },
            "events": [
                {"time_s": 1.2, "duration_s": 0.1, "fault": "fatal_fault"},
                {"time_s": 1.6, "duration_s": 0.1, "fault": "clear_fault"},
                {"time_s": 1.8, "duration_s": 0.1, "fault": "rearm"},
            ],
        }
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=ScenarioPlayer(specification),
                realtime=False,
            )
            app.start_scenario()
            app.run_fast(2.2)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            fault_rows = [row for row in rows if row["state"] == "FAULT"]
            self.assertGreaterEqual(len(fault_rows), 30)
            self.assertTrue(
                any(row["fatal_fault_injected"] == "True" for row in fault_rows)
            )
            self.assertTrue(
                any(
                    1.31 < float(row["time_s"]) < 1.59
                    and row["state"] == "FAULT"
                    and row["fatal_fault_injected"] == "False"
                    for row in rows
                )
            )
            self.assertTrue(
                all(
                    row["fault_reason"] == "injected fatal safety fault"
                    and int(row["fault_bits"]) != 0
                    and row["ik_attempted"] == "False"
                    and row["openrst_command_accepted"] == "False"
                    for row in fault_rows
                )
            )
            clear_rows = [
                row for row in rows if row["clear_fault_injected"] == "True"
            ]
            self.assertGreaterEqual(len(clear_rows), 1)
            self.assertTrue(all(row["state"] == "HOLD" for row in clear_rows))
            self.assertFalse(
                any(
                    1.7 < float(row["time_s"]) < 1.8
                    and row["state"] == "TELEOP"
                    for row in rows
                )
            )
            self.assertTrue(
                any(
                    float(row["time_s"]) > 1.95 and row["state"] == "TELEOP"
                    for row in rows
                )
            )
            self.assertGreater(report["metrics"]["state_sample_counts"]["FAULT"], 0)

    def test_scenario_completion_cannot_reuse_cached_deadman(self) -> None:
        scenario = ScenarioPlayer(
            {
                "name": "short_script",
                "type": "parametric",
                "duration_s": 0.02,
                "shape": "circle",
                "radius_m": 0.001,
                "frequency_hz": 0.1,
                "plane": "xy",
            }
        )
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=scenario,
                realtime=False,
            )
            zeros = np.zeros(3, dtype=float)
            app.set_interactive_input(zeros, zeros, 0.0, True, False)
            app.start_scenario()

            for _ in range(3):
                app._simulation_time_s += 0.01
                app._step(0.01, 0.01)
            self.assertEqual(app.safety.state.value, "HOLD")

            app.set_interactive_input(zeros, zeros, 0.0, False, False)
            app._simulation_time_s += 0.01
            app._step(0.01, 0.01)
            self.assertEqual(app.safety.state.value, "HOLD")

            app.set_interactive_input(zeros, zeros, 0.0, True, False)
            app._simulation_time_s += 0.01
            app._step(0.01, 0.01)
            self.assertEqual(app.safety.state.value, "TELEOP")
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))
            self.assertFalse(
                any(
                    row["fault_reason"] == "out-of-order input timestamp"
                    for row in rows
                )
            )

    def test_stuck_joint_enters_hold_and_recovers_only_after_rearm(self) -> None:
        specification = {
            "name": "stuck_joint_recovery",
            "type": "faults",
            "duration_s": 4.0,
            "base_motion": {
                "shape": "circle",
                "radius_m": 0.03,
                "frequency_hz": 0.2,
                "plane": "xy",
            },
            "events": [
                {
                    "time_s": 1.5,
                    "duration_s": 1.2,
                    "fault": "joint_stuck",
                    "joint_index": 2,
                },
                {"time_s": 2.7, "duration_s": 0.2, "fault": "rearm"},
            ],
        }
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=ScenarioPlayer(specification),
                realtime=False,
            )
            app.start_scenario()
            app.run_fast(3.8)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            stalled = [
                row
                for row in rows
                if row["fault_reason"] == "joint tracking error persisted"
            ]
            self.assertGreaterEqual(len(stalled), 1)
            self.assertTrue(
                any(
                    row["safety_stalled_joint_mask[2]"] == "True"
                    for row in stalled
                )
            )
            self.assertTrue(
                any(
                    float(row["time_s"]) > 3.0 and row["state"] == "TELEOP"
                    for row in rows
                )
            )

    def test_reset_preserves_monotonic_simulation_and_plant_time(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=None,
                realtime=False,
            )
            app.run_fast(0.1)
            before_reset = app.simulation_time_s
            app.reset()
            app.run_fast(0.1)
            self.assertGreater(app.simulation_time_s, before_reset)
            self.assertAlmostEqual(app.plant.time, app.simulation_time_s, places=12)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            metrics = report["metrics"]
            self.assertEqual(metrics["reset_count"], 1)
            self.assertEqual(
                metrics["accepted_plant_commands"], metrics["samples_written"]
            )

    def test_interactive_input_timeout_requires_fresh_rearm_cycle(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=None,
                realtime=False,
            )
            zeros = np.zeros(3, dtype=float)
            app.set_interactive_input(zeros, zeros, 0.0, True, False)
            app.run_fast(0.08)
            app.set_interactive_input(zeros, zeros, 0.0, True, False)
            app.run_fast(0.01)
            app.set_interactive_input(zeros, zeros, 0.0, False, False)
            app.run_fast(0.01)
            app.set_interactive_input(zeros, zeros, 0.0, True, False)
            app.run_fast(0.01)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertTrue(
                any(row["fault_reason"] == "master input timed out" for row in rows)
            )
            self.assertEqual(rows[-3]["fault_reason"], "rearm required")
            self.assertEqual(rows[-2]["state"], "HOLD")
            self.assertEqual(rows[-1]["state"], "TELEOP")

    def test_reset_clears_cached_interactive_deadman(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=None,
                realtime=False,
            )
            zeros = np.zeros(3, dtype=float)
            app.set_interactive_input(zeros, zeros, 0.0, True, False)
            app.run_fast(0.01)
            app.reset()
            app.run_fast(0.01)
            report_path = app.stop()
            report = json.loads(report_path.read_text(encoding="utf-8"))
            with (report_path.parent / report["csv"]).open(
                newline="", encoding="utf-8"
            ) as csv_file:
                rows = list(csv.DictReader(csv_file))

            self.assertEqual(rows[-1]["state"], "READY")
            self.assertEqual(rows[-1]["deadman"], "False")

    def test_realtime_cycle_records_full_stall_but_caps_dynamics_step(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=None,
                realtime=True,
            )
            observed: list[tuple[float, float]] = []

            def observe_step(dt: float, wall_dt: float) -> None:
                observed.append((dt, wall_dt))
                if len(observed) == 1:
                    time.sleep(0.08)
                else:
                    app._running.clear()

            app._step = observe_step  # type: ignore[method-assign]
            app.start()
            deadline = time.perf_counter() + 1.0
            while app.running and time.perf_counter() < deadline:
                time.sleep(0.001)
            app.stop()

            stalled_steps = [(dt, wall) for dt, wall in observed if wall > 0.06]
            self.assertGreaterEqual(len(stalled_steps), 1)
            self.assertTrue(all(dt <= 0.05 for dt, _ in stalled_steps))

    def test_control_thread_failure_is_reported_before_stop_raises(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=None,
                realtime=True,
            )

            def fail_step(_dt: float, _wall_dt: float) -> None:
                raise ValueError("injected control failure")

            app._step = fail_step  # type: ignore[method-assign]
            app.start()
            deadline = time.perf_counter() + 1.0
            while app.running and time.perf_counter() < deadline:
                time.sleep(0.001)
            self.assertFalse(app.running)

            with self.assertRaisesRegex(RuntimeError, "control loop failed"):
                app.stop()
            report = json.loads(app.recorder.report_path.read_text(encoding="utf-8"))
            metrics = report["metrics"]
            self.assertTrue(metrics["control_loop_failed"])
            self.assertIn("injected control failure", metrics["control_loop_error"])

            with self.assertRaisesRegex(RuntimeError, "already been stopped"):
                app.start()

    def test_finalized_simulation_cannot_run_again(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            app = SimulationApp(
                self._config(temporary_directory),
                scenario=None,
                realtime=False,
            )
            app.run_fast(0.01)
            app.stop()

            with self.assertRaisesRegex(RuntimeError, "already been stopped"):
                app.run_fast(0.01)


if __name__ == "__main__":
    unittest.main()
