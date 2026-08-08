#!/usr/bin/env python3
"""Windows-native, offline-only Dummy/OpenRST teleoperation simulator."""

from __future__ import annotations

import argparse
from collections import deque
import json
import math
from pathlib import Path
import threading
import time
from typing import Any, Mapping

import numpy as np
from scipy.spatial.transform import Rotation

if __package__:
    from .sim import (
        BoundedIKSolver,
        FaultConfig,
        IdealOpenRSTModel,
        MasterState,
        MockJointPlant,
        MultiToneAnalyzer,
        OneEuroPoseFilter,
        OpenRSTGeometry,
        PlantConfig,
        Pose,
        PoseRateLimiter,
        SAFE_JOINT_LIMITS_RAD,
        TeleopMapper,
        TeleopSafetyStateMachine,
        TeleopState,
        create_dummy_kinematics,
        load_openrst_urdf,
        within_safe_limits,
        wrapped_phase_difference,
    )
    from .sim.recorder import SimulationRecorder
    from .sim.scenario import ScenarioFaults, ScenarioPlayer, ScenarioSample
else:
    from sim import (
        BoundedIKSolver,
        FaultConfig,
        IdealOpenRSTModel,
        MasterState,
        MockJointPlant,
        MultiToneAnalyzer,
        OneEuroPoseFilter,
        OpenRSTGeometry,
        PlantConfig,
        Pose,
        PoseRateLimiter,
        SAFE_JOINT_LIMITS_RAD,
        TeleopMapper,
        TeleopSafetyStateMachine,
        TeleopState,
        create_dummy_kinematics,
        load_openrst_urdf,
        within_safe_limits,
        wrapped_phase_difference,
    )
    from sim.recorder import SimulationRecorder
    from sim.scenario import ScenarioFaults, ScenarioPlayer, ScenarioSample


ROOT = Path(__file__).resolve().parent


def _load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("configuration root must be a JSON object")
    return config


def _resolve_from_root(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (ROOT / path).resolve()


def _pose_error(target: Pose, actual: Pose) -> tuple[float, float]:
    position = float(np.linalg.norm(target.position - actual.position))
    target_rotation = Rotation.from_quat(target.orientation)
    actual_rotation = Rotation.from_quat(actual.orientation)
    orientation = float((actual_rotation.inv() * target_rotation).magnitude())
    return position, orientation


def _rpy_pose(position_m: np.ndarray, rpy_deg: np.ndarray) -> Pose:
    return Pose(
        np.asarray(position_m, dtype=float),
        Rotation.from_euler("xyz", np.asarray(rpy_deg, dtype=float), degrees=True).as_quat(),
    )


class SimulationApp:
    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        scenario: ScenarioPlayer | None = None,
        filter_enabled: bool | None = None,
        realtime: bool = True,
    ) -> None:
        self.config = dict(config)
        self.control_rate_hz = float(self.config["control_rate_hz"])
        if not math.isfinite(self.control_rate_hz) or self.control_rate_hz <= 0.0:
            raise ValueError("control_rate_hz must be finite and positive")
        self.period_s = 1.0 / self.control_rate_hz
        self.render_rate_hz = float(self.config["render_rate_hz"])
        if not math.isfinite(self.render_rate_hz) or self.render_rate_hz <= 0.0:
            raise ValueError("render_rate_hz must be finite and positive")
        self._snapshot_period_s = 1.0 / self.render_rate_hz
        self._next_snapshot_time_s = 0.0
        self.realtime = bool(realtime)
        self.scenario = scenario
        self._scenario_start_s = 0.0
        self._scenario_active = False
        self._scenario_finished = False
        self._active_scenario_run: dict[str, object] | None = None
        self._terminal_hold_active = False

        dummy_path = _resolve_from_root(str(self.config["dummy_urdf"]))
        self.kinematics = create_dummy_kinematics(dummy_path)
        self.ik = BoundedIKSolver(self.kinematics, max_nfev=15)
        openrst_path = _resolve_from_root(str(self.config["openrst_urdf"]))
        self.openrst_urdf = load_openrst_urdf(openrst_path)
        self.initial_joints = np.deg2rad(
            np.asarray(
                self.config.get(
                    "initial_joints_deg", [0.0, -30.0, 45.0, 0.0, 30.0, 0.0]
                ),
                dtype=float,
            )
        )
        if self.initial_joints.shape != (6,) or not within_safe_limits(
            self.initial_joints
        ):
            raise ValueError("initial_joints_deg must be a safe length-6 vector")
        self.target_joints = self.initial_joints.copy()

        plant_config = self.config["plant"]
        self.plant = MockJointPlant(
            PlantConfig(
                lower_limits=SAFE_JOINT_LIMITS_RAD[:, 0],
                upper_limits=SAFE_JOINT_LIMITS_RAD[:, 1],
                velocity_limits=float(plant_config["max_joint_velocity_rad_s"]),
                acceleration_limits=float(
                    plant_config["max_joint_acceleration_rad_s2"]
                ),
                jerk_limits=float(plant_config["max_joint_jerk_rad_s3"]),
                response_time=float(plant_config["response_time_s"]),
            ),
            initial_positions=self.initial_joints,
            faults=FaultConfig(
                command_delay=float(plant_config.get("command_delay_s", 0.0)),
                command_drop_probability=float(
                    plant_config.get("dropout_probability", 0.0)
                ),
                feedback_noise_std=float(
                    plant_config.get("feedback_noise_std_rad", 0.0)
                ),
            ),
            random_seed=int(plant_config.get("random_seed", 7)),
        )
        self.feedback_timeout_s = float(
            plant_config.get("feedback_timeout_s", self.config["input_timeout_s"])
        )
        self.max_joint_tracking_error_rad = float(
            plant_config.get("max_joint_tracking_error_rad", 0.12)
        )
        self.max_joint_target_velocity_rad_s = float(
            plant_config.get(
                "max_joint_target_velocity_rad_s",
                0.5 * float(plant_config["max_joint_velocity_rad_s"]),
            )
        )
        self.tracking_error_timeout_s = float(
            plant_config.get("tracking_error_timeout_s", 0.5)
        )
        self.stall_error_threshold_rad = float(
            plant_config.get("stall_error_threshold_rad", 0.015)
        )
        self.stall_motion_threshold_rad = float(
            plant_config.get("stall_motion_threshold_rad", 0.001)
        )
        self.stall_timeout_s = float(plant_config.get("stall_timeout_s", 0.3))
        if (
            self.feedback_timeout_s <= 0.0
            or self.max_joint_tracking_error_rad <= 0.0
            or self.max_joint_target_velocity_rad_s <= 0.0
            or self.tracking_error_timeout_s <= 0.0
            or self.stall_error_threshold_rad <= 0.0
            or self.stall_motion_threshold_rad <= 0.0
            or self.stall_timeout_s <= 0.0
        ):
            raise ValueError("plant safety timeouts and tracking limit must be positive")

        self.mapper = TeleopMapper(
            translation_scale=float(self.config["translation_scale"]),
            rotation_scale=float(self.config["rotation_scale"]),
            axis_map=np.asarray(
                self.config.get("master_to_slave_axis_map", np.eye(3)),
                dtype=float,
            ),
        )
        filter_config = self.config["filter"]
        self.filter_enabled = (
            bool(filter_config["enabled"])
            if filter_enabled is None
            else bool(filter_enabled)
        )
        self.pose_filter = OneEuroPoseFilter(
            position_min_cutoff=float(filter_config["min_cutoff_hz"]),
            position_beta=float(filter_config["beta"]),
            orientation_min_cutoff=float(filter_config["min_cutoff_hz"]),
            orientation_beta=float(filter_config["beta"]),
            derivative_cutoff=float(filter_config["derivative_cutoff_hz"]),
        )
        limits = self.config["limits"]
        self.rate_limiter = PoseRateLimiter(
            max_linear_speed=float(limits["max_linear_velocity_m_s"]),
            max_angular_speed=float(limits["max_angular_velocity_rad_s"]),
            max_linear_acceleration=float(limits["max_linear_acceleration_m_s2"]),
            max_angular_acceleration=float(limits["max_angular_acceleration_rad_s2"]),
        )
        self.safety = TeleopSafetyStateMachine(
            input_timeout=float(self.config["input_timeout_s"])
        )
        self.safety.enable()

        openrst_config = self.config["openrst"]
        self.openrst = IdealOpenRSTModel(
            OpenRSTGeometry(
                shaft_length=float(openrst_config["shaft_length_m"]),
                jaw_length=float(openrst_config["jaw_length_m"]),
                max_jaw_angle=math.radians(
                    float(openrst_config["max_jaw_opening_deg"])
                ),
            ),
            pitch_limit=math.radians(float(openrst_config["pitch_limit_deg"])),
            yaw_limit=math.radians(float(openrst_config["yaw_limit_deg"])),
        )

        self._lock = threading.RLock()
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._thread_error: BaseException | None = None
        self._finalized = False
        self._simulation_time_s = 0.0
        self._sequence = 0
        self._interactive_timestamp_s = 0.0
        self._interactive_sequence = 0
        self._interactive_sample = ScenarioSample(
            Pose.identity(), 0.0, False, False
        )
        self._last_master = MasterState(validity_flags=1)
        self._last_ik_success = True
        self._feedback_state = self.plant.state()
        self._tracking_violation_since: float | None = None
        self._stall_since = np.full(6, np.nan, dtype=float)
        self._stall_reference = self.initial_joints.copy()
        self._joint_limit_violation_count = 0
        self._deadline_miss_count = 0
        self._accepted_plant_commands_before_reset = 0
        self._dropped_plant_commands_before_reset = 0
        self._dropped_feedback_samples_before_reset = 0
        self._reset_count = 0
        self._frequency_analyzer: MultiToneAnalyzer | None = None
        self._frequency_analysis_start_s = math.inf
        self._frequency_axis = 0
        self._frequency_direction = np.array([1.0, 0.0, 0.0])
        trajectory_max_points = int(self.config.get("trajectory_max_points", 600))
        if trajectory_max_points <= 1:
            raise ValueError("trajectory_max_points must be greater than one")
        self._trajectory: deque[np.ndarray] = deque(maxlen=trajectory_max_points)
        self._snapshot: dict[str, object] = {}

        logging_config = self.config["logging"]
        output_root = _resolve_from_root(str(logging_config["output_directory"]))
        self.recorder = SimulationRecorder(
            output_root,
            csv_name=str(logging_config["csv_name"]),
            report_name=str(logging_config["report_name"]),
            metadata={
                "offline_only": True,
                "serial_access": False,
                "scenario": "interactive",
                "configured_scenario": self.scenario.name if self.scenario else None,
                "session_scope": "entire_simulation_app_lifetime",
                "scenario_runs": [],
                "control_rate_hz": self.control_rate_hz,
                "filter_enabled": self.filter_enabled,
                "realtime": self.realtime,
                "master_to_slave_axis_map": self.mapper.axis_map.tolist(),
                "dummy_urdf": str(dummy_path),
                "openrst_urdf": str(openrst_path),
                "openrst_model": "ideal_pitch_yaw_grasp",
                "initial_joints_deg": np.rad2deg(self.initial_joints).tolist(),
            },
        )
        try:
            self._reset_internal()
        except BaseException:
            self.recorder.close()
            raise

    @property
    def scenario_finished(self) -> bool:
        with self._lock:
            return self._scenario_finished

    @property
    def simulation_time_s(self) -> float:
        with self._lock:
            return self._simulation_time_s

    @property
    def running(self) -> bool:
        return self._running.is_set()

    def raise_if_failed(self, report_path: Path | None = None) -> None:
        with self._lock:
            error = self._thread_error
        if error is not None:
            detail = "simulation control loop failed"
            if report_path is not None:
                detail += f"; report: {report_path}"
            raise RuntimeError(detail) from error

    def _ensure_not_finalized(self) -> None:
        if self._finalized:
            raise RuntimeError("simulation has already been stopped and finalized")

    def set_interactive_input(
        self,
        position_m: np.ndarray,
        rpy_deg: np.ndarray,
        grasp: float,
        deadman: bool,
        clutch: bool,
    ) -> None:
        self._ensure_not_finalized()
        sample = ScenarioSample(
            pose=_rpy_pose(position_m, rpy_deg),
            grasp=float(np.clip(grasp, 0.0, 1.0)),
            deadman=bool(deadman),
            clutch=bool(clutch),
        )
        with self._lock:
            self._sequence += 1
            self._interactive_sequence = self._sequence
            self._interactive_timestamp_s = self._simulation_time_s
            self._interactive_sample = sample
            self._terminal_hold_active = False

    def start_scenario(self, scenario: ScenarioPlayer | None = None) -> None:
        self._ensure_not_finalized()
        self.raise_if_failed()
        with self._lock:
            self._finish_active_scenario_run(finished=False)
            if scenario is not None:
                self.scenario = scenario
            if self.scenario is None:
                return
            self._scenario_start_s = self._simulation_time_s
            self._scenario_active = True
            self._scenario_finished = False
            self._terminal_hold_active = False
            self.mapper.clear()
            self.pose_filter.reset()
            actual_joints = self._feedback_state.positions
            actual_pose = self.kinematics.flange_pose(actual_joints)
            self.rate_limiter.reset(actual_pose)
            self.ik.reset(actual_joints)
            self.safety.disable()
            self.safety.enable()
            self._last_ik_success = True
            self._tracking_violation_since = None
            self._stall_since.fill(np.nan)
            self._stall_reference = actual_joints.copy()
            scenario_runs = self.recorder.metadata["scenario_runs"]
            assert isinstance(scenario_runs, list)
            run_record: dict[str, object] = {
                "name": self.scenario.name,
                "start_time_s": self._scenario_start_s,
                "end_time_s": None,
                "finished": False,
            }
            scenario_runs.append(run_record)
            self._active_scenario_run = run_record
            if len(scenario_runs) == 1 and self._scenario_start_s <= 1e-12:
                self.recorder.metadata["scenario"] = self.scenario.name
            else:
                self.recorder.metadata["scenario"] = "mixed_session"
            self._configure_frequency_analysis(actual_pose)

    def _finish_active_scenario_run(self, *, finished: bool) -> None:
        if self._active_scenario_run is None:
            return
        self._active_scenario_run["end_time_s"] = self._simulation_time_s
        self._active_scenario_run["finished"] = bool(finished)
        self._active_scenario_run = None

    def _configure_frequency_analysis(self, slave_reference: Pose) -> None:
        self._frequency_analyzer = None
        if self.scenario is None or self.scenario.kind != "parametric":
            return
        specification = self.scenario.specification
        if str(specification.get("shape", "")) != "tremor":
            return
        axis_name = str(specification.get("axis", "x"))
        self._frequency_axis = {"x": 0, "y": 1, "z": 2}[axis_name]
        intentional = float(specification.get("intentional_frequency_hz", 0.5))
        tremor = float(specification.get("tremor_frequency_hz", 10.0))
        self._frequency_analyzer = MultiToneAnalyzer(
            (intentional, tremor),
            ("master_raw", "master_filtered", "actual_flange"),
        )
        warmup = float(specification.get("warmup_s", 0.0))
        settle = float(self.config.get("analysis_settle_s", 1.0))
        self._frequency_analysis_start_s = self._scenario_start_s + warmup + settle
        master_axis = np.zeros(3, dtype=float)
        master_axis[self._frequency_axis] = 1.0
        slave_rotation = slave_reference.as_matrix()[:3, :3]
        self._frequency_direction = (
            slave_rotation @ self.mapper.axis_map @ master_axis
        )

    @staticmethod
    def _attenuation_db(response: float, reference: float) -> float | None:
        if response <= 0.0 or reference <= 0.0:
            return None
        return 20.0 * math.log10(reference / response)

    def _frequency_metrics(self) -> dict[str, object]:
        analyzer = self._frequency_analyzer
        if analyzer is None:
            return {}
        estimates = analyzer.estimates()
        if estimates is None:
            return {"frequency_analysis_samples": analyzer.sample_count}

        specification = self.scenario.specification if self.scenario else {}
        intentional_key = f"{float(specification.get('intentional_frequency_hz', 0.5)):g}"
        tremor_key = f"{float(specification.get('tremor_frequency_hz', 10.0)):g}"

        def tone(signal: str, key: str) -> dict[str, float]:
            return estimates[signal]["tones"][key]  # type: ignore[index,return-value]

        raw_intentional = tone("master_raw", intentional_key)
        filtered_intentional = tone("master_filtered", intentional_key)
        raw_tremor = tone("master_raw", tremor_key)
        filtered_tremor = tone("master_filtered", tremor_key)
        actual_intentional = tone("actual_flange", intentional_key)
        actual_tremor = tone("actual_flange", tremor_key)

        intentional_loss = (
            100.0
            * (1.0 - filtered_intentional["amplitude"] / raw_intentional["amplitude"])
            if raw_intentional["amplitude"] > 0.0
            else None
        )
        tremor_attenuation = self._attenuation_db(
            filtered_tremor["amplitude"], raw_tremor["amplitude"]
        )
        expected_actual_tremor = (
            raw_tremor["amplitude"] * self.mapper.translation_scale
        )
        expected_actual_intentional = (
            raw_intentional["amplitude"] * self.mapper.translation_scale
        )
        actual_intentional_loss = (
            100.0
            * (
                1.0
                - actual_intentional["amplitude"]
                / expected_actual_intentional
            )
            if expected_actual_intentional > 0.0
            else None
        )
        return {
            "frequency_analysis_scenario": self.scenario.name if self.scenario else None,
            "frequency_analysis_samples": analyzer.sample_count,
            "frequency_analysis": estimates,
            "intentional_amplitude_loss_percent": intentional_loss,
            "tremor_filter_attenuation_db": tremor_attenuation,
            "tremor_filter_phase_lag_deg": math.degrees(
                wrapped_phase_difference(
                    filtered_tremor["phase_rad"], raw_tremor["phase_rad"]
                )
            ),
            "actual_intentional_amplitude_m": actual_intentional["amplitude"],
            "actual_intentional_amplitude_loss_percent": actual_intentional_loss,
            "actual_tremor_amplitude_m": actual_tremor["amplitude"],
            "actual_tremor_attenuation_db": self._attenuation_db(
                actual_tremor["amplitude"], expected_actual_tremor
            ),
            "filter_intentional_amplitude_pass": (
                intentional_loss is not None and intentional_loss < 5.0
            ),
            "filter_tremor_attenuation_pass": (
                tremor_attenuation is not None and tremor_attenuation > 15.0
            ),
        }

    def reset(self) -> None:
        self._ensure_not_finalized()
        self.raise_if_failed()
        with self._lock:
            self._finish_active_scenario_run(finished=False)
            self._reset_count += 1
            self._reset_internal()

    def _reset_internal(self) -> None:
        self._accepted_plant_commands_before_reset += self.plant.accepted_command_count
        self._dropped_plant_commands_before_reset += self.plant.dropped_command_count
        self._dropped_feedback_samples_before_reset += self.plant.dropped_feedback_count
        self.plant = MockJointPlant(
            self.plant.config,
            initial_positions=self.initial_joints,
            random_seed=int(self.config["plant"].get("random_seed", 7)),
        )
        self.plant.time = self._simulation_time_s
        self._configure_faults(ScenarioFaults())
        self._feedback_state = self.plant.state()
        self.target_joints = self.initial_joints.copy()
        actual_pose = self.kinematics.flange_pose(self.initial_joints)
        self.mapper.clear()
        self.mapper.capture(Pose.identity(), actual_pose)
        self.pose_filter.reset(Pose.identity(), self._simulation_time_s)
        self.rate_limiter.reset(actual_pose)
        self.ik.reset(self.initial_joints)
        self.safety.disable()
        self.safety.enable()
        self.openrst.reset()
        self._interactive_sample = ScenarioSample(
            Pose.identity(), 0.0, False, False
        )
        self._interactive_timestamp_s = self._simulation_time_s
        self._interactive_sequence = self._sequence
        self._last_master = MasterState(
            timestamp=self._simulation_time_s,
            sequence=self._sequence,
            flange_pose=Pose.identity(),
            grasp=0.0,
            deadman=False,
            clutch=False,
            validity_flags=1,
        )
        self._last_ik_success = True
        self._tracking_violation_since = None
        self._stall_since.fill(np.nan)
        self._stall_reference = self.initial_joints.copy()
        self._frequency_analyzer = None
        self._scenario_active = False
        self._scenario_finished = False
        self._terminal_hold_active = False
        self._trajectory.clear()
        self._update_snapshot(
            actual_pose,
            actual_pose,
            self.initial_joints,
            None,
            "READY",
            force=True,
        )

    def start(self) -> None:
        self._ensure_not_finalized()
        self.raise_if_failed()
        if self._thread is not None and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def run_fast(self, duration_s: float) -> None:
        self._ensure_not_finalized()
        self.raise_if_failed()
        if self.realtime:
            raise RuntimeError("run_fast() requires realtime=False")
        duration = float(duration_s)
        if not math.isfinite(duration) or duration <= 0.0:
            raise ValueError("duration_s must be finite and positive")
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("run_fast() cannot run beside the control thread")

        target_time = self._simulation_time_s + duration
        last_wall = time.perf_counter()
        self._running.set()
        try:
            while self._running.is_set() and not self.scenario_finished:
                with self._lock:
                    remaining = target_time - self._simulation_time_s
                    if remaining <= 1e-12:
                        break
                    dt = min(self.period_s, remaining)
                    tick_wall = time.perf_counter()
                    wall_dt = max(1e-9, tick_wall - last_wall)
                    last_wall = tick_wall
                    if wall_dt > 0.02:
                        self._deadline_miss_count += 1
                    self._simulation_time_s += dt
                    self._step(dt, wall_dt)
                time.sleep(0)
        except BaseException as exc:
            with self._lock:
                self._thread_error = exc
            raise
        finally:
            self._running.clear()

    def stop(self, *, raise_on_control_error: bool = True) -> Path:
        self._running.clear()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=10.0)
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError("simulation control loop did not stop within 10 seconds")
        with self._lock:
            control_error = self._thread_error
            self._finish_active_scenario_run(finished=False)
            scenario_runs = self.recorder.metadata["scenario_runs"]
            assert isinstance(scenario_runs, list)
            latest_scenario_duration = None
            if scenario_runs:
                latest = scenario_runs[-1]
                if isinstance(latest, dict) and latest.get("end_time_s") is not None:
                    latest_scenario_duration = float(latest["end_time_s"]) - float(
                        latest["start_time_s"]
                    )
        extra_metrics: dict[str, object] = {
            "scenario_finished": self._scenario_finished,
            "simulated_duration_s": self._simulation_time_s,
            "accepted_plant_commands": (
                self._accepted_plant_commands_before_reset
                + self.plant.accepted_command_count
            ),
            "dropped_plant_commands": (
                self._dropped_plant_commands_before_reset
                + self.plant.dropped_command_count
            ),
            "dropped_feedback_samples": (
                self._dropped_feedback_samples_before_reset
                + self.plant.dropped_feedback_count
            ),
            "reset_count": self._reset_count,
            "latest_scenario_duration_s": latest_scenario_duration,
            "joint_limit_violation_count": self._joint_limit_violation_count,
            "deadline_miss_count": self._deadline_miss_count,
            "control_loop_failed": control_error is not None,
            "control_loop_error": (
                f"{type(control_error).__name__}: {control_error}"
                if control_error is not None
                else None
            ),
        }
        extra_metrics.update(self._frequency_metrics())
        report_path = self.recorder.finalize(extra_metrics)
        self._finalized = True
        if raise_on_control_error:
            self.raise_if_failed(report_path)
        return report_path

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            copied: dict[str, object] = {}
            for key, value in self._snapshot.items():
                copied[key] = value.copy() if isinstance(value, np.ndarray) else value
            return copied

    def _run_loop(self) -> None:
        next_tick = time.perf_counter()
        last_wall = next_tick
        try:
            while self._running.is_set():
                if self.realtime:
                    now_wall = time.perf_counter()
                    if now_wall < next_tick:
                        time.sleep(next_tick - now_wall)
                    tick_wall = time.perf_counter()
                    wall_dt = max(1e-6, tick_wall - last_wall)
                    dt = min(0.05, wall_dt)
                    last_wall = tick_wall
                    next_tick += self.period_s
                    if tick_wall - next_tick > self.period_s:
                        next_tick = tick_wall + self.period_s
                else:
                    tick_wall = time.perf_counter()
                    wall_dt = max(1e-9, tick_wall - last_wall)
                    last_wall = tick_wall
                    dt = self.period_s

                with self._lock:
                    if wall_dt > 0.02:
                        self._deadline_miss_count += 1
                    self._simulation_time_s += wall_dt if self.realtime else dt
                    self._step(dt, wall_dt)

                if not self.realtime:
                    time.sleep(0)
        except BaseException as exc:
            with self._lock:
                self._thread_error = exc
            self._running.clear()

    def _current_sample(self) -> tuple[ScenarioSample, bool]:
        if self._terminal_hold_active:
            return ScenarioSample(Pose.identity(), self.openrst.grasp, True, False), False
        if self.scenario is None or not self._scenario_active:
            return self._interactive_sample, True
        elapsed = self._simulation_time_s - self._scenario_start_s
        if elapsed >= self.scenario.duration_s:
            self._scenario_finished = True
            self._scenario_active = False
            self._finish_active_scenario_run(finished=True)
            self._terminal_hold_active = True
            self.safety.require_rearm("scenario completed; rearm required")
            return ScenarioSample(Pose.identity(), 0.0, True, False), False
        return self.scenario.sample(elapsed), False

    def _master_state(
        self,
        sample: ScenarioSample,
        *,
        interactive: bool,
    ) -> MasterState:
        faults = sample.faults
        if faults.input_dropout:
            return self._last_master

        if interactive:
            timestamp = self._interactive_timestamp_s
            sequence = self._interactive_sequence
        else:
            self._sequence += 1
            timestamp = self._simulation_time_s
            sequence = self._sequence
        if faults.timestamp_out_of_order:
            timestamp = self._last_master.timestamp - 0.1
        master = MasterState(
            timestamp=timestamp,
            sequence=sequence,
            flange_pose=sample.pose,
            flange_twist=np.zeros(6, dtype=float),
            grasp=sample.grasp,
            deadman=sample.deadman,
            clutch=sample.clutch,
            validity_flags=sample.validity_flags,
        )
        self._last_master = master
        return master

    def _configure_faults(self, faults: ScenarioFaults) -> None:
        plant_config = self.config["plant"]
        self.plant.configure_faults(
            FaultConfig(
                command_delay=max(
                    float(plant_config.get("command_delay_s", 0.0)),
                    float(faults.command_delay_s),
                ),
                command_drop_probability=max(
                    float(plant_config.get("dropout_probability", 0.0)),
                    float(faults.command_drop_probability),
                ),
                feedback_noise_std=float(plant_config["feedback_noise_std_rad"]),
                feedback_drop_probability=float(faults.feedback_drop_probability),
                feedback_frozen=bool(faults.feedback_frozen),
                stuck_joints=tuple(faults.stuck_joints),
            )
        )

    def _tracking_is_ok(
        self,
        actual_joints: np.ndarray,
    ) -> tuple[bool, float, np.ndarray]:
        joint_errors = np.abs(self.target_joints - actual_joints)
        tracking_error = float(np.max(joint_errors))
        if tracking_error <= self.max_joint_tracking_error_rad:
            self._tracking_violation_since = None
            error_tracking_ok = True
        elif self._tracking_violation_since is None:
            self._tracking_violation_since = self._simulation_time_s
            error_tracking_ok = True
        else:
            elapsed = self._simulation_time_s - self._tracking_violation_since
            error_tracking_ok = elapsed <= self.tracking_error_timeout_s

        stalled = np.zeros(6, dtype=bool)
        for index, error in enumerate(joint_errors):
            if error <= self.stall_error_threshold_rad:
                self._stall_since[index] = np.nan
                self._stall_reference[index] = actual_joints[index]
                continue
            movement = abs(actual_joints[index] - self._stall_reference[index])
            if np.isnan(self._stall_since[index]) or movement > self.stall_motion_threshold_rad:
                self._stall_since[index] = self._simulation_time_s
                self._stall_reference[index] = actual_joints[index]
                continue
            stalled[index] = (
                self._simulation_time_s - self._stall_since[index]
                > self.stall_timeout_s
            )
        return error_tracking_ok and not np.any(stalled), tracking_error, stalled

    def _step(self, dt: float, wall_dt: float) -> None:
        compute_started = time.perf_counter()
        sample, interactive = self._current_sample()
        self._configure_faults(sample.faults)
        master = self._master_state(sample, interactive=interactive)
        actual_joints = self._feedback_state.positions.copy()
        actual_pose = self.kinematics.flange_pose(actual_joints)
        safety_feedback_age = max(
            0.0, self._simulation_time_s - self._feedback_state.timestamp
        )
        feedback_fresh = safety_feedback_age <= self.feedback_timeout_s
        (
            tracking_ok,
            safety_joint_tracking_error,
            safety_stalled_joints,
        ) = self._tracking_is_ok(actual_joints)

        if sample.faults.fatal_fault:
            if self.safety.state is not TeleopState.FAULT:
                self.safety.fault("injected fatal safety fault")
        elif (
            sample.faults.clear_fault
            and self.safety.state is TeleopState.FAULT
        ):
            self.safety.clear_fault()

        safety = self.safety.update_master(
            master,
            self._simulation_time_s,
            ik_success=True,
            joints_within_limits=True,
            feedback_fresh=feedback_fresh,
            tracking_ok=tracking_ok,
        )
        effective_clutch = master.clutch or not master.deadman
        filtered_master = master.flange_pose

        if effective_clutch:
            self.pose_filter.reset(master.flange_pose, self._simulation_time_s)
            mapped_target = self.mapper.update(
                master.flange_pose, actual_pose, clutch=True
            )
            self.rate_limiter.reset(actual_pose)
        else:
            if self.filter_enabled:
                filtered_master = self.pose_filter.filter(
                    master.flange_pose, self._simulation_time_s
                )
            mapped_target = self.mapper.update(
                filtered_master, actual_pose, clutch=False
            )

        limited_target = self.rate_limiter.update(mapped_target, dt)
        if sample.faults.unreachable_target:
            # Fault injection bypasses filtering/rate limits so IK sees the
            # intentionally unreachable Cartesian command during its window.
            limited_target = self.mapper.map_pose(master.flange_pose)
        ik_result = None
        ik_attempted = False
        ik_success: bool | None = None
        ik_message = ""
        ik_time_s = 0.0
        command_accepted = False
        joint_target_scale = 1.0
        if safety.motion_allowed:
            ik_attempted = True
            if sample.faults.force_ik_failure:
                ik_success = False
                joints_safe = True
                ik_message = "injected IK non-convergence"
            else:
                ik_started = time.perf_counter()
                ik_result = self.ik.solve(limited_target, self.target_joints)
                ik_time_s = time.perf_counter() - ik_started
                ik_success = ik_result.success
                joints_safe = within_safe_limits(ik_result.joints)
                ik_message = ik_result.message
            safety = self.safety.update_master(
                master,
                self._simulation_time_s,
                ik_success=bool(ik_success),
                joints_within_limits=joints_safe,
                feedback_fresh=feedback_fresh,
                tracking_ok=tracking_ok,
            )
            self._last_ik_success = bool(ik_success)
            if safety.motion_allowed and joints_safe and ik_result is not None:
                joint_delta = ik_result.joints - self.target_joints
                step_limits = np.minimum(
                    self.plant.config.velocity_limits,
                    self.max_joint_target_velocity_rad_s,
                ) * dt
                ratios = np.divide(
                    step_limits,
                    np.abs(joint_delta),
                    out=np.full_like(joint_delta, np.inf),
                    where=np.abs(joint_delta) > 1e-12,
                )
                joint_target_scale = min(1.0, float(np.min(ratios)))
                self.target_joints = (
                    self.target_joints + joint_target_scale * joint_delta
                )
                self.ik.reset(self.target_joints)
                if joint_target_scale < 1.0 - 1e-12:
                    self.rate_limiter.synchronize(
                        self.kinematics.flange_pose(self.target_joints)
                    )
                command_accepted = self.plant.command(
                    self.target_joints, self._simulation_time_s
                )
            else:
                command_accepted = self.plant.command(
                    self.target_joints, self._simulation_time_s
                )
                self.rate_limiter.reset(actual_pose)
        else:
            self.target_joints = actual_joints.copy()
            command_accepted = self.plant.command(
                self.target_joints, self._simulation_time_s
            )
            self.rate_limiter.reset(actual_pose)

        if not within_safe_limits(self.target_joints):
            self._joint_limit_violation_count += 1
        true_state = self.plant.step(dt, self._simulation_time_s)
        feedback = self.plant.feedback()
        feedback_available = feedback is not None
        if feedback is not None:
            self._feedback_state = feedback
        state = self._feedback_state
        actual_pose = self.kinematics.flange_pose(state.positions)
        true_pose = self.kinematics.flange_pose(true_state.positions)
        target_pose = self.kinematics.flange_pose(self.target_joints)
        feedback_age = max(0.0, self._simulation_time_s - state.timestamp)
        joint_tracking_error = float(
            np.max(np.abs(self.target_joints - state.positions))
        )
        position_error, orientation_error = _pose_error(target_pose, actual_pose)
        mapped_position_error, mapped_orientation_error = _pose_error(
            limited_target, actual_pose
        )
        openrst_command_accepted = False
        if safety.motion_allowed:
            self.openrst.set_command(0.0, 0.0, master.grasp)
            openrst_command_accepted = True
        openrst_state = self.openrst.forward(actual_pose)
        if (
            self._frequency_analyzer is not None
            and self._simulation_time_s >= self._frequency_analysis_start_s
        ):
            self._frequency_analyzer.update(
                self._simulation_time_s - self._frequency_analysis_start_s,
                {
                    "master_raw": float(
                        master.flange_pose.position[self._frequency_axis]
                    ),
                    "master_filtered": float(
                        filtered_master.position[self._frequency_axis]
                    ),
                    "actual_flange": float(
                        np.dot(actual_pose.position, self._frequency_direction)
                    ),
                },
            )
        reason = safety.reason or "tracking"
        status_text = f"State: {safety.state.value}\n{reason}"
        self._update_snapshot(
            actual_pose,
            target_pose,
            state.positions,
            openrst_state,
            status_text,
            filtered_master=filtered_master,
            master=master,
            position_error=position_error,
            orientation_error=orientation_error,
        )
        self.recorder.record(
            {
                "time_s": self._simulation_time_s,
                "wall_time_s": time.time(),
                "cycle_period_s": wall_dt,
                "compute_time_s": time.perf_counter() - compute_started,
                "dt_s": dt,
                "state": safety.state.value,
                "fault_bits": safety.fault_bits,
                "fault_reason": safety.reason,
                "message_age_s": safety.message_age,
                "input_timestamp_s": master.timestamp,
                "master_sequence": master.sequence,
                "master_raw": master.flange_pose,
                "master_filtered": filtered_master,
                "mapped_flange": mapped_target,
                "limited_flange": limited_target,
                "target_flange": target_pose,
                "actual_flange": actual_pose,
                "true_flange": true_pose,
                "target_joints_rad": self.target_joints,
                "actual_joints_rad": state.positions,
                "true_joints_rad": true_state.positions,
                "actual_joint_velocity_rad_s": state.velocities,
                "actual_joint_acceleration_rad_s2": state.accelerations,
                "grasp": master.grasp,
                "openrst_pitch_rad": self.openrst.pitch,
                "openrst_yaw_rad": self.openrst.yaw,
                "openrst_grasp": self.openrst.grasp,
                "openrst_command_accepted": openrst_command_accepted,
                "openrst_command_clipped": self.openrst.last_command_was_clipped,
                "deadman": master.deadman,
                "clutch": master.clutch,
                "validity_flags": master.validity_flags,
                "ik_attempted": ik_attempted,
                "ik_success": ik_success,
                "ik_time_s": ik_time_s,
                "ik_evaluations": ik_result.iterations if ik_result else 0,
                "ik_position_error_m": (
                    ik_result.position_error if ik_result else None
                ),
                "ik_orientation_error_rad": (
                    ik_result.orientation_error if ik_result else None
                ),
                "ik_message": ik_message,
                "command_accepted": command_accepted,
                "feedback_available": feedback_available,
                "feedback_age_s": feedback_age,
                "safety_feedback_age_s": safety_feedback_age,
                "safety_feedback_fresh": feedback_fresh,
                "joint_tracking_error_rad": joint_tracking_error,
                "safety_joint_tracking_error_rad": safety_joint_tracking_error,
                "safety_stalled_joint_mask": safety_stalled_joints,
                "joint_target_scale": joint_target_scale,
                "unreachable_target_injected": sample.faults.unreachable_target,
                "fatal_fault_injected": sample.faults.fatal_fault,
                "clear_fault_injected": sample.faults.clear_fault,
                "position_error_m": position_error,
                "orientation_error_rad": orientation_error,
                "mapped_position_error_m": mapped_position_error,
                "mapped_orientation_error_rad": mapped_orientation_error,
            }
        )

    def _points_for_joints(self, joints: np.ndarray) -> np.ndarray:
        transforms = self.kinematics.forward_all(joints)
        return np.asarray([matrix[:3, 3] for matrix in transforms.values()])

    def _update_snapshot(
        self,
        actual_pose: Pose,
        target_pose: Pose,
        actual_joints: np.ndarray,
        openrst_state: object | None,
        status_text: str,
        *,
        filtered_master: Pose | None = None,
        master: MasterState | None = None,
        position_error: float = 0.0,
        orientation_error: float = 0.0,
        force: bool = False,
    ) -> None:
        if not force and self._simulation_time_s + 1e-12 < self._next_snapshot_time_s:
            return
        if force:
            self._next_snapshot_time_s = (
                self._simulation_time_s + self._snapshot_period_s
            )
        else:
            intervals = max(
                1,
                int(
                    math.floor(
                        (self._simulation_time_s - self._next_snapshot_time_s)
                        / self._snapshot_period_s
                    )
                )
                + 1,
            )
            self._next_snapshot_time_s += intervals * self._snapshot_period_s
        self._trajectory.append(actual_pose.position.copy())
        if openrst_state is None:
            openrst_points = np.empty((0, 3), dtype=float)
        else:
            openrst_points = np.asarray(
                [
                    openrst_state.mount_pose.position,
                    openrst_state.pitch_pose.position,
                    openrst_state.yaw_pose.position,
                    openrst_state.tcp_pose.position,
                    openrst_state.left_jaw_tip,
                    openrst_state.tcp_pose.position,
                    openrst_state.right_jaw_tip,
                ]
            )
        self._snapshot = {
            "actual_points": self._points_for_joints(actual_joints),
            "target_points": self._points_for_joints(self.target_joints),
            "openrst_points": openrst_points,
            "trajectory": np.asarray(self._trajectory),
            "actual_flange": actual_pose.as_matrix(),
            "target_flange": target_pose.as_matrix(),
            "master_transform": (
                filtered_master.as_matrix() if filtered_master else np.eye(4)
            ),
            "position_error_m": position_error,
            "orientation_error_rad": orientation_error,
            "status_text": status_text,
            "master_sequence": master.sequence if master else 0,
        }


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline Dummy/OpenRST Cartesian teleoperation simulator"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config.json",
        help="JSON configuration path",
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        help="JSON scenario path; headless mode defaults to axis_steps.json",
    )
    parser.add_argument("--headless", action="store_true", help="run without a GUI")
    parser.add_argument(
        "--duration",
        type=float,
        help="stop after this many simulated seconds",
    )
    parser.add_argument(
        "--no-filter", action="store_true", help="disable the One Euro pose filter"
    )
    parser.add_argument(
        "--no-realtime",
        action="store_true",
        help="run headless scenarios as quickly as possible",
    )
    return parser


def main() -> int:
    args = _build_argument_parser().parse_args()
    if args.no_realtime and not args.headless:
        raise SystemExit("--no-realtime requires --headless")

    scenario_path = args.scenario or ROOT / "scenarios" / "axis_steps.json"
    scenario = ScenarioPlayer.from_file(scenario_path)
    config = _load_config(args.config.resolve())
    app = SimulationApp(
        config,
        scenario=scenario,
        filter_enabled=False if args.no_filter else None,
        realtime=not args.no_realtime,
    )

    run_error: BaseException | None = None
    report: Path | None = None
    try:
        if args.headless:
            duration = args.duration
            if duration is None:
                duration = scenario.duration_s + 0.25
            if not math.isfinite(duration) or duration <= 0.0:
                raise ValueError("--duration must be finite and positive")
            app.start_scenario()
            if args.no_realtime:
                app.run_fast(duration)
            else:
                app.start()
                deadline = time.perf_counter() + duration
                while (
                    time.perf_counter() < deadline
                    and not app.scenario_finished
                    and app.running
                ):
                    app.raise_if_failed()
                    time.sleep(0.05)
                app.raise_if_failed()
        else:
            import matplotlib

            matplotlib.use("TkAgg")
            if __package__:
                from .sim.viewer import InteractiveViewer
            else:
                from sim.viewer import InteractiveViewer

            if args.scenario is not None:
                app.start_scenario()

            viewer = InteractiveViewer(
                snapshot_provider=app.snapshot,
                input_callback=lambda command: app.set_interactive_input(
                    command.position_m,
                    command.rpy_deg,
                    command.grasp,
                    command.deadman,
                    command.clutch,
                ),
                reset_callback=app.reset,
                script_callback=app.start_scenario,
                health_check=app.raise_if_failed,
                master_publish_rate_hz=float(config["control_rate_hz"]),
                render_rate_hz=float(config["render_rate_hz"]),
            )
            app.start()
            viewer.show()
    except KeyboardInterrupt:
        pass
    except BaseException as exc:
        run_error = exc
    finally:
        try:
            report = app.stop(raise_on_control_error=False)
            print(f"Simulation report: {report}")
        except BaseException as stop_error:
            if run_error is None:
                raise
            run_error.add_note(f"simulation cleanup also failed: {stop_error!r}")
    if run_error is not None:
        raise run_error.with_traceback(run_error.__traceback__)
    app.raise_if_failed(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
