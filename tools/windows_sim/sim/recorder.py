"""Streaming CSV recorder and compact JSON metrics for offline simulation."""

from __future__ import annotations

import csv
import json
import math
import random
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import numpy as np


def _flatten(prefix: str, value: Any, output: dict[str, Any]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            _flatten(child_prefix, child, output)
        return

    if hasattr(value, "position") and hasattr(value, "orientation_xyzw"):
        _flatten(f"{prefix}.position", getattr(value, "position"), output)
        _flatten(
            f"{prefix}.orientation_xyzw",
            getattr(value, "orientation_xyzw"),
            output,
        )
        return

    if isinstance(value, (list, tuple, np.ndarray)):
        array = np.asarray(value).reshape(-1)
        for index, item in enumerate(array):
            output[f"{prefix}[{index}]"] = _scalar(item)
        return

    output[prefix] = _scalar(value)


def _scalar(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if hasattr(value, "value") and isinstance(value.value, (str, int, float)):
        return value.value
    return value


class SimulationRecorder:
    """Write samples incrementally so long soak tests do not grow memory."""

    def __init__(
        self,
        output_root: Path,
        csv_name: str = "teleop_samples.csv",
        report_name: str = "report.json",
        run_name: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        percentile_reservoir_size: int = 100_000,
    ) -> None:
        if percentile_reservoir_size <= 0:
            raise ValueError("percentile_reservoir_size must be positive")
        output_root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        if run_name is not None:
            self.run_directory = output_root / run_name
            self.run_directory.mkdir(exist_ok=False)
        else:
            suffix = 0
            while True:
                name = timestamp if suffix == 0 else f"{timestamp}_{suffix}"
                self.run_directory = output_root / name
                try:
                    self.run_directory.mkdir(exist_ok=False)
                    break
                except FileExistsError:
                    suffix += 1
        self.csv_path = self.run_directory / csv_name
        self.report_path = self.run_directory / report_name
        self.metadata = dict(metadata or {})

        self._file = self.csv_path.open("w", newline="", encoding="utf-8")
        self._writer: csv.DictWriter[str] | None = None
        self._fieldnames: list[str] = []
        self._lock = threading.Lock()
        self._samples_written = 0
        self._position_error_sq_sum = 0.0
        self._orientation_error_sq_sum = 0.0
        self._position_error_max = 0.0
        self._orientation_error_max = 0.0
        self._error_count = 0
        self._cycle_periods: list[float] = []
        self._cycle_period_count = 0
        self._percentile_reservoir_size = int(percentile_reservoir_size)
        self._reservoir_random = random.Random(0x51A7)
        self._ik_successes = 0
        self._ik_attempts = 0
        self._states: Counter[str] = Counter()
        self._fault_reasons: Counter[str] = Counter()
        self._finalized_report: Path | None = None

    def record(self, sample: Mapping[str, Any]) -> None:
        flat: dict[str, Any] = {}
        _flatten("", sample, flat)

        with self._lock:
            if self._writer is None:
                self._fieldnames = list(flat.keys())
                self._writer = csv.DictWriter(
                    self._file,
                    fieldnames=self._fieldnames,
                    extrasaction="ignore",
                )
                self._writer.writeheader()
            else:
                unexpected = set(flat).difference(self._fieldnames)
                if unexpected:
                    names = ", ".join(sorted(unexpected))
                    raise ValueError(f"sample introduced fields after CSV header: {names}")

            row = {field: flat.get(field, "") for field in self._fieldnames}
            self._writer.writerow(row)
            self._samples_written += 1
            if self._samples_written % 100 == 0:
                self._file.flush()
            self._update_metrics(sample)

    def _update_metrics(self, sample: Mapping[str, Any]) -> None:
        position_error = sample.get("position_error_m")
        orientation_error = sample.get("orientation_error_rad")
        if position_error is not None and orientation_error is not None:
            p = float(position_error)
            r = float(orientation_error)
            if math.isfinite(p) and math.isfinite(r):
                self._position_error_sq_sum += p * p
                self._orientation_error_sq_sum += r * r
                self._position_error_max = max(self._position_error_max, p)
                self._orientation_error_max = max(self._orientation_error_max, r)
                self._error_count += 1

        cycle_period = sample.get("cycle_period_s")
        if cycle_period is not None:
            value = float(cycle_period)
            if math.isfinite(value) and value >= 0.0:
                self._cycle_period_count += 1
                if len(self._cycle_periods) < self._percentile_reservoir_size:
                    self._cycle_periods.append(value)
                else:
                    index = self._reservoir_random.randrange(self._cycle_period_count)
                    if index < self._percentile_reservoir_size:
                        self._cycle_periods[index] = value

        ik_success = sample.get("ik_success")
        if ik_success is not None:
            self._ik_attempts += 1
            self._ik_successes += int(bool(ik_success))

        state = sample.get("state")
        if state is not None:
            self._states[str(_scalar(state))] += 1
        fault_reason = sample.get("fault_reason")
        if fault_reason:
            self._fault_reasons[str(fault_reason)] += 1

    def finalize(self, extra_metrics: Mapping[str, Any] | None = None) -> Path:
        with self._lock:
            if self._finalized_report is not None:
                return self._finalized_report
            if not self._file.closed:
                self._file.flush()
                self._file.close()

            metrics: dict[str, Any] = {
                "samples_written": self._samples_written,
                "position_error_rms_m": self._rms(
                    self._position_error_sq_sum, self._error_count
                ),
                "orientation_error_rms_rad": self._rms(
                    self._orientation_error_sq_sum, self._error_count
                ),
                "position_error_max_m": self._position_error_max,
                "orientation_error_max_rad": self._orientation_error_max,
                "ik_success_rate": (
                    self._ik_successes / self._ik_attempts
                    if self._ik_attempts
                    else None
                ),
                "ik_attempts": self._ik_attempts,
                "cycle_period_p50_s": self._percentile(50.0),
                "cycle_period_p99_s": self._percentile(99.0),
                "cycle_period_samples_seen": self._cycle_period_count,
                "cycle_period_reservoir_size": len(self._cycle_periods),
                "state_sample_counts": dict(self._states),
                "fault_reason_sample_counts": dict(self._fault_reasons),
            }
            if extra_metrics:
                metrics.update(dict(extra_metrics))
            p99 = metrics.get("cycle_period_p99_s")
            ik_rate = metrics.get("ik_success_rate")
            limit_violations = metrics.get("joint_limit_violation_count")
            timing_evaluated = bool(self.metadata.get("realtime", False))
            metrics["acceptance"] = {
                "control_cycle_p99_under_20ms": (
                    p99 is not None and float(p99) < 0.02
                    if timing_evaluated
                    else None
                ),
                "control_cycle_timing_evaluated": timing_evaluated,
                "ik_success_rate_at_least_99_percent": (
                    ik_rate is not None and float(ik_rate) >= 0.99
                ),
                "joint_limits_respected": (
                    limit_violations is not None and int(limit_violations) == 0
                ),
                "scenario_finished": bool(metrics.get("scenario_finished", False)),
            }

            report = {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "metadata": self.metadata,
                "metrics": metrics,
                "csv": self.csv_path.name,
            }
            self.report_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=True),
                encoding="utf-8",
            )
            self._finalized_report = self.report_path
            return self.report_path

    @staticmethod
    def _rms(square_sum: float, count: int) -> float | None:
        return math.sqrt(square_sum / count) if count else None

    def _percentile(self, percentile: float) -> float | None:
        if not self._cycle_periods:
            return None
        return float(np.percentile(np.asarray(self._cycle_periods), percentile))

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()

    def __enter__(self) -> "SimulationRecorder":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
