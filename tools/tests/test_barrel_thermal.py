#!/usr/bin/env python3
"""Barrel thermal state tests (issue #130).

Mirror of fnc_calculateBarrelState.sqf: per-weapon barrel temperature
(heat per round by firearm class, exponential cooling to ambient), the
elevation-only POI shift from thermal-gradient muzzle curvature, and the
cold-bore first-shot bias that decays by round 5.

Run: python3 -m unittest tools.tests.test_barrel_thermal
"""

import math
import unittest


def barrel_step(
    temp_c,
    rounds,
    ambient_c,
    is_mg,
    shot=False,
    dt_s=0.0,
    heat_per_round=None,
    tau=None,
):
    """Mirror of the SQF barrel state step.

    is_mg: machine-gun class (higher heat per round, slower cooling,
    larger POI coefficient).
    shot: True adds heat and increments the round count.
    dt_s: cooling duration in seconds (0 for a pure shot tick).
    """
    if heat_per_round is None:
        heat_per_round = 3.0 if is_mg else 1.0
    if tau is None:
        tau = 250 if is_mg else 150

    if shot:
        temp_c += heat_per_round
        rounds += 1
    if dt_s > 0:
        temp_c = ambient_c + (temp_c - ambient_c) * math.exp(-dt_s / tau)
    return temp_c, rounds


def poi_shift(temp_c, ambient_c, is_mg, rounds, cold_bore_threshold=15.0):
    """Mirror of the SQF POI shift (elevation only, mrad, positive = up).

    Cold-bore bias applies to shots 1-5 of a cold barrel; an unfired
    barrel (rounds == 0) has no first-shot bias.
    """
    k = 0.02 if is_mg else 0.008
    poi = k * (temp_c - ambient_c)
    if temp_c - ambient_c < cold_bore_threshold and rounds >= 1 and rounds <= 5:
        poi += max(0.25 * (1 - (rounds - 1) / 4), 0.0)
    return poi


class TestBarrelTemperature(unittest.TestCase):
    def test_shot_adds_heat(self):
        t, r = barrel_step(21.0, 0, 21.0, is_mg=False, shot=True)
        self.assertAlmostEqual(t, 22.0, places=6)  # +1 C/round rifle
        self.assertEqual(r, 1)

    def test_mg_heats_faster(self):
        t_mg, _ = barrel_step(21.0, 0, 21.0, is_mg=True, shot=True)
        t_rf, _ = barrel_step(21.0, 0, 21.0, is_mg=False, shot=True)
        self.assertGreater(t_mg, t_rf)  # +3 vs +1 C/round

    def test_mag_of_rifle_warms_barrel(self):
        # 30 rounds of 5.56: +30 C over ambient.
        t, r = 21.0, 0
        for _ in range(30):
            t, r = barrel_step(t, r, 21.0, is_mg=False, shot=True)
        self.assertAlmostEqual(t, 51.0, places=4)
        self.assertEqual(r, 30)

    def test_sqf_honors_rounds_fired_batch(self):
        # The SQF accepts an optional _roundsFired count so a caller (or
        # the docker test) can seed a burst in one call.  The mirror stays
        # per-shot; this drift-lock pins that the SQF multiplies the heat
        # by the batch count and accumulates the round count, so the two
        # never diverge silently.
        from pathlib import Path

        text = Path(
            "addons/ballistics/functions/fnc_calculateBarrelState.sqf"
        ).read_text(encoding="utf-8")
        self.assertIn("_roundsFired max 1", text)
        self.assertIn("_tempC + (_heatPerRound * _n)", text)
        self.assertIn("_rounds = _rounds + _n", text)

    def test_cooling_exponential(self):
        # 100 C barrel in 21 C ambient, one tau (150 s rifle): gap 63% closed.
        t_cool = barrel_step(100.0, 0, 21.0, is_mg=False, dt_s=150.0)[0]
        gap = t_cool - 21.0  # remaining elevation above ambient
        self.assertAlmostEqual(gap / (100 - 21), math.exp(-1.0), places=3)

    def test_mg_cools_slower(self):
        t_mg = barrel_step(100.0, 0, 21.0, is_mg=True, dt_s=150.0)[0]
        t_rf = barrel_step(100.0, 0, 21.0, is_mg=False, dt_s=150.0)[0]
        # MG tau 250 keeps more heat after the same 150 s.
        self.assertGreater(t_mg, t_rf)

    def test_reaches_ambient(self):
        t, _ = 100.0, 0
        for _ in range(200):  # 200 x 60 s = 3.3 h
            t, _ = barrel_step(t, 0, 21.0, is_mg=False, dt_s=60.0)
        self.assertAlmostEqual(t, 21.0, delta=0.01)


class TestPOIShift(unittest.TestCase):
    def test_cold_barrel_no_shift(self):
        self.assertAlmostEqual(poi_shift(21.0, 21.0, False, 10), 0.0, places=6)

    def test_hot_barrel_rises(self):
        # Rifle at +100 C: 0.008 * 100 = 0.8 mrad (spec rule of thumb
        # 0.5-1 mrad at +100 C).
        self.assertAlmostEqual(poi_shift(121.0, 21.0, False, 30), 0.8, places=4)

    def test_mg_shift_larger(self):
        # MG at +300 C: 0.02 * 300 = 6 mrad (spec 3-9 mrad).
        self.assertAlmostEqual(poi_shift(321.0, 21.0, True, 60), 6.0, places=3)

    def test_vertical_only_elevation(self):
        # The shift is elevation-only; the mirror has no lateral term.
        self.assertEqual(poi_shift(121.0, 21.0, False, 30), 0.8)

    def test_cold_bore_first_shot_high(self):
        # First shot from a cold barrel: +0.25 mrad (0.9 MOA) high.
        shift = poi_shift(21.0, 21.0, False, 1)
        self.assertAlmostEqual(shift, 0.25, places=6)

    def test_cold_bore_decays_by_round_5(self):
        # Rounds 2-5 scale the bias down; round 5 reaches zero.
        s1 = poi_shift(21.0, 21.0, False, 1)
        s2 = poi_shift(21.0, 21.0, False, 2)
        s5 = poi_shift(21.0, 21.0, False, 5)
        s6 = poi_shift(21.0, 21.0, False, 6)
        self.assertGreater(s1, s2)
        self.assertAlmostEqual(s5, 0.0, places=6)
        self.assertEqual(s6, 0.0)

    def test_cold_bore_does_not_apply_to_hot_barrel(self):
        # A hot barrel (>15 C above ambient) has no cold-bore bias.
        shift = poi_shift(41.0, 21.0, False, 1)
        self.assertEqual(shift, 0.008 * 20)  # expansion only, no bias


if __name__ == "__main__":
    unittest.main()
