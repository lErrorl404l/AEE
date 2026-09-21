#!/usr/bin/env python3
"""Collision-damage response tests (issue #172).

Locks the collision-damage physics in fnc_handleCollisionDamage.sqf:
the impact-energy scaling (0.5*m*v^2 -> damage multiplier), the
collision gate (projectile impacts pass through untouched - the
no-double-count guard), and the hitpoint/component response.

The scaling is a Python mirror of the SQF linearConversion - verified
against the SOURCE text so the mirror cannot drift (the #204 lesson).
"""

import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
FNC = (REPO / "addons/core/functions/fnc_handleCollisionDamage.sqf").read_text(
    encoding="utf-8"
)


def energy_scale(energy_joules: float) -> float:
    """Mirror of the SQF: linearConversion [20000, 5e6, E, 0.1, 1.5, true]."""
    lo, hi, lo_v, hi_v = 20000.0, 5_000_000.0, 0.1, 1.5
    e = max(lo, min(hi, energy_joules))
    return lo_v + (e - lo) / (hi - lo) * (hi_v - lo_v)


class TestImpactPhysics(unittest.TestCase):
    def test_light_tap_low_damage(self):
        # 12 t vehicle pair bumping at 5 km/h: E = 0.5*24000*1.39^2 ~ 23 kJ
        m = 12000 + 12000
        v = 5 / 3.6
        e = 0.5 * m * v * v
        s = energy_scale(e)
        self.assertAlmostEqual(e, 23148, delta=1000)
        self.assertLess(s, 0.15)  # ~0.1 - a scuff, not an explosion

    def test_crash_major_damage(self):
        # Same pair at 80 km/h: E ~ 5.9 MJ
        m = 24000
        v = 80 / 3.6
        e = 0.5 * m * v * v
        s = energy_scale(e)
        self.assertGreater(e, 5e6)
        self.assertAlmostEqual(s, 1.5, delta=0.1)  # clamped at the top

    def test_mid_speed_scales(self):
        # 40 km/h: E ~ 1.5 MJ -> ~0.75
        e = 0.5 * 24000 * (40 / 3.6) ** 2
        s = energy_scale(e)
        self.assertGreater(s, 0.5)
        self.assertLess(s, 1.0)

    def test_collision_gate_present(self):
        # Projectile impacts must pass through untouched (no double-count
        # with the ballistic model).
        self.assertIn('if (_projectile isEqualType "") exitWith { _damage };', FNC)
        self.assertIn("isKindOf", FNC)

    def test_energy_formula_in_source(self):
        self.assertIn("0.5 * _mass * _speed * _speed", FNC)
        self.assertIn("linearConversion [20000, 5000000", FNC)

    def test_component_response(self):
        # The hitpoint selects what takes the damage.
        self.assertIn("_hitPoint", FNC)
        self.assertIn('["Hull", _selection] select', FNC)

    def test_clamped_return(self):
        # Damage is clamped to 1.0 (a real crash CAN destroy, only the
        # light-tap explosion is the bug).
        self.assertIn("min 1.0", FNC)


if __name__ == "__main__":
    unittest.main()
