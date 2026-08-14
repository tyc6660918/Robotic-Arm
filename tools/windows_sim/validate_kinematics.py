#!/usr/bin/env python3
"""Deterministic offline FK -> IK -> FK acceptance validation."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import time

import numpy as np
import scipy

if __package__:
    from .sim import BoundedIKSolver, create_dummy_kinematics, rotation_error_vector
else:
    from sim import BoundedIKSolver, create_dummy_kinematics, rotation_error_vector


ROOT = Path(__file__).resolve().parent


def run_validation(
    sample_count: int = 1000,
    seed: int = 20260808,
    singular_value_threshold: float = 1e-4,
) -> dict[str, object]:
    if sample_count <= 0:
        raise ValueError("sample_count must be positive")
    if singular_value_threshold <= 0.0:
        raise ValueError("singular_value_threshold must be positive")

    kinematics = create_dummy_kinematics()
    random = np.random.default_rng(seed)
    margin = 0.02 * kinematics.joint_range
    lower = kinematics.lower_limits + margin
    upper = kinematics.upper_limits - margin

    successes = 0
    generated = 0
    skipped_singular = 0
    position_errors: list[float] = []
    orientation_errors: list[float] = []
    solve_times: list[float] = []
    failure_examples: list[dict[str, object]] = []
    started = time.perf_counter()

    while generated < sample_count:
        expected_joints = random.uniform(lower, upper)
        target, jacobian = kinematics.forward_with_geometric_jacobian(
            expected_joints
        )
        minimum_singular_value = float(
            np.min(np.linalg.svd(jacobian, compute_uv=False))
        )
        if minimum_singular_value < singular_value_threshold:
            skipped_singular += 1
            continue

        generated += 1
        solver = BoundedIKSolver(kinematics)
        result = solver.solve(target)
        solve_times.append(result.solve_time_s)
        if result.success:
            actual = kinematics.forward(result.joints)
            position_error = float(
                np.linalg.norm(actual[:3, 3] - target[:3, 3])
            )
            orientation_error = float(
                np.linalg.norm(rotation_error_vector(target, actual))
            )
            position_errors.append(position_error)
            orientation_errors.append(orientation_error)
            successes += 1
        elif len(failure_examples) < 10:
            failure_examples.append(
                {
                    "sample": generated,
                    "target_joints_rad": expected_joints.tolist(),
                    "best_position_error_m": result.position_error,
                    "best_orientation_error_rad": result.orientation_error,
                    "message": result.message,
                }
            )

    success_rate = successes / sample_count
    total_time = time.perf_counter() - started
    maximum_position_error = max(position_errors, default=None)
    maximum_orientation_error = max(orientation_errors, default=None)
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "metadata": {
            "offline_only": True,
            "serial_access": False,
            "sample_count": sample_count,
            "seed": seed,
            "singular_value_threshold": singular_value_threshold,
            "python_stack": {
                "numpy": np.__version__,
                "scipy": scipy.__version__,
            },
        },
        "metrics": {
            "generated_samples": generated,
            "skipped_singular_samples": skipped_singular,
            "successful_samples": successes,
            "success_rate": success_rate,
            "maximum_position_error_m": maximum_position_error,
            "maximum_orientation_error_rad": maximum_orientation_error,
            "solve_time_p50_s": float(np.percentile(solve_times, 50.0)),
            "solve_time_p99_s": float(np.percentile(solve_times, 99.0)),
            "total_time_s": total_time,
            "acceptance": {
                "success_rate_at_least_99_percent": bool(success_rate >= 0.99),
                "position_error_under_0_1_mm": bool(
                    maximum_position_error is not None
                    and maximum_position_error < 1e-4
                ),
                "orientation_error_under_0_05_deg": bool(
                    maximum_orientation_error is not None
                    and maximum_orientation_error < np.deg2rad(0.05)
                ),
            },
        },
        "failure_examples": failure_examples,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline Dummy FK/IK acceptance validation"
    )
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260808)
    parser.add_argument("--singular-value-threshold", type=float, default=1e-4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = run_validation(
        args.samples,
        args.seed,
        args.singular_value_threshold,
    )
    output = args.output
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output = ROOT / "runs" / f"kinematics_validation_{timestamp}.json"
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    metrics = report["metrics"]
    print(f"Validation report: {output}")
    print(
        "Success: "
        f"{metrics['successful_samples']}/{metrics['generated_samples']} "
        f"({100.0 * metrics['success_rate']:.2f}%)"
    )
    return 0 if all(metrics["acceptance"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
