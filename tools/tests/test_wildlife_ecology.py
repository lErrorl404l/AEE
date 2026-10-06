#!/usr/bin/env python3
"""Wildlife ecology kernel tests (aee-wildlife-ecology).

The pure kernels run from their real SQF through tools/tests/sqf_lite.py, so a
failure is a source failure, not a mirror drift.  The source contracts read
the engine wiring, which the harness cannot execute.

Run: python3 -m unittest tools.tests.test_wildlife_ecology -v
"""

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WILDLIFE = ROOT / "addons" / "wildlife"
FUNCS = WILDLIFE / "functions"
DATA = WILDLIFE / "data"

MATCH = FUNCS / "fnc_getSpeciesMatch.sqf"
CORPUS = DATA / "ecology_corpus.sqf"


def load_corpus():
    return run_sqf(CORPUS, [])


def match(
    biome,
    sun_elevation,
    temperature,
    month,
    water_frac,
    veg_score,
    surface="ground",
    structure=0,
    weather=None,
    seed=1,
    corpus=None,
):
    if weather is None:
        weather = [0, 0, 0]
    if corpus is None:
        corpus = load_corpus()
    return run_sqf(
        MATCH,
        [
            biome,
            sun_elevation,
            temperature,
            month,
            water_frac,
            veg_score,
            surface,
            structure,
            weather,
            seed,
            corpus,
        ],
    )


def group_ids(rows):
    return [row[0] for row in rows]


class TestGetSpeciesMatch(unittest.TestCase):
    """fnc_getSpeciesMatch runs from the real SQF against the real corpus."""

    def test_temperate_june_day_returns_a_dawn_bird(self):
        rows = match("Cfb", 30, 18, 6, 0, 0.8)
        self.assertGreater(len(rows), 0)
        self.assertIn("temperate_bird_dawn", group_ids(rows))

    def test_every_row_is_a_group_id_with_a_weight_in_range(self):
        for group, weight in match("Cfb", 30, 18, 6, 0, 0.8):
            self.assertIsInstance(group, str)
            self.assertGreater(weight, 0)
            self.assertLessEqual(weight, 1)

    def test_arid_family_differs_from_temperate(self):
        self.assertNotEqual(
            match("Cfb", 30, 18, 6, 0, 0.8), match("BWh", 30, 18, 6, 0, 0.8)
        )

    def test_zero_celsius_january_returns_no_cricket(self):
        rows = match("Cfb", 30, 0, 1, 0, 0.8)
        self.assertNotIn("temperate_insect_cricket", group_ids(rows))

    def test_a_water_overlay_appears_over_high_water(self):
        rows = match("Cfb", 30, 18, 6, 0.9, 0.8)
        self.assertIn("water_bird", group_ids(rows))

    def test_the_sun_elevation_is_a_number_not_a_boolean(self):
        # A high sun keeps diurnal groups; a sun below the horizon drops them.
        day = group_ids(match("Cfb", 30, 18, 6, 0, 0.8))
        night = group_ids(match("Cfb", -30, 18, 6, 0, 0.8))
        self.assertIn("temperate_bird_day", day)
        self.assertNotIn("temperate_bird_day", night)

    def test_same_inputs_are_deterministic(self):
        self.assertEqual(
            match("Cfb", 30, 18, 6, 0, 0.8, seed=7),
            match("Cfb", 30, 18, 6, 0, 0.8, seed=7),
        )

    def test_a_seed_step_change_moves_the_weight(self):
        self.assertNotEqual(
            match("Cfb", 30, 18, 6, 0, 0.8, seed=7),
            match("Cfb", 30, 18, 6, 0, 0.8, seed=8),
        )

    def test_an_empty_corpus_returns_nothing(self):
        self.assertEqual(match("Cfb", 30, 18, 6, 0, 0.8, corpus=[]), [])


class TestSpeciesMatchSourceContracts(unittest.TestCase):
    """The wiring the harness cannot execute."""

    def test_the_kernel_is_pure(self):
        text = MATCH.read_text(encoding="utf-8")
        # Strip block and line comments: the header states the purity, the
        # contract must judge the code.
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_signature_reads_temperature_sun_and_month(self):
        code = MATCH.read_text(encoding="utf-8")
        for arg in ('["_sunElevationDeg"', '["_temperatureC"', '["_month"'):
            self.assertIn(arg, code, arg)

    def test_the_deprecated_shim_forwards_to_the_matcher(self):
        text = (FUNCS / "fnc_speciesForBiome.sqf").read_text(encoding="utf-8")
        self.assertIn("FUNC(getSpeciesMatch)", text)
        self.assertIn("FUNC(speciesDeprecation)", text)

    def test_spawn_fauna_calls_the_matcher(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("FUNC(getSpeciesMatch)", text)

    def test_the_matcher_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(getSpeciesMatch)", text)
        self.assertIn("PREP(speciesDeprecation)", text)


if __name__ == "__main__":
    unittest.main()
