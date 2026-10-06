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
from sqf_lite import Lambda, Params, load_sqf, run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WILDLIFE = ROOT / "addons" / "wildlife"
FUNCS = WILDLIFE / "functions"
DATA = WILDLIFE / "data"

MATCH = FUNCS / "fnc_getSpeciesMatch.sqf"
CALL_PATTERN = FUNCS / "fnc_getCallPattern.sqf"
SEASON = FUNCS / "fnc_getSeason.sqf"
GRID = FUNCS / "fnc_environmentGrid.sqf"
CORPUS = DATA / "ecology_corpus.sqf"


def _kernel(path):
    """A callable Lambda built from a real kernel file, params pre-bound."""
    stmts = load_sqf(path)
    params, body = [], stmts
    if stmts and isinstance(stmts[0], Params):
        params = [name for name, _default in stmts[0].specs]
        body = stmts[1:]
    return Lambda(params, body, {})


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


def call_pattern(
    group_id,
    sun_elevation,
    hour,
    month,
    temperature,
    wind=0,
    rain=0,
    pattern=None,
):
    if pattern is None:
        pattern = [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0]
    return run_sqf(
        CALL_PATTERN,
        [group_id, sun_elevation, hour, month, temperature, wind, rain, pattern],
    )


def get_season(month, koppen="Cfb"):
    return run_sqf(SEASON, [month, koppen])


CALL_PATTERN_BIRD = "temperate_bird_dawn"
CALL_PATTERN_CRICKET = [0.3, 0, 0, 0, 0, 0.6, 1]


class TestGetCallPattern(unittest.TestCase):
    """fnc_getCallPattern runs from the real SQF."""

    def test_the_dawn_chorus_exceeds_midday(self):
        predawn = call_pattern(CALL_PATTERN_BIRD, -6, 5, 6, 10)
        midday = call_pattern(CALL_PATTERN_BIRD, 60, 12, 6, 10)
        self.assertGreater(predawn, midday)
        self.assertGreater(predawn, 0)

    def test_the_cricket_is_positive_at_ten_celsius(self):
        value = call_pattern(
            "temperate_insect_cricket", -30, 22, 6, 10, pattern=CALL_PATTERN_CRICKET
        )
        self.assertGreater(value, 0)

    def test_the_cricket_is_zero_below_the_dolbear_floor(self):
        value = call_pattern(
            "temperate_insect_cricket", -30, 22, 6, 2, pattern=CALL_PATTERN_CRICKET
        )
        self.assertEqual(value, 0)

    def test_rain_suppresses_the_call(self):
        dry = call_pattern(CALL_PATTERN_BIRD, -6, 5, 6, 10, rain=0)
        wet = call_pattern(CALL_PATTERN_BIRD, -6, 5, 6, 10, rain=1)
        self.assertLess(wet, dry)

    def test_wind_suppresses_the_call(self):
        calm = call_pattern(CALL_PATTERN_BIRD, -6, 5, 6, 10, wind=0)
        windy = call_pattern(CALL_PATTERN_BIRD, -6, 5, 6, 10, wind=20)
        self.assertLess(windy, calm)

    def test_the_cicada_is_silent_below_the_horizon(self):
        value = call_pattern("temperate_insect_cicada", -30, 12, 6, 25)
        self.assertEqual(value, 0)

    def test_the_amphibian_chorus_is_gated_by_rain(self):
        dry = call_pattern(
            "temperate_amphibian",
            -30,
            22,
            6,
            10,
            rain=0,
            pattern=[0.4, 0.1, 0, 0, 0, 0.5, 0.9],
        )
        wet = call_pattern(
            "temperate_amphibian",
            -30,
            22,
            6,
            10,
            rain=0.6,
            pattern=[0.4, 0.1, 0, 0, 0, 0.5, 0.9],
        )
        self.assertLess(dry, wet)

    def test_the_probability_is_bounded(self):
        value = call_pattern(CALL_PATTERN_BIRD, 0, 6, 6, 10, rain=0, wind=0)
        self.assertGreaterEqual(value, 0)
        self.assertLessEqual(value, 1)


class TestGetSeason(unittest.TestCase):
    """fnc_getSeason runs from the real SQF."""

    def test_each_month_returns_a_stable_enum_and_factor(self):
        for month in range(1, 13):
            first = get_season(month)
            second = get_season(month)
            self.assertEqual(first, second)
            self.assertIn(first[0], (0, 1, 2, 3), month)
            self.assertGreaterEqual(first[1], 0)
            self.assertLessEqual(first[1], 1)

    def test_the_seasons_map_to_the_months(self):
        self.assertEqual(get_season(4)[0], 1)
        self.assertEqual(get_season(7)[0], 2)
        self.assertEqual(get_season(10)[0], 3)

    def test_winter_is_december_january_february(self):
        self.assertEqual(get_season(1)[0], 0)
        self.assertEqual(get_season(12)[0], 0)

    def test_the_tropics_swing_less(self):
        self.assertLess(get_season(7, "Af")[1], get_season(7, "Cfb")[1])


class TestTemporalSourceContracts(unittest.TestCase):
    """The wiring the harness cannot execute."""

    def test_the_call_pattern_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/", "", CALL_PATTERN.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_season_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/", "", SEASON.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_temporal_kernels_are_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(getCallPattern)", text)
        self.assertIn("PREP(getSeason)", text)

    def test_the_dolbear_inverse_is_stated_with_its_band(self):
        code = CALL_PATTERN.read_text(encoding="utf-8")
        self.assertIn("7 * T_C - 30", code)
        self.assertIn("5 to 30 C", code)


SAMPLER = FUNCS / "fnc_sampleNeighbourhood.sqf"


def sample(
    centre=(0, 0, 0),
    water=False,
    foliage=None,
    buildings=None,
    cell_size=25,
    cells_per_axis=5,
    max_objects=12,
    budget_ms=2.0,
    store=None,
    queries=None,
):
    if foliage is None:
        foliage = ["Tree", "Bush"]
    if buildings is None:
        buildings = ["Building"]
    if store is None:
        store = {}
    if queries is None:
        queries = []

    def _nearest(payload):
        queries.append(payload)
        types = payload[1]
        for t in types:
            if t in ("Tree", "Bush"):
                return foliage
        return buildings

    globals_ = {
        "missionNamespace": store,
        "getVariable": lambda n, s: n.get(s[0], s[1]),
        "setVariable": lambda n, s: n.__setitem__(s[0], s[1]),
        "diag_tickTime": 100.0,
        "surfaceIsWater": lambda p: water,
        "surfaceType": lambda p: "GdtConcrete",
        "getTerrainHeightASL": lambda p: 10.0,
        "nearestTerrainObjects": _nearest,
        "__EFUNC__material_classifyBySurfaceType": lambda s: "concrete",
        "__FUNC__environmentGrid": _kernel(GRID),
        "WILDLIFE_ENVIRONMENT_CAP": 256,
        "WILDLIFE_ENVIRONMENT_QUERY_CAP": 64,
        "WILDLIFE_ENVIRONMENT_HORIZON": 120,
    }
    result = run_sqf(
        SAMPLER,
        [list(centre), cell_size, cells_per_axis, max_objects, budget_ms],
        globals_=globals_,
    )
    return result, store, queries


class TestSampleNeighbourhood(unittest.TestCase):
    """fnc_sampleNeighbourhood runs from the real SQF with engine stubs."""

    def test_a_concrete_cell_has_no_foliage(self):
        result, _store, _q = sample(foliage=[], buildings=[])
        self.assertEqual(result[0], 0)
        self.assertEqual(result[2], 0)
        self.assertEqual(result[3], 0)
        self.assertIn(["concrete", 25.0], result[1])

    def test_a_wooded_cell_has_foliage(self):
        result, _store, _q = sample(foliage=["Tree", "Tree", "Bush"], buildings=[])
        self.assertGreater(result[0], 0)

    def test_a_water_cell_is_water(self):
        result, _store, _q = sample(water=True, foliage=[], buildings=[])
        self.assertEqual(result[2], 1)

    def test_the_mean_elevation_is_returned(self):
        result, _store, _q = sample(foliage=[], buildings=[])
        self.assertEqual(result[4], 10.0)

    def test_the_foliage_fraction_is_bounded(self):
        result, _store, _q = sample(foliage=["Tree"] * 50, buildings=[], max_objects=12)
        self.assertLessEqual(result[0], 1)

    def test_a_zero_budget_requeues_and_the_next_call_progresses(self):
        result0, store, _q = sample(foliage=["Tree"], buildings=[], budget_ms=0)
        self.assertEqual(result0[0], 0)
        self.assertEqual(len(store.get("__QGVAR__environmentPending", [])), 25)
        result1, store, _q = sample(
            foliage=["Tree"], buildings=[], budget_ms=2.0, store=store
        )
        self.assertGreater(result1[0], 0)
        self.assertEqual(len(store.get("__QGVAR__environmentPending", [])), 0)

    def test_a_second_call_uses_the_cache_and_queries_nothing(self):
        first, store, queries1 = sample()
        self.assertGreater(len(queries1), 0)
        second, store, queries2 = sample(store=store)
        self.assertEqual(len(queries2), 0)
        self.assertEqual(first, second)


class TestSamplerSourceContracts(unittest.TestCase):
    def test_the_sampler_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(sampleNeighbourhood)", text)

    def test_the_policy_defines_exist(self):
        text = (WILDLIFE / "script_component.hpp").read_text(encoding="utf-8")
        self.assertIn("WILDLIFE_ENVIRONMENT_QUERY_CAP", text)
        self.assertIn("WILDLIFE_ENVIRONMENT_CAP", text)

    def test_the_sampler_requeues_at_the_front(self):
        code = SAMPLER.read_text(encoding="utf-8")
        self.assertIn("environmentPending", code)
        self.assertIn("classifyBySurfaceType", code)
        self.assertIn("nearestTerrainObjects", code)


SUITABILITY = FUNCS / "fnc_environmentSuitability.sqf"

WOODLAND_RULE = [0.6, 0, 0, 0.1]
CRICKET_RULE = [0.3, 0.6, 0, 0]
SHOREBIRD_RULE = [0.1, 0, 0.9, 0]


def suitability(environment, rule):
    return run_sqf(SUITABILITY, [environment, rule])


class TestEnvironmentSuitability(unittest.TestCase):
    """fnc_environmentSuitability runs from the real SQF."""

    def test_a_woodland_bird_scores_low_on_concrete(self):
        value = suitability([0.0, [["concrete", 1]], 0, 0.9, 10], WOODLAND_RULE)
        self.assertLess(value, 0.3)

    def test_a_woodland_bird_scores_high_in_forest(self):
        value = suitability([0.9, [["vegetation", 1]], 0, 0.1, 10], WOODLAND_RULE)
        self.assertGreater(value, 0.7)

    def test_a_cricket_scores_zero_on_concrete(self):
        self.assertEqual(
            suitability([0.0, [["concrete", 1]], 0, 0, 10], CRICKET_RULE), 0
        )

    def test_a_cricket_scores_on_a_warm_surface(self):
        warm = suitability([0.0, [["rock", 1]], 0, 0, 10], CRICKET_RULE)
        cold = suitability([0.0, [["concrete", 1]], 0, 0, 10], CRICKET_RULE)
        self.assertGreater(warm, cold)

    def test_a_shorebird_scores_on_water(self):
        self.assertGreater(suitability([0.0, [], 0.9, 0, 10], SHOREBIRD_RULE), 0.7)

    def test_a_missing_factor_field_is_zero_weight(self):
        # Only the foliage weight is present, so the score is the foliage.
        self.assertAlmostEqual(suitability([0.8, [], 0, 0, 10], [0.5]), 0.8)

    def test_the_result_is_clamped(self):
        value = suitability([2.0, [], 2.0, 2.0, 10], [1, 1, 1, 1])
        self.assertGreaterEqual(value, 0)
        self.assertLessEqual(value, 1)

    def test_an_empty_environment_is_zero(self):
        self.assertEqual(suitability([], WOODLAND_RULE), 0)

    def test_an_all_zero_rule_is_zero(self):
        self.assertEqual(suitability([0.8, [], 0, 0, 10], [0, 0, 0, 0]), 0)


class TestSuitabilitySourceContracts(unittest.TestCase):
    def test_the_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/", "", SUITABILITY.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_kernel_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(environmentSuitability)", text)


BOUNDARY = FUNCS / "fnc_habitatBoundary.sqf"


def boundary(here, neighbours, threshold=0.6, seed=42, rate=0.02):
    return run_sqf(BOUNDARY, [here, neighbours, threshold, seed, rate])


class TestHabitatBoundary(unittest.TestCase):
    """fnc_habitatBoundary runs from the real SQF."""

    def test_a_high_here_score_stays(self):
        self.assertEqual(boundary(0.9, [0.8, 0.7])[0], 0)

    def test_a_higher_neighbour_moves(self):
        self.assertEqual(boundary(0.2, [0.9, 0.3])[0], 1)

    def test_a_lower_neighbour_is_avoided(self):
        self.assertEqual(boundary(0.2, [0.1, 0.15])[0], 2)

    def test_same_inputs_are_deterministic(self):
        self.assertEqual(
            boundary(0.9, [0.8, 0.7], seed=42), boundary(0.9, [0.8, 0.7], seed=42)
        )

    def test_a_zero_exception_rate_never_excurses(self):
        for seed in range(1000):
            self.assertFalse(boundary(0.9, [0.8, 0.7], seed=seed, rate=0.0)[1])

    def test_the_default_exception_rate_is_rare(self):
        count = sum(
            1 for seed in range(1000) if boundary(0.9, [0.8, 0.7], seed=seed)[1]
        )
        self.assertGreater(count, 0)
        self.assertLess(count, 100)


class TestBoundarySourceContracts(unittest.TestCase):
    def test_the_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/", "", BOUNDARY.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_kernel_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(habitatBoundary)", text)


def grid(store, now):
    return run_sqf(
        GRID,
        [store, now],
        globals_={
            "WILDLIFE_ENVIRONMENT_CAP": 256,
            "WILDLIFE_ENVIRONMENT_HORIZON": 120,
        },
    )


class TestEnvironmentGrid(unittest.TestCase):
    """fnc_environmentGrid runs from the real SQF."""

    def test_a_fresh_entry_is_kept(self):
        store = [[[0, 0], [0.5, [], 0, 0, 10], 100.0]]
        self.assertEqual(len(grid(store, 110)), 1)

    def test_a_stale_entry_is_dropped(self):
        store = [[[0, 0], [0.5, [], 0, 0, 10], 0.0]]
        self.assertEqual(grid(store, 200), [])

    def test_the_store_is_capped_keeping_the_newest(self):
        store = [[[i, 0], [0.5, [], 0, 0, 10], 1000.0 - (i * 0.01)] for i in range(300)]
        out = grid(store, 1000)
        self.assertEqual(len(out), 256)
        self.assertGreater(out[0][2], 999.0)

    def test_an_empty_store_is_empty(self):
        self.assertEqual(grid([], 10), [])


class TestEnvironmentGridSourceContracts(unittest.TestCase):
    def test_the_cap_and_horizon_match_the_ai_values(self):
        wild = (WILDLIFE / "script_component.hpp").read_text(encoding="utf-8")
        ai = (ROOT / "addons" / "ai" / "script_component.hpp").read_text(
            encoding="utf-8"
        )

        def value(text, name):
            match = re.search(rf"#define\s+{name}\s+([0-9]+)", text)
            self.assertIsNotNone(match, name)
            return int(match.group(1))

        self.assertEqual(
            value(wild, "WILDLIFE_ENVIRONMENT_CAP"), value(ai, "AI_CELL_CAP")
        )
        self.assertEqual(
            value(wild, "WILDLIFE_ENVIRONMENT_HORIZON"), value(ai, "AI_CELL_HORIZON")
        )

    def test_the_state_line_reports_the_cache(self):
        text = (FUNCS / "fnc_logWildlifeState.sqf").read_text(encoding="utf-8")
        self.assertIn("env=%25/%26", text)
        self.assertIn("QGVAR(environment)", text)

    def test_the_environment_debug_switch_exists(self):
        text = (WILDLIFE / "initSettings.inc.sqf").read_text(encoding="utf-8")
        self.assertIn("environmentDebug", text)
        self.assertIn('"AEE Debug"', text)

    def test_the_sampler_reads_the_grid(self):
        text = (FUNCS / "fnc_sampleNeighbourhood.sqf").read_text(encoding="utf-8")
        self.assertIn("FUNC(environmentGrid)", text)


if __name__ == "__main__":
    unittest.main()
