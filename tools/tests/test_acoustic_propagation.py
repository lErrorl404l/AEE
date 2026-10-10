#!/usr/bin/env python3
"""Acoustic-propagation data-layer tests (issue #80).

Executes the real SQF kernels in addons/ambience through
tools/tests/sqf_lite.py, so a test failure is a source failure, not a mirror
drift.  The absorption kernel is validated against the ISO 9613-1:1993
equations (a Python reference) and against the issue #80 reference values
2.60 / 12.59 dB/km at 15 C, 50 % RH, 101.325 kPa.

Run: python3 -m unittest tools.tests.test_acoustic_propagation -v
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AMBIENCE = ROOT / "addons" / "ambience" / "functions"

ABSORPTION = AMBIENCE / "fnc_atmosphericAbsorption.sqf"
ABSORPTION_TABLE = AMBIENCE / "fnc_atmosphericAbsorptionTable.sqf"
SPECTRUM = AMBIENCE / "fnc_acousticSpectrum.sqf"
ARRIVING = AMBIENCE / "fnc_getArrivingSound.sqf"
ARRIVAL_TIME = AMBIENCE / "fnc_getArrivalTime.sqf"
SOURCE_DB = AMBIENCE / "fnc_acousticSourceDb.sqf"

BANDS = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000]

KERNELS = (ABSORPTION, ABSORPTION_TABLE, SPECTRUM, ARRIVING, ARRIVAL_TIME)


def source_db(kind):
    return run_sqf(SOURCE_DB, [kind])


GLOBALS = {"__FUNC__acousticSourceDb": source_db}


def absorption(f_hz, t_c, rh, p_hpa=1013.25):
    return run_sqf(ABSORPTION, [f_hz, t_c, rh, p_hpa])


def absorption_table(t_c, rh, p_hpa=1013.25):
    return run_sqf(
        ABSORPTION_TABLE,
        [t_c, rh, p_hpa],
        globals_={"__FUNC__atmosphericAbsorption": absorption},
    )


def spectrum(kind):
    return run_sqf(SPECTRUM, [kind], globals_=GLOBALS)


def arriving(source_spectrum, distance, index=1.0, table=None, occlusion=0.0):
    if table is None:
        table = []
    return run_sqf(
        ARRIVING,
        [source_spectrum, distance, index, table, occlusion],
        globals_=GLOBALS,
    )


def arrival_time(shot_time, distance, t_c=15.0, wind=0.0):
    return run_sqf(ARRIVAL_TIME, [shot_time, distance, t_c, wind])


def iso9613_db_per_m(f_hz, t_c, rh, p_hpa=1013.25):
    """ISO 9613-1:1993 eq (3)-(5), the independent reference (issue #80)."""
    t_k = t_c + 273.15
    t0 = 293.15
    p = p_hpa * 100.0
    p0 = 101325.0
    psat = 6.1121 * math.exp((18.678 - t_c / 234.5) * (t_c / (257.14 + t_c))) * 100.0
    h = (rh / 100.0) * psat / p
    fr_o = (p / p0) * (24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    fr_n = (t_k / t0) ** -0.5 * (
        9.0 + 280.0 * h * math.exp(-4.170 * ((t_k / t0) ** (-1.0 / 3.0) - 1.0))
    )
    alpha = (
        8.686
        * f_hz**2
        * (
            1.84e-11 * (p / p0) ** -1 * (t_k / t0) ** 0.5
            + (t_k / t0) ** -2.5
            * (
                0.01275 * math.exp(-2239.1 / t_k) / (fr_o + f_hz**2 / fr_o)
                + 0.1068 * math.exp(-3352.0 / t_k) / (fr_n + f_hz**2 / fr_n)
            )
        )
    )
    return alpha


class TestAtmosphericAbsorption(unittest.TestCase):
    """fnc_atmosphericAbsorption runs from the real SQF."""

    def test_issue80_reference_values(self):
        one_k = absorption(1000, 15, 50) * 1000.0
        eight_k = absorption(8000, 15, 50) * 1000.0
        self.assertAlmostEqual(one_k, 2.60, delta=0.05)
        self.assertAlmostEqual(eight_k, 12.59, delta=0.05)

    def test_matches_the_iso_standard_over_a_grid(self):
        for f_hz in BANDS:
            for t_c, rh, p_hpa in (
                (15, 50, 1013.25),
                (-10, 80, 1000.0),
                (40, 20, 980.0),
            ):
                with self.subTest(f=f_hz, t=t_c, rh=rh, p=p_hpa):
                    self.assertAlmostEqual(
                        absorption(f_hz, t_c, rh, p_hpa),
                        iso9613_db_per_m(f_hz, t_c, rh, p_hpa),
                        places=9,
                    )

    def test_zero_frequency_absorbs_nothing(self):
        self.assertEqual(absorption(0, 15, 50), 0.0)

    def test_humidity_raises_the_high_band_absorption(self):
        dry = absorption(4000, 15, 10)
        wet = absorption(4000, 15, 90)
        self.assertGreater(wet, dry)


class TestAtmosphericAbsorptionTable(unittest.TestCase):
    """fnc_atmosphericAbsorptionTable runs from the real SQF."""

    def test_nine_octave_bands_low_first(self):
        table = absorption_table(15, 50)
        self.assertEqual([row[0] for row in table], BANDS)

    def test_each_row_matches_the_per_band_kernel(self):
        for row in absorption_table(15, 50):
            with self.subTest(f=row[0]):
                self.assertAlmostEqual(row[1], absorption(row[0], 15, 50), places=12)


class TestAcousticSpectrum(unittest.TestCase):
    """fnc_acousticSpectrum runs from the real SQF."""

    def test_nine_bands(self):
        self.assertEqual([row[0] for row in spectrum("gunshot")], BANDS)

    def test_peak_band_carries_the_source_level(self):
        for kind in ("gunshot", "suppressed", "explosion", "vehicle", "footstep"):
            with self.subTest(kind=kind):
                levels = [row[1] for row in spectrum(kind)]
                self.assertAlmostEqual(max(levels), source_db(kind))

    def test_suppressed_cuts_the_high_bands(self):
        gun = dict(spectrum("gunshot"))
        sup = dict(spectrum("suppressed"))
        self.assertLess(sup[8000], gun[8000] - 20.0)
        self.assertLess(sup[2000], gun[2000] - 20.0)

    def test_explosion_is_low_band_dominant(self):
        exp = dict(spectrum("explosion"))
        self.assertGreater(exp[31.5], exp[1000])
        self.assertGreater(exp[63], exp[500])

    def test_unknown_kind_is_silent(self):
        self.assertEqual([row[1] for row in spectrum("nonsense")], [0.0] * 9)


class TestGetArrivingSound(unittest.TestCase):
    """fnc_getArrivingSound runs from the real SQF."""

    def test_spreading_is_6_db_per_doubling(self):
        src = spectrum("gunshot")
        near = dict(arriving(src, 1000, 1.0))
        far = dict(arriving(src, 2000, 1.0))
        for f in BANDS:
            with self.subTest(f=f):
                self.assertAlmostEqual(near[f] - far[f], 20 * math.log10(2), places=6)

    def test_absorption_cuts_the_high_band_more(self):
        src = spectrum("gunshot")
        table = absorption_table(15, 50)
        arr = dict(arriving(src, 10000, 1.0, table))
        spread = 20 * math.log10(10000)
        low_loss = src[0][1] - spread - arr[31.5]
        high_loss = src[8][1] - spread - arr[8000]
        self.assertGreater(high_loss, low_loss)

    def test_index_extends_the_range(self):
        src = spectrum("gunshot")
        loud = dict(arriving(src, 5000, 2.0))
        quiet = dict(arriving(src, 5000, 0.3))
        for f in BANDS:
            with self.subTest(f=f):
                self.assertGreater(loud[f], quiet[f])

    def test_occlusion_lowers_every_band(self):
        src = spectrum("gunshot")
        clear = dict(arriving(src, 1000, 1.0, None, 0))
        blocked = dict(arriving(src, 1000, 1.0, None, 6))
        for f in BANDS:
            with self.subTest(f=f):
                self.assertAlmostEqual(clear[f] - blocked[f], 6.0, places=9)

    def test_deterministic(self):
        src = spectrum("explosion")
        table = absorption_table(20, 40)
        self.assertEqual(
            arriving(src, 3000, 1.1, table, 3), arriving(src, 3000, 1.1, table, 3)
        )


class TestGetArrivalTime(unittest.TestCase):
    """fnc_getArrivalTime runs from the real SQF."""

    def test_distance_over_speed_at_20c(self):
        self.assertAlmostEqual(arrival_time(0, 3432, 20), 10.0, places=1)

    def test_speed_of_sound_at_20c_is_343(self):
        speed = 3432 / (arrival_time(0, 3432, 20) - 0)
        self.assertAlmostEqual(speed, 343.2, delta=0.5)

    def test_hotter_air_arrives_earlier(self):
        self.assertLess(arrival_time(0, 10000, 35), arrival_time(0, 10000, -10))

    def test_wind_along_the_path_changes_the_time(self):
        downwind = arrival_time(0, 1000, 15, 20)
        upwind = arrival_time(0, 1000, 15, -20)
        self.assertLess(downwind, upwind)

    def test_shot_time_is_offset_not_scaled(self):
        self.assertAlmostEqual(
            arrival_time(5, 1000, 15) - arrival_time(0, 1000, 15), 5.0, places=9
        )


class TestKernelPurity(unittest.TestCase):
    """The new kernels are pure: no engine read, no engine write."""

    FORBIDDEN = ("missionNamespace", "GVAR(", "random", "diag_", "setVariable")

    def _code(self, path):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        return re.sub(r"//[^\n]*", "", text)

    def test_no_engine_access(self):
        for path in KERNELS:
            code = self._code(path)
            with self.subTest(kernel=path.name):
                for token in self.FORBIDDEN:
                    self.assertNotIn(token, code, f"{path.name} contains {token}")


if __name__ == "__main__":
    unittest.main()
