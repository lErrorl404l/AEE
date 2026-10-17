#!/usr/bin/env python3
"""The shared event RNG is exact in float32 and statistically sound.

Executes addons/lib/functions/fnc_deterministicRandom.sqf and checks it
against an exact-integer transcription evaluated in float32: the engine's
numbers are 32-bit floats, so every intermediate must stay below 2^24.

Run: python3 -m unittest tools.tests.test_deterministic_random
"""

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.tests.sqf_lite import run_sqf  # noqa: E402

SRC = REPO / "addons/lib/functions/fnc_deterministicRandom.sqf"


def exact(a: float, b: float) -> float:
    a = int(abs(a)) % 1048576
    b = int(abs(b)) % 1048576
    s1 = 1 + ((a + (b % 4096) * 4096) % 32362)
    s2 = 1 + (((a % 4096) * 4096 + b) % 31726)
    s3 = 1 + ((a // 4096 + (b // 4096) * 256 + (a % 7919)) % 31656)
    peak = 0
    for _ in range(6):
        s1, s2, s3 = 157 * s1 % 32363, 146 * s2 % 31727, 142 * s3 % 31657
        peak = max(peak, 157 * 32363, s1 + s3)
        s1 = 1 + ((s1 + s3) % 32362)
        s2 = 1 + ((s2 + s1) % 31726)
        s3 = 1 + ((s3 + s2) % 31656)
    assert peak < 2 ** 24
    z = (s1 - s2 + s3) % 32362
    if z < 1:
        z += 32362
    return z / 32363


class TestDeterministicRandom(unittest.TestCase):
    def test_sqf_matches_the_exact_generator(self):
        for a in (0, 1, 2, 999, 123456, 2 ** 20 + 5, 9_876_543):
            for b in (401, 402, 7):
                self.assertAlmostEqual(run_sqf(SRC, [a, b]), exact(a, b), places=9)

    def test_uniform_and_uncorrelated(self):
        xs = [exact(a, 401) for a in range(50000)]
        bins = [0] * 10
        for x in xs:
            bins[min(9, int(x * 10))] += 1
        self.assertLess(max(bins) - min(bins), 600)
        mean = sum(xs) / len(xs)
        num = sum((xs[i] - mean) * (xs[i + 1] - mean) for i in range(len(xs) - 1))
        den = sum((x - mean) ** 2 for x in xs)
        self.assertLess(abs(num / den), 0.02)


if __name__ == "__main__":
    unittest.main()
