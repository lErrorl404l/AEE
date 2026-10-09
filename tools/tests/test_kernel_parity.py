#!/usr/bin/env python3
"""The native kernel parity harness (Phase E).

Two facts are generated from the SQF reference and must stay fresh:

- the coefficient table the Rust kernels compile (`gen_kernel_coefficients.py`);
- the parity vectors the Rust `#[test]` reads (`gen_kernel_vectors.py`).

This suite also holds the per-kernel tolerance to the ADR-034 rule: no relative
bound looser than ``1e-6``, and an absolute bound no larger than one rounding
step (``0.5``) for a kernel whose output is rounded to an integer.

Run: python3 -m unittest tools.tests.test_kernel_parity
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VECTORS = (
    ROOT / "tools" / "dev-harness" / "extension" / "tests" / "vectors" / "kernels.json"
)


def _check(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / script), "--check"],
        capture_output=True,
        text=True,
    )


class TestKernelParity(unittest.TestCase):
    def test_coefficients_are_fresh(self):
        result = _check("gen_kernel_coefficients.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_vectors_are_fresh(self):
        result = _check("gen_kernel_vectors.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_the_vectors_cover_every_native_kernel(self):
        suite = json.loads(VECTORS.read_text(encoding="utf-8"))["kernels"]
        self.assertEqual(
            set(suite),
            {"stationPressure", "relativeHumidity", "airDensity"},
            "the vector file must cover each native kernel",
        )
        for name, kernel in suite.items():
            self.assertTrue(kernel["vectors"], f"{name} has no vectors")

    def test_every_relative_bound_is_no_looser_than_1e_6(self):
        suite = json.loads(VECTORS.read_text(encoding="utf-8"))["kernels"]
        for name, kernel in suite.items():
            self.assertLessEqual(
                kernel["tolerance_rel"], 1e-6, f"{name}: relative bound is too loose"
            )

    def test_absolute_bounds_stay_within_one_rounding_step(self):
        suite = json.loads(VECTORS.read_text(encoding="utf-8"))["kernels"]
        for name, kernel in suite.items():
            self.assertLessEqual(
                kernel["tolerance_abs"], 0.5, f"{name}: absolute bound is too loose"
            )


if __name__ == "__main__":
    sys.exit(unittest.main())
