"""Deterministic scripted master trajectories and fault schedules."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

from .types import Pose


@dataclass(frozen=True)
class ScenarioFaults:
    input_dropout: bool = False
    timestamp_out_of_order: bool = False
    command_delay_s: float = 0.0
    command_drop_probability: float = 0.0
    feedback_drop_probability: float = 0.0
    feedback_frozen: bool = False
    stuck_joints: tuple[int, ...] = ()
    force_ik_failure: bool = False
    unreachable_target: bool = False
    fatal_fault: bool = False
    clear_fault: bool = False


@dataclass(frozen=True)
class ScenarioSample:
    pose: Pose
    grasp: float
    deadman: bool
    clutch: bool
    validity_flags: int = 1
    faults: ScenarioFaults = field(default_factory=ScenarioFaults)


class ScenarioPlayer:
    def __init__(self, specification: dict[str, Any], source: Path | None = None) -> None:
        if not isinstance(specification, dict):
            raise ValueError("scenario specification must be a JSON object")
        self.specification = specification
        self.source = source
        self.name = str(specification.get("name", source.stem if source else "scenario"))
        self.kind = str(specification.get("type", "keyframes"))
        self.duration_s = float(specification.get("duration_s", 0.0))
        if not math.isfinite(self.duration_s) or self.duration_s <= 0.0:
            raise ValueError("scenario duration_s must be finite and positive")
        if self.kind not in {"keyframes", "parametric", "faults"}:
            raise ValueError(f"unsupported scenario type: {self.kind}")
        self._validate_specification()
        self._fault_base_player: ScenarioPlayer | None = None
        if self.kind == "faults":
            base = dict(self.specification.get("base_motion", {}))
            base.update(
                {
                    "name": self.name,
                    "type": "parametric",
                    "duration_s": self.duration_s,
                    "warmup_s": 1.0,
                    "deadman": True,
                }
            )
            self._fault_base_player = ScenarioPlayer(base)

    @staticmethod
    def _finite_vector(value: Any, size: int, name: str) -> np.ndarray:
        result = np.asarray(value, dtype=float)
        if result.shape != (size,) or np.any(~np.isfinite(result)):
            raise ValueError(f"{name} must be a finite length-{size} vector")
        return result

    def _validate_specification(self) -> None:
        if self.kind == "keyframes":
            keyframes = self.specification.get("keyframes")
            if not isinstance(keyframes, list) or not keyframes:
                raise ValueError("keyframe scenario requires a non-empty keyframes list")
            times: list[float] = []
            for index, frame in enumerate(keyframes):
                if not isinstance(frame, dict) or "time_s" not in frame:
                    raise ValueError(f"keyframe {index} must be an object with time_s")
                timestamp = float(frame["time_s"])
                if not math.isfinite(timestamp) or not 0.0 <= timestamp <= self.duration_s:
                    raise ValueError(f"keyframe {index} time_s is outside the scenario")
                times.append(timestamp)
                self._finite_vector(
                    frame.get("position_m", [0.0, 0.0, 0.0]),
                    3,
                    f"keyframe {index} position_m",
                )
                self._finite_vector(
                    frame.get("rpy_deg", [0.0, 0.0, 0.0]),
                    3,
                    f"keyframe {index} rpy_deg",
                )
            if any(after <= before for before, after in zip(times, times[1:])):
                raise ValueError("keyframe time_s values must be strictly increasing")
            return

        if self.kind == "parametric":
            shape = str(self.specification.get("shape", "circle"))
            if shape not in {"circle", "tremor", "figure_eight"}:
                raise ValueError(f"unsupported parametric shape: {shape}")
            self._finite_vector(
                self.specification.get("center_m", [0.0, 0.0, 0.0]),
                3,
                "center_m",
            )
            self._finite_vector(
                self.specification.get("rpy_amplitude_deg", [0.0, 0.0, 0.0]),
                3,
                "rpy_amplitude_deg",
            )
            return

        events = self.specification.get("events", [])
        if not isinstance(events, list):
            raise ValueError("fault scenario events must be a list")
        allowed_faults = {
            "clear_fault",
            "command_delay",
            "fatal_fault",
            "feedback_dropout",
            "feedback_freeze",
            "force_ik_failure",
            "input_dropout",
            "invalid_input",
            "joint_stuck",
            "packet_dropout",
            "rearm",
            "timestamp_out_of_order",
            "unreachable_target",
        }
        for index, event in enumerate(events):
            if not isinstance(event, dict):
                raise ValueError(f"fault event {index} must be an object")
            fault = str(event.get("fault", ""))
            if fault not in allowed_faults:
                raise ValueError(f"unsupported fault event: {fault}")
            start = float(event.get("time_s", -1.0))
            duration = float(event.get("duration_s", 0.0))
            if (
                not math.isfinite(start)
                or not math.isfinite(duration)
                or start < 0.0
                or duration <= 0.0
                or start + duration > self.duration_s + 1e-12
            ):
                raise ValueError(f"fault event {index} has an invalid time window")
            if fault in {"packet_dropout", "feedback_dropout"}:
                probability = float(event.get("probability", 0.0))
                if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
                    raise ValueError(f"fault event {index} probability must be in [0, 1]")
            if fault == "command_delay":
                delay = float(event.get("value_s", 0.0))
                if not math.isfinite(delay) or delay < 0.0:
                    raise ValueError(f"fault event {index} delay must be non-negative")
            if fault == "joint_stuck":
                joint_index = int(event.get("joint_index", -1))
                if not 0 <= joint_index < 6:
                    raise ValueError(f"fault event {index} joint_index must be in [0, 5]")
            if fault == "unreachable_target":
                self._finite_vector(
                    event.get("offset_m", [0.0, 0.0, 0.0]),
                    3,
                    f"fault event {index} offset_m",
                )

    @classmethod
    def from_file(cls, path: str | Path) -> "ScenarioPlayer":
        source = Path(path).resolve()
        specification = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(specification, dict):
            raise ValueError("scenario root must be a JSON object")
        return cls(specification, source)

    def sample(self, elapsed_s: float) -> ScenarioSample:
        elapsed = float(np.clip(elapsed_s, 0.0, self.duration_s))
        if self.kind == "keyframes":
            return self._sample_keyframes(elapsed)
        if self.kind == "parametric":
            return self._sample_parametric(elapsed)
        if self.kind == "faults":
            return self._sample_faults(elapsed)
        raise ValueError(f"unsupported scenario type: {self.kind}")

    def _sample_keyframes(self, elapsed: float) -> ScenarioSample:
        keyframes = self.specification.get("keyframes")
        if not isinstance(keyframes, list) or not keyframes:
            raise ValueError("keyframe scenario requires a non-empty keyframes list")

        before = keyframes[0]
        after = keyframes[-1]
        for index, frame in enumerate(keyframes):
            if float(frame["time_s"]) >= elapsed:
                after = frame
                before = keyframes[max(0, index - 1)]
                break

        t0 = float(before["time_s"])
        t1 = float(after["time_s"])
        alpha = 0.0 if t1 <= t0 else (elapsed - t0) / (t1 - t0)
        alpha = float(np.clip(alpha, 0.0, 1.0))

        p0 = np.asarray(before.get("position_m", [0.0, 0.0, 0.0]), dtype=float)
        p1 = np.asarray(after.get("position_m", p0), dtype=float)
        r0 = np.asarray(before.get("rpy_deg", [0.0, 0.0, 0.0]), dtype=float)
        r1 = np.asarray(after.get("rpy_deg", r0), dtype=float)
        rotations = Rotation.from_euler("xyz", np.stack((r0, r1)), degrees=True)
        orientation = Slerp([0.0, 1.0], rotations)([alpha]).as_quat()[0]
        position = p0 + alpha * (p1 - p0)
        grasp0 = float(before.get("grasp", 0.0))
        grasp1 = float(after.get("grasp", grasp0))
        discrete = before if alpha < 1.0 else after
        return ScenarioSample(
            pose=Pose(position, orientation),
            grasp=float(np.clip(grasp0 + alpha * (grasp1 - grasp0), 0.0, 1.0)),
            deadman=bool(discrete.get("deadman", False)),
            clutch=bool(discrete.get("clutch", False)),
        )

    def _sample_parametric(self, elapsed: float) -> ScenarioSample:
        warmup = float(self.specification.get("warmup_s", 0.0))
        active_t = max(0.0, elapsed - warmup)
        shape = str(self.specification.get("shape", "circle"))
        position = np.asarray(
            self.specification.get("center_m", [0.0, 0.0, 0.0]),
            dtype=float,
        ).copy()
        rpy = np.zeros(3, dtype=float)

        if shape == "circle":
            radius = float(self.specification.get("radius_m", 0.05))
            omega = 2.0 * math.pi * float(self.specification.get("frequency_hz", 0.1))
            value = radius * np.array(
                [math.cos(omega * active_t) - 1.0, math.sin(omega * active_t)],
                dtype=float,
            )
            plane = str(self.specification.get("plane", "xy"))
            axes = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}.get(plane)
            if axes is None:
                raise ValueError(f"unsupported circle plane: {plane}")
            position[list(axes)] += value
            amplitude = np.asarray(
                self.specification.get("rpy_amplitude_deg", [0.0, 0.0, 0.0]),
                dtype=float,
            )
            rpy = amplitude * math.sin(omega * active_t)
        elif shape == "tremor":
            intentional_frequency = float(
                self.specification.get("intentional_frequency_hz", 0.5)
            )
            intentional_amplitude = float(
                self.specification.get("intentional_amplitude_m", 0.03)
            )
            tremor_frequency = float(
                self.specification.get("tremor_frequency_hz", 10.0)
            )
            tremor_amplitude = float(
                self.specification.get("tremor_amplitude_m", 0.001)
            )
            axis_name = str(self.specification.get("axis", "x"))
            axis = {"x": 0, "y": 1, "z": 2}.get(axis_name)
            if axis is None:
                raise ValueError(f"unsupported tremor axis: {axis_name}")
            position[axis] += (
                intentional_amplitude
                * math.sin(2.0 * math.pi * intentional_frequency * active_t)
                + tremor_amplitude
                * math.sin(2.0 * math.pi * tremor_frequency * active_t)
            )
        elif shape == "figure_eight":
            radius = float(self.specification.get("radius_m", 0.05))
            omega = 2.0 * math.pi * float(
                self.specification.get("frequency_hz", 0.1)
            )
            value = radius * np.array(
                [math.sin(omega * active_t), 0.5 * math.sin(2.0 * omega * active_t)],
                dtype=float,
            )
            plane = str(self.specification.get("plane", "xy"))
            axes = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}.get(plane)
            if axes is None:
                raise ValueError(f"unsupported figure-eight plane: {plane}")
            position[list(axes)] += value
            amplitude = np.asarray(
                self.specification.get("rpy_amplitude_deg", [0.0, 0.0, 0.0]),
                dtype=float,
            )
            rpy = amplitude * math.sin(omega * active_t)

        return ScenarioSample(
            pose=Pose(position, Rotation.from_euler("xyz", rpy, degrees=True).as_quat()),
            grasp=float(np.clip(self.specification.get("grasp", 0.0), 0.0, 1.0)),
            deadman=bool(self.specification.get("deadman", True)) and elapsed >= warmup,
            clutch=False,
        )

    def _sample_faults(self, elapsed: float) -> ScenarioSample:
        assert self._fault_base_player is not None
        sample = self._fault_base_player.sample(elapsed)
        active: list[dict[str, Any]] = []
        for event in self.specification.get("events", []):
            start = float(event["time_s"])
            end = start + float(event.get("duration_s", 0.0))
            if start <= elapsed < end:
                active.append(event)

        input_dropout = any(event.get("fault") == "input_dropout" for event in active)
        timestamp_out = any(
            event.get("fault") == "timestamp_out_of_order" for event in active
        )
        command_delay = max(
            [float(event.get("value_s", 0.0)) for event in active if event.get("fault") == "command_delay"]
            or [0.0]
        )
        command_dropout = max(
            [float(event.get("probability", 0.0)) for event in active if event.get("fault") == "packet_dropout"]
            or [0.0]
        )
        feedback_dropout = max(
            [
                float(event.get("probability", 0.0))
                for event in active
                if event.get("fault") == "feedback_dropout"
            ]
            or [0.0]
        )
        feedback_frozen = any(
            event.get("fault") == "feedback_freeze" for event in active
        )
        force_ik_failure = any(
            event.get("fault") == "force_ik_failure" for event in active
        )
        unreachable_target = any(
            event.get("fault") == "unreachable_target" for event in active
        )
        fatal_fault = any(event.get("fault") == "fatal_fault" for event in active)
        clear_fault = any(event.get("fault") == "clear_fault" for event in active)
        invalid_input = any(event.get("fault") == "invalid_input" for event in active)
        rearm = any(event.get("fault") == "rearm" for event in active)
        stuck = tuple(
            sorted(
                {
                    int(event["joint_index"])
                    for event in active
                    if event.get("fault") == "joint_stuck"
                }
            )
        )
        position = sample.pose.position.copy()
        for event in active:
            if event.get("fault") == "unreachable_target":
                position += np.asarray(event.get("offset_m", [0.0, 0.0, 0.0]), dtype=float)
        return ScenarioSample(
            pose=Pose(position, sample.pose.orientation),
            grasp=sample.grasp,
            deadman=sample.deadman and not rearm,
            clutch=sample.clutch,
            validity_flags=0 if invalid_input else 1,
            faults=ScenarioFaults(
                input_dropout=input_dropout,
                timestamp_out_of_order=timestamp_out,
                command_delay_s=command_delay,
                command_drop_probability=command_dropout,
                feedback_drop_probability=feedback_dropout,
                feedback_frozen=feedback_frozen,
                stuck_joints=stuck,
                force_ik_failure=force_ik_failure,
                unreachable_target=unreachable_target,
                fatal_fault=fatal_fault,
                clear_fault=clear_fault,
            ),
        )
