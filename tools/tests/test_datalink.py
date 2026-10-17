#!/usr/bin/env python3
"""Tracker datalink: ITU-R P.526-15 Bullington diffraction, the link budget
and the ATAK dynamic reporting rate.

Runs the REAL kernels through sqf_lite (float32) against an independent
Python port of the published equations:

  fnc_bullingtonLoss          ITU-R P.526-15 s.4.5.1, eqs. 31, 49-57
  fnc_datalinkState           Pr = Pt + G - (FSPL + Ldiff + Lexcess), P.525 FSPL
  fnc_trackerReportInterval   ATAK-CIV ReportingRate.checkIfTimeToReport

Run: python3 -m unittest tools.tests.test_datalink -v
"""

from __future__ import annotations

import math
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

GEO = ROOT / "addons/lib/functions/geo"
BULL = GEO / "fnc_bullingtonLoss.sqf"
LINK = GEO / "fnc_datalinkState.sqf"
RATE = ROOT / "addons/hud/functions/hud/fnc_trackerReportInterval.sqf"


def J(nu: float) -> float:
    """P.526-15 eq. 31."""
    if nu <= -0.78:
        return 0.0
    return 6.9 + 20 * math.log10(math.sqrt((nu - 0.1) ** 2 + 1) + nu - 0.1)


def bullington(d, dist, hgt, hts, hrs, f_mhz):
    """P.526-15 s.4.5.1, a direct transcription."""
    ce = 1 / 8500
    lam = 299.792458 / f_mhz
    pts = [(di, hi + 500 * ce * di * (d - di)) for di, hi in zip(dist, hgt) if 0 < di < d]
    if not pts:
        return 0.0
    stim = max((h - hts) / di for di, h in pts)                       # (49)
    str_ = (hrs - hts) / d                                            # (50)
    if stim < str_:
        numax = max((h - (hts * (d - di) + hrs * di) / d)
                    * math.sqrt(0.002 * d / (lam * di * (d - di))) for di, h in pts)  # (51)
        luc = J(numax)                                                # (52)
    else:
        srim = max((h - hrs) / (d - di) for di, h in pts)            # (53)
        db = (hrs - hts + srim * d) / max(stim + srim, 1e-9)          # (54)
        db = min(max(db, 1e-4), d - 1e-4)
        nub = (hts + stim * db - (hts * (d - db) + hrs * db) / d) \
            * math.sqrt(0.002 * d / (lam * db * (d - db)))            # (55)
        luc = J(nub)                                                  # (56)
    return luc + (1 - math.exp(-luc / 6)) * (10 + 0.02 * d)          # (57)


G = {"__FUNC__bullingtonLoss": lambda *a: run_sqf(BULL, list(a), {})}


def sqf_bull(*a):
    return run_sqf(BULL, list(a), {}, float32=True)


class TestBullington(unittest.TestCase):
    def test_grazing_knife_edge(self):
        # A single edge exactly on the line of sight: nu = 0, J(0) ~ 6.0 dB,
        # the textbook grazing-incidence loss.
        d = 10.0
        bulge = 500 / 8500 * 5 * 5
        got = sqf_bull(d, [5.0], [100 - bulge - 1e-3], 100, 100, 100)
        luc = J(0.0)
        self.assertAlmostEqual(luc, 6.03, delta=0.01)
        self.assertAlmostEqual(got, luc + (1 - math.exp(-luc / 6)) * (10 + 0.2), delta=0.02)

    def test_clear_path_has_no_loss(self):
        # 2 km over flat ground, antennas 30 m up: nu far below -0.78.
        self.assertEqual(sqf_bull(2.0, [0.5, 1.0, 1.5], [0, 0, 0], 30, 30, 100), 0)

    def test_random_profiles_match_the_reference(self):
        rnd = random.Random(3)
        for _ in range(40):
            d = rnd.uniform(0.3, 15)
            n = rnd.randint(2, 40)
            dist = [d * (k + 1) / (n + 1) for k in range(n)]
            hgt = [rnd.uniform(0, 300) for _ in range(n)]
            hts, hrs = rnd.uniform(0, 250), rnd.uniform(0, 250)
            f = rnd.choice([30, 60, 100, 250, 400])
            ref = bullington(d, dist, hgt, hts, hrs, f)
            got = sqf_bull(d, dist, hgt, hts, hrs, f)
            self.assertAlmostEqual(got, ref, delta=max(0.05, 1e-3 * ref), msg=(d, n, f))

    def test_a_ridge_costs_more_at_higher_frequency(self):
        args = ([2.5], [180], 100, 100)
        self.assertGreater(sqf_bull(5.0, *args, 400), sqf_bull(5.0, *args, 40))


class TestLinkBudget(unittest.TestCase):
    def test_free_space_loss(self):
        # P.525: 32.45 + 20 log 100 + 20 log 1 = 72.45 dB at 1 km, 100 MHz.
        state, pr, margin, loss = run_sqf(LINK, [37, 0, -116, 100, 1, [], [], 2, 2, 0], G)
        self.assertAlmostEqual(loss, 72.45, places=3)
        self.assertAlmostEqual(pr, 37 - 72.45, places=3)
        self.assertAlmostEqual(margin, pr + 116, places=3)
        self.assertEqual(state, "received")

    def test_vhf_diffracts_over_a_ridge(self):
        # 800 m above the path at 100 MHz: nu ~ 14.6, Ldiff ~ 46 dB; with
        # 90.5 dB of free-space loss a 5 W radio still closes (Pr ~ -100 dBm).
        out = run_sqf(LINK, [37, 0, -116, 100, 8, [4.0], [900], 102, 102, 0], G)
        self.assertEqual(out[0], "received")
        self.assertTrue(-105 < out[1] < -95, out[1])

    def test_a_massif_cuts_a_uhf_link(self):
        out = run_sqf(LINK, [37, 0, -116, 400, 8, [4.0], [2100], 102, 102, 0], G)
        self.assertEqual(out[0], "lost")

    def test_excess_loss_is_added(self):
        base = run_sqf(LINK, [37, 0, -116, 100, 1, [], [], 2, 2, 0], G)
        lossy = run_sqf(LINK, [37, 0, -116, 100, 1, [], [], 2, 2, 12], G)
        self.assertAlmostEqual(lossy[3] - base[3], 12, places=4)

    def test_defaults_are_the_prc152a_datasheet(self):
        src = LINK.read_text(encoding="utf-8")
        self.assertIn("AN/PRC-152A", src)
        self.assertIn('["_txDbm", 37', src)
        self.assertIn('["_sensDbm", -116', src)


class TestAtakReportingRate(unittest.TestCase):
    @staticmethod
    def atak(v, still=30, slow=20, fast=2):
        vmin, vmax = 0.44704, 13.4112
        if v < vmin:
            return still
        if v >= vmax:
            return fast
        scaled = vmin + (v - vmin) * 100 / (vmax - vmin)
        return slow - scaled * (slow - fast) / 100

    def test_matches_atak(self):
        for v in (0, 0.3, 0.44704, 1.0, 1.5, 4, 8, 13.4, 13.4112, 30):
            with self.subTest(v=v):
                got = run_sqf(RATE, [v, 30, 20, 2], {}, float32=True)
                self.assertAlmostEqual(got, self.atak(v), delta=1e-4)

    def test_walking_reports_about_every_eighteen_seconds(self):
        # 1.5 m/s walk with the ATAK multicast defaults.
        self.assertAlmostEqual(run_sqf(RATE, [1.5, 30, 20, 2]), 18.458, delta=0.005)


if __name__ == "__main__":
    unittest.main()
