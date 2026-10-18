#!/usr/bin/env python3
"""Acoustic-propagation data-layer tests (issue #80).

Executes the real SQF kernels in addons/ambience through
tools/tests/sqf_lite.py, so a test failure is a source failure, not a mirror
drift.  The absorption kernel is validated against the ISO 9613-1:1993
equations (a Python reference) and against ISO 9613-2:1996 Table 2.

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

ABSORPTION = AMBIENCE.parents[1] / "lib/functions/acoustics/fnc_atmosphericAbsorption.sqf"
ABSORPTION_TABLE = AMBIENCE / "fnc_atmosphericAbsorptionTable.sqf"
ARRIVING = AMBIENCE / "fnc_getArrivingSound.sqf"
ARRIVAL_TIME = AMBIENCE / "fnc_getArrivalTime.sqf"
SOURCE_DB = AMBIENCE / "fnc_acousticSourceDb.sqf"
REGISTER = ROOT / "docs" / "wiki" / "research" / "wildlife-ecology-constants.md"

BANDS = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000]

KERNELS = (ABSORPTION, ABSORPTION_TABLE, ARRIVING, ARRIVAL_TIME)


def source_db(kind):
    blast = AMBIENCE.parents[1] / "lib/functions/acoustics/fnc_blastPeakDb.sqf"
    return run_sqf(SOURCE_DB, [kind], {"__EFUNC__lib_blastPeakDb": lambda *a: run_sqf(blast, list(a))})


GLOBALS = {"__FUNC__acousticSourceDb": source_db}


def absorption(f_hz, t_c, rh, p_hpa=1013.25):
    return run_sqf(ABSORPTION, [f_hz, t_c, rh, p_hpa])


def absorption_table(t_c, rh, p_hpa=1013.25):
    return run_sqf(
        ABSORPTION_TABLE,
        [t_c, rh, p_hpa],
        globals_={"__EFUNC__lib_atmosphericAbsorption": absorption},
    )


def spectrum(kind):
    """A flat test spectrum at the kind's source level (the per-band shape
    kernel was removed: no published shape was held)."""
    return [[f, source_db(kind)] for f in BANDS]


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
    h = rh * psat / p  # molar concentration in PERCENT (ISO 9613-1 eq. B.1)
    fr_o = (p / p0) * (24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h))
    fr_n = (p / p0) * (t_k / t0) ** -0.5 * (
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

    def test_iso_9613_2_table_2(self):
        # ISO 9613-2:1996 Table 2, 10 C, 70 % RH, dB/km, to its printed digits.
        table = {63: 0.1, 125: 0.4, 250: 1.0, 500: 1.9, 1000: 3.7,
                 2000: 9.7, 4000: 32.8, 8000: 117}
        for f, ref in table.items():
            got = absorption(f, 10, 70) * 1000.0
            self.assertAlmostEqual(got, ref, delta=max(0.06, 0.02 * ref), msg=f)

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

    def test_dry_air_absorbs_the_high_band_most(self):
        # ISO 9613-1: at 4 kHz the absorption peaks at low humidity (the
        # oxygen relaxation frequency sweeps through the band) and falls as
        # the air gets more humid.
        dry = absorption(4000, 15, 10)
        wet = absorption(4000, 15, 90)
        self.assertGreater(dry, wet)


class TestAtmosphericAbsorptionTable(unittest.TestCase):
    """fnc_atmosphericAbsorptionTable runs from the real SQF."""

    def test_nine_octave_bands_low_first(self):
        table = absorption_table(15, 50)
        self.assertEqual([row[0] for row in table], BANDS)

    def test_each_row_matches_the_per_band_kernel(self):
        for row in absorption_table(15, 50):
            with self.subTest(f=row[0]):
                self.assertAlmostEqual(row[1], absorption(row[0], 15, 50), places=12)


class TestAcousticSourceDb(unittest.TestCase):
    """fnc_acousticSourceDb runs from the real SQF; the sourced rows."""

    def test_gunshot_is_the_measured_peak_level(self):
        # SOURCED: the measured unsuppressed centre-fire peak is 160 to
        # 170 dB.  NIOSH HHE report 2013-0124-3208 (Results) and the NIOSH
        # "Hit the Mark" bulletin, 2017.  The table takes 160.
        self.assertAlmostEqual(source_db("gunshot"), 160.0, places=6)

    def test_suppressed_sits_in_the_measured_reduction_band(self):
        # SOURCED: a suppressor lowers the peak by 17 to 24 dB at the ear.
        # Murphy, Flamme and others 2017, Int. J. Audiology, DOI
        # 10.1080/14992027.2017.1407459.  The table takes 22 dB, a point
        # inside the band (its mid is 20.5 dB), not the mid.
        suppression = source_db("gunshot") - source_db("suppressed")
        self.assertGreaterEqual(suppression, 17.0)
        self.assertLessEqual(suppression, 24.0)
        self.assertAlmostEqual(suppression, 22.0, places=6)

    def test_the_derivation_states_the_suppression_it_uses(self):
        # 22 dB is inside the measured 17-24 dB band and is not its mid, so
        # neither the source header nor the constants register may call it
        # the mid reduction, and both must state the band's mid.
        for path in (SOURCE_DB, REGISTER):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("22 dB", text)
                self.assertIn("20.5", text)
                self.assertIsNone(re.search(r"(?i)mid\s+reduction", text))

    def test_the_source_db_cites_the_measured_values(self):
        text = SOURCE_DB.read_text(encoding="utf-8")
        self.assertIn("2013-0124-3208", text)
        self.assertIn("10.1080/14992027.2017.1407459", text)


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
