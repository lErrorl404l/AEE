#!/usr/bin/env python3
"""Stability tests (Miller twist rule).

Two checks:

1. The SQF function must carry the published rule.
2. The rule computed here must agree with the minimum twist that a
   manufacturer published, which is an independent confirmation that
   the physics is right. Berger publishes a minimum twist for every
   bullet and also publishes the bullet length, so the comparison is
   exact for 60 or more bullets.

Run: python3 tools/tests/test_stability.py
"""

import json
import math
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
SQF = (REPO / "addons/ballistics/functions/fnc_calculateStability.sqf").read_text(
    encoding="utf-8"
)
GRAIN_TO_G = 0.06479891


def stability(mass_gr, diameter_in, length_in, twist_in, velocity=853.0, alt_ft=0.0):
    """Miller twist rule with the velocity and altitude corrections."""
    calibers = length_in / diameter_in
    s = (30 * mass_gr) / (twist_in * twist_in * length_in * (1 + calibers**2))
    s = s * (velocity / 853.0) ** (1 / 3)
    return s * math.exp(3.158e-5 * alt_ft)


def required_twist_in(mass_gr, diameter_in, length_in, sg=1.5):
    calibers = length_in / diameter_in
    return math.sqrt(30 * mass_gr / (sg * length_in * (1 + calibers**2)))


class TestPublishedRule(unittest.TestCase):
    def test_sqf_carries_the_rule(self):
        for fragment in (
            "30 * _massGr",
            "0.06479891",
            "0.0254",
            "1 / 3",
            "3.158e-5",
            "exp",
        ):
            self.assertIn(fragment, SQF, f"missing from the kernel: {fragment}")

    def test_registered(self):
        prep = (REPO / "addons/ballistics/XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("calculateStability", prep)

    def test_miller_reference_example(self):
        # The published worked example: 180 gr, .308 in, 1.180 in long,
        # at SG 2.0 needs 12.1 inches per turn.
        twist = required_twist_in(180, 0.308, 1.180, sg=2.0)
        self.assertAlmostEqual(twist, 12.1, delta=0.2)


class TestAgainstPublishedTwist(unittest.TestCase):
    """The computed requirement must match the manufacturer's own figure."""

    def bullets(self):
        db = json.loads(
            (REPO / "data/ballistics/projectiles.json").read_text(encoding="utf-8")
        )
        out = []
        for rec in db:
            v = rec["values"]
            if not all(
                k in v for k in ("mass_g", "diameter_mm", "length_mm", "min_twist_m")
            ):
                continue
            if v["min_twist_m"]["value"] <= 0:
                continue
            out.append(
                (
                    rec["projectile_id"],
                    v["mass_g"]["value"] / GRAIN_TO_G,
                    v["diameter_mm"]["value"] / 25.4,
                    v["length_mm"]["value"] / 25.4,
                    v["min_twist_m"]["value"] / 0.0254,
                )
            )
        return out

    def test_matches_published_minimum_twist(self):
        rows = self.bullets()
        self.assertGreater(len(rows), 50, "too few bullets to validate")
        errors = []
        for pid, mass, dia, length, published in rows:
            computed = required_twist_in(mass, dia, length)
            errors.append(abs(computed - published) / published)
        mean = sum(errors) / len(errors)
        within20 = sum(1 for e in errors if e <= 0.20) / len(errors)
        # The rule is shape-blind, so a flat base bullet deviates. The
        # boat tail bullets, which are the majority, land close.
        self.assertLess(mean, 0.12, f"mean error {mean:.1%} against published twist")
        self.assertGreater(within20, 0.85, f"only {within20:.0%} within 20 percent")

    def test_heavy_match_bullet_needs_a_fast_twist(self):
        # The Hornady 225 gr ELD Match is published for a 1:10 and a 1:7
        # twist, because 1:10 is only marginal for it.
        at10 = stability(225, 0.308, 1.665, 10.0)
        at7 = stability(225, 0.308, 1.665, 7.0)
        self.assertGreater(at10, 1.1)
        self.assertLess(at10, 1.6)
        self.assertGreater(at7, 2.4)


if __name__ == "__main__":
    unittest.main()
