"""Fixed-memory harmonic response estimation for scripted validation."""

from __future__ import annotations

import math
from typing import Mapping

import numpy as np


class MultiToneAnalyzer:
    """Fit DC plus configured sine/cosine tones with streaming normal equations."""

    def __init__(self, frequencies_hz: tuple[float, ...], signals: tuple[str, ...]) -> None:
        if not frequencies_hz or not signals:
            raise ValueError("frequencies_hz and signals must be non-empty")
        frequencies = np.asarray(frequencies_hz, dtype=float)
        if np.any(~np.isfinite(frequencies)) or np.any(frequencies <= 0.0):
            raise ValueError("frequencies_hz must be finite and positive")
        if len(set(signals)) != len(signals) or any(not name for name in signals):
            raise ValueError("signal names must be unique and non-empty")
        self.frequencies_hz = tuple(float(value) for value in frequencies)
        self.signals = tuple(signals)
        feature_count = 1 + 2 * len(self.frequencies_hz)
        self._normal = np.zeros((feature_count, feature_count), dtype=float)
        self._projections = {
            name: np.zeros(feature_count, dtype=float) for name in self.signals
        }
        self.sample_count = 0

    def update(self, timestamp_s: float, values: Mapping[str, float]) -> None:
        timestamp = float(timestamp_s)
        if not math.isfinite(timestamp):
            raise ValueError("timestamp_s must be finite")
        if set(values) != set(self.signals):
            raise ValueError("values must contain exactly the configured signals")
        feature = [1.0]
        for frequency in self.frequencies_hz:
            phase = 2.0 * math.pi * frequency * timestamp
            feature.extend((math.sin(phase), math.cos(phase)))
        design = np.asarray(feature, dtype=float)
        self._normal += np.outer(design, design)
        for name in self.signals:
            value = float(values[name])
            if not math.isfinite(value):
                raise ValueError("signal samples must be finite")
            self._projections[name] += design * value
        self.sample_count += 1

    def estimates(self) -> dict[str, dict[str, object]] | None:
        if self.sample_count < self._normal.shape[0]:
            return None
        result: dict[str, dict[str, object]] = {}
        for name, projection in self._projections.items():
            coefficients = np.linalg.lstsq(
                self._normal,
                projection,
                rcond=None,
            )[0]
            tones: dict[str, dict[str, float]] = {}
            for index, frequency in enumerate(self.frequencies_hz):
                sine = float(coefficients[1 + 2 * index])
                cosine = float(coefficients[2 + 2 * index])
                tones[f"{frequency:g}"] = {
                    "amplitude": math.hypot(sine, cosine),
                    "phase_rad": math.atan2(cosine, sine),
                }
            result[name] = {
                "dc": float(coefficients[0]),
                "tones": tones,
            }
        return result


def wrapped_phase_difference(response: float, reference: float) -> float:
    return math.atan2(
        math.sin(response - reference),
        math.cos(response - reference),
    )
