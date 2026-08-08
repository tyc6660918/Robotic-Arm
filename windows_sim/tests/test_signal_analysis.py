from __future__ import annotations

import math
import unittest

import numpy as np

from windows_sim.sim.signal_analysis import (
    MultiToneAnalyzer,
    wrapped_phase_difference,
)


class MultiToneAnalyzerTests(unittest.TestCase):
    def test_recovers_two_tones_and_relative_phase(self) -> None:
        analyzer = MultiToneAnalyzer((0.5, 10.0), ("raw", "filtered"))
        for timestamp in np.arange(0.0, 20.0, 0.01):
            raw = 0.2 + 0.03 * math.sin(2.0 * math.pi * 0.5 * timestamp)
            raw += 0.001 * math.sin(2.0 * math.pi * 10.0 * timestamp + 0.2)
            filtered = 0.1 + 0.029 * math.sin(
                2.0 * math.pi * 0.5 * timestamp - 0.1
            )
            filtered += 0.0001 * math.sin(
                2.0 * math.pi * 10.0 * timestamp - 0.5
            )
            analyzer.update(timestamp, {"raw": raw, "filtered": filtered})

        estimates = analyzer.estimates()
        self.assertIsNotNone(estimates)
        assert estimates is not None
        self.assertAlmostEqual(
            estimates["raw"]["tones"]["0.5"]["amplitude"],
            0.03,
            places=10,
        )
        self.assertAlmostEqual(
            estimates["raw"]["tones"]["10"]["amplitude"],
            0.001,
            places=10,
        )
        phase = wrapped_phase_difference(
            estimates["filtered"]["tones"]["10"]["phase_rad"],
            estimates["raw"]["tones"]["10"]["phase_rad"],
        )
        self.assertAlmostEqual(phase, -0.7, places=10)

    def test_rejects_incomplete_signal_samples(self) -> None:
        analyzer = MultiToneAnalyzer((1.0,), ("a", "b"))
        with self.assertRaises(ValueError):
            analyzer.update(0.0, {"a": 1.0})


if __name__ == "__main__":
    unittest.main()
