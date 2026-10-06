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


VEG_SCORE = FUNCS / "fnc_vegScore.sqf"


def veg_score(signals, values_fn=None):
    globals_ = {}
    if values_fn is not None:
        globals_["values"] = values_fn
    return run_sqf(VEG_SCORE, [signals], globals_=globals_)


class TestVegScore(unittest.TestCase):
    """fnc_vegScore runs from the real SQF."""

    def test_a_legacy_number_is_clamped(self):
        self.assertAlmostEqual(veg_score([0, 0.8]), 0.8)

    def test_a_negative_number_clamps_to_zero(self):
        self.assertEqual(veg_score([0, -1]), 0)

    def test_a_number_above_one_clamps_to_one(self):
        self.assertEqual(veg_score([0, 2]), 1)

    def test_short_signals_are_zero(self):
        self.assertEqual(veg_score([]), 0)

    def test_the_hashmap_shape_takes_the_strongest_vote(self):
        value = veg_score(
            [0, {"Cfb": 0.4, "Dfb": 0.9}], values_fn=lambda d: list(d.values())
        )
        self.assertAlmostEqual(value, 0.9)


class TestEnvironmentConsumptionContracts(unittest.TestCase):
    """The wiring the harness cannot execute."""

    def test_all_three_vegetation_readers_call_the_helper(self):
        for name in (
            "fnc_wildlifeTick.sqf",
            "fnc_spawnFauna.sqf",
            "fnc_applyAnimalBehaviour.sqf",
        ):
            text = (FUNCS / name).read_text(encoding="utf-8")
            self.assertIn("FUNC(vegScore)", text, name)

    def test_the_veg_score_kernel_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(vegScore)", text)

    def test_spawn_gates_on_the_environment_suitability(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("FUNC(sampleNeighbourhood)", text)
        self.assertIn("FUNC(environmentSuitability)", text)
        self.assertIn("WILDLIFE_SUITABILITY_MIN", text)

    def test_movement_respects_the_habitat_boundary(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("FUNC(habitatBoundary)", text)

    def test_the_tick_still_passes_the_veg_score_to_the_bed(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("_vegScore, _settlement, _coastal", text)
        self.assertIn("call FUNC(soundBedForContext)", text)


ACOUSTIC = FUNCS / "fnc_acousticLevel.sqf"
ACOUSTIC_SOURCE = FUNCS / "fnc_acousticSourceDb.sqf"
ACOUSTIC_PUBLISH = FUNCS / "fnc_acousticPublish.sqf"
ACOUSTIC_SAMPLE = FUNCS / "fnc_acousticSample.sqf"
PERCEIVE = FUNCS / "fnc_wildlifePerceive.sqf"
THINK = FUNCS / "fnc_wildlifeThink.sqf"


def _acoustic_kernel():
    """The acoustic kernel bound as a FUNC for the sample kernel to call."""
    return _kernel(ACOUSTIC)


ACOUSTIC_GLOBALS = {
    "WILDLIFE_ACOUSTIC_OCCLUSION_DB": 6,
    "WILDLIFE_ACOUSTIC_OCCLUSION_RADIUS_M": 2.5,
    "WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB": 30,
    "WILDLIFE_ACOUSTIC_LOUD_DB": 140,
    "WILDLIFE_ACOUSTIC_EVENT_CAP": 64,
    "WILDLIFE_ACOUSTIC_EVENT_HORIZON": 3,
}
ACOUSTIC_GLOBALS["__FUNC__acousticLevel"] = _acoustic_kernel()


def acoustic(events, listener, index=1.0, occluders=None):
    if occluders is None:
        occluders = []
    return run_sqf(
        ACOUSTIC, [events, listener, index, occluders], globals_=ACOUSTIC_GLOBALS
    )


def level_at(distance, source_db=160, index=1.0, kind="gunshot", occluders=None):
    return acoustic(
        [[[0, 0, 0], source_db, kind]],
        [distance, 0, 0],
        index=index,
        occluders=occluders,
    )[0][1]


class TestAcousticLevel(unittest.TestCase):
    """fnc_acousticLevel runs from the real SQF."""

    def test_the_level_falls_smoothly_with_distance(self):
        near = level_at(10)
        mid = level_at(100)
        far = level_at(1000)
        self.assertGreater(near, mid)
        self.assertGreater(mid, far)

    def test_the_level_never_hard_cuts_at_a_radius(self):
        # No fixed radius: the level keeps falling but stays positive well
        # beyond the old 120 m gate.
        at_500 = level_at(500)
        at_5000 = level_at(5000)
        self.assertGreater(at_500, 0)
        self.assertGreater(at_5000, 0)
        self.assertGreater(at_500, at_5000)

    def test_an_occluder_lowers_the_level(self):
        clear = level_at(500, occluders=[])
        blocked = level_at(500, occluders=[[250, 0, 0]])
        self.assertLess(blocked, clear)

    def test_an_occluder_off_the_line_does_not_block(self):
        clear = level_at(500)
        off = level_at(500, occluders=[[250, 500, 0]])
        self.assertEqual(off, clear)

    def test_the_same_cell_is_the_strongest(self):
        self.assertEqual(level_at(0), 1)
        self.assertLess(level_at(200), level_at(0))

    def test_a_suppressed_source_is_inaudible_far_away(self):
        self.assertEqual(level_at(50000, source_db=100), 0)
        self.assertGreater(level_at(50, source_db=100), 0)

    def test_the_weather_index_extends_the_range(self):
        good = level_at(2000, index=2.0)
        bad = level_at(2000, index=0.3)
        self.assertGreater(good, bad)

    def test_the_stimulus_is_bounded(self):
        self.assertLessEqual(level_at(0, source_db=400), 1)
        self.assertGreaterEqual(level_at(1e7, source_db=1), 0)

    def test_same_inputs_are_deterministic(self):
        self.assertEqual(level_at(300), level_at(300))

    def test_the_kind_is_passed_through(self):
        rows = acoustic([[[0, 0, 0], 160, "vehicle"]], [10, 0, 0])
        self.assertEqual(rows[0][0], "vehicle")


class TestAcousticSourceDb(unittest.TestCase):
    """fnc_acousticSourceDb runs from the real SQF."""

    def test_every_named_kind_has_a_level(self):
        for kind in (
            "gunshot",
            "suppressed",
            "explosion",
            "grenade",
            "aircraft",
            "vehicle",
            "footstep",
        ):
            self.assertGreater(run_sqf(ACOUSTIC_SOURCE, [kind]), 0, kind)

    def test_an_unknown_kind_is_silent(self):
        self.assertEqual(run_sqf(ACOUSTIC_SOURCE, [""]), 0)
        self.assertEqual(run_sqf(ACOUSTIC_SOURCE, ["warp"]), 0)

    def test_the_loudness_order_holds(self):
        self.assertGreater(
            run_sqf(ACOUSTIC_SOURCE, ["explosion"]),
            run_sqf(ACOUSTIC_SOURCE, ["gunshot"]),
        )
        self.assertGreater(
            run_sqf(ACOUSTIC_SOURCE, ["vehicle"]),
            run_sqf(ACOUSTIC_SOURCE, ["footstep"]),
        )


class TestAcousticBus(unittest.TestCase):
    """fnc_acousticPublish and fnc_acousticSample run from the real SQF."""

    def publish(self, events, now, pos=(0, 0, 0), db=160, kind="gunshot"):
        return run_sqf(
            ACOUSTIC_PUBLISH,
            [events, list(pos), db, kind, now],
            globals_=ACOUSTIC_GLOBALS,
        )

    def test_a_new_event_is_appended(self):
        bus = self.publish([], 10)
        self.assertEqual(len(bus), 1)
        self.assertEqual(bus[0][2], "gunshot")

    def test_a_stale_event_is_dropped(self):
        bus = self.publish([], 10)
        bus = self.publish(bus, 20)
        self.assertEqual(len(bus), 1)
        self.assertEqual(bus[0][3], 20)

    def test_the_bus_is_capped_keeping_the_newest(self):
        bus = []
        for i in range(200):
            bus = self.publish(bus, i * 0.01)
        self.assertEqual(len(bus), ACOUSTIC_GLOBALS["WILDLIFE_ACOUSTIC_EVENT_CAP"])

    def test_the_strongest_event_is_returned(self):
        bus = self.publish([], 10, pos=(100, 0, 0), db=160, kind="gunshot")
        bus = self.publish(bus, 10, pos=(10, 0, 0), db=100, kind="vehicle")
        level, kind = run_sqf(
            ACOUSTIC_SAMPLE,
            [bus, [0, 0, 0], 10, 3, 1.0, []],
            globals_=ACOUSTIC_GLOBALS,
        )
        self.assertEqual(kind, "gunshot")
        self.assertGreater(level, 0)

    def test_a_stale_event_is_ignored(self):
        bus = self.publish([], 0)
        level, _kind = run_sqf(
            ACOUSTIC_SAMPLE,
            [bus, [0, 0, 0], 100, 3, 1.0, []],
            globals_=ACOUSTIC_GLOBALS,
        )
        self.assertEqual(level, 0)

    def test_an_empty_bus_is_silent(self):
        level, kind = run_sqf(
            ACOUSTIC_SAMPLE,
            [[], [0, 0, 0], 10, 3, 1.0, []],
            globals_=ACOUSTIC_GLOBALS,
        )
        self.assertEqual(level, 0)
        self.assertEqual(kind, "")


class TestAcousticSourceContracts(unittest.TestCase):
    def _pure(self, path):
        code = re.sub(
            r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_kernels_are_pure(self):
        for path in (ACOUSTIC, ACOUSTIC_SOURCE, ACOUSTIC_PUBLISH, ACOUSTIC_SAMPLE):
            self._pure(path)

    def test_the_kernels_are_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        for name in (
            "acousticLevel",
            "acousticSourceDb",
            "acousticPublish",
            "acousticSample",
            "acousticOccluders",
        ):
            self.assertIn(f"PREP({name})", text, name)

    def test_the_constants_are_declared(self):
        text = (WILDLIFE / "script_component.hpp").read_text(encoding="utf-8")
        for name in (
            "WILDLIFE_ACOUSTIC_EVENT_CAP",
            "WILDLIFE_ACOUSTIC_OCCLUSION_DB",
            "WILDLIFE_ACOUSTIC_HEARING_FLOOR_DB",
            "WILDLIFE_SPOOK_ACOUSTIC_MIN",
        ):
            self.assertIn(name, text, name)

    def test_the_fired_handler_propagates_a_source_level(self):
        text = (FUNCS / "fnc_initWildlife.sqf").read_text(encoding="utf-8")
        self.assertIn("FUNC(acousticPublish)", text)
        self.assertIn("FUNC(acousticSourceDb)", text)
        # The old fixed magnitude report is removed.
        self.assertNotIn("[getPos _unit, 1] call EFUNC(ai,reportStimulus)", text)

    def test_the_tick_consumes_the_propagated_level(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("FUNC(acousticSample)", text)
        self.assertIn("FUNC(acousticOccluders)", text)
        self.assertIn("currentSoundPropagation", text)
        self.assertIn("_acousticLevel > WILDLIFE_SPOOK_ACOUSTIC_MIN", text)

    def test_the_event_kinds_are_covered(self):
        text = (FUNCS / "fnc_initWildlife.sqf").read_text(encoding="utf-8")
        tick = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn('"explosion"', text)
        self.assertIn('"footstep"', tick)
        self.assertIn('"vehicle"', tick)
        self.assertIn('"aircraft"', tick)


PERCEIVE_ENV = [0.5, [], 0, 0, 10]
PERCEIVE_SPECIES = [1, 0.4, 0.6, 1]


def perceive(
    habitat, state, heard=None, environment=PERCEIVE_ENV, species=PERCEIVE_SPECIES
):
    if heard is None:
        heard = []
    return run_sqf(PERCEIVE, [environment, habitat, species, state, heard])


class TestWildlifePerceive(unittest.TestCase):
    """fnc_wildlifePerceive runs from the real SQF."""

    def test_a_high_threat_is_a_high_threat(self):
        out = perceive(0.9, [0.1, 0.1, 0.9, 5, [0, 0, 0], 0])
        self.assertEqual(out[1], 0.9)

    def test_hunger_above_the_threshold_gives_need(self):
        out = perceive(0.9, [0.8, 0.1, 0, 5, [0, 0, 0], 0])
        self.assertGreater(out[2][0], 0)
        self.assertEqual(out[2][1], 0)

    def test_hunger_below_the_threshold_gives_no_need(self):
        out = perceive(0.9, [0.2, 0.1, 0, 5, [0, 0, 0], 0])
        self.assertEqual(out[2][0], 0)

    def test_a_decoded_alarm_raises_threat(self):
        quiet = perceive(0.9, [0.1, 0.1, 0, 5, [0, 0, 0], 0])
        alarmed = perceive(0.9, [0.1, 0.1, 0, 5, [0, 0, 0], 0], heard=["alarm", 0.8])
        self.assertGreater(alarmed[1], quiet[1])

    def test_a_loud_acoustic_level_raises_threat(self):
        quiet = perceive(0.9, [0.1, 0.1, 0, 5, [0, 0, 0], 0.1])
        loud = perceive(0.9, [0.1, 0.1, 0, 5, [0, 0, 0], 0.9])
        self.assertGreater(loud[1], quiet[1])
        self.assertEqual(quiet[1], 0.1)

    def test_no_environment_gives_zero_suitability(self):
        out = perceive(0.9, [0.1, 0.1, 0, 5, [0, 0, 0], 0], environment=[])
        self.assertEqual(out[0], 0)

    def test_the_heard_call_is_passed_through(self):
        out = perceive(0.9, [0.1, 0.1, 0, 5, [0, 0, 0], 0], heard=["contact", 0.4])
        self.assertEqual(out[3], ["contact", 0.4])

    def test_identical_inputs_are_identical(self):
        state = [0.5, 0.5, 0.5, 5, [0, 0, 0], 0.5]
        self.assertEqual(perceive(0.9, state), perceive(0.9, state))


class TestPerceiveSourceContracts(unittest.TestCase):
    def test_the_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/", "", PERCEIVE.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_kernel_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(wildlifePerceive)", text)

    def test_the_acoustic_level_feeds_the_threat(self):
        code = PERCEIVE.read_text(encoding="utf-8")
        self.assertIn("acoustic", code.lower())


THINK_SPECIES = [0.0]
THINK_THRESHOLDS = [0.7, 0.3, 0.5, 0.2, 0.3]


def think(perception, species=THINK_SPECIES, thresholds=THINK_THRESHOLDS):
    return run_sqf(THINK, [perception, species, thresholds])


class TestWildlifeThink(unittest.TestCase):
    """fnc_wildlifeThink runs from the real SQF."""

    def test_threat_above_flee_gives_flee(self):
        out = think([0.9, 0.9, [0, 0], []])
        self.assertEqual(out[0], 3)
        self.assertEqual(out[1], "alarm")
        self.assertEqual(out[2], 2)

    def test_thirst_before_hunger(self):
        out = think([0.9, 0.1, [0.5, 0.9], []])
        self.assertEqual(out[0], 2)
        self.assertEqual(out[2], 1)

    def test_hunger_drinks_only_after_thirst(self):
        out = think([0.9, 0.1, [0.8, 0.1], []])
        self.assertEqual(out[0], 1)

    def test_a_mid_threat_freezes(self):
        out = think([0.9, 0.5, [0, 0], []])
        self.assertEqual(out[0], 4)

    def test_low_suitability_avoids(self):
        out = think([0.1, 0.1, [0, 0], []])
        self.assertEqual(out[2], 2)

    def test_a_gregarious_rest_gives_contact(self):
        out = think([0.9, 0.1, [0, 0], []], species=[0.8])
        self.assertEqual(out[1], "contact")

    def test_the_thresholds_are_arguments(self):
        # A very low flee threshold flees on a mild threat.
        out = think([0.9, 0.2, [0, 0], []], thresholds=[0.1, 0.05, 0.5, 0.2, 0.3])
        self.assertEqual(out[0], 3)

    def test_determinism(self):
        perception = [0.5, 0.5, [0.5, 0.5], []]
        self.assertEqual(think(perception), think(perception))


class TestThinkSourceContracts(unittest.TestCase):
    def test_the_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/", "", THINK.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_kernel_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(wildlifeThink)", text)

    def test_the_header_states_the_a_life_shape(self):
        code = THINK.read_text(encoding="utf-8")
        self.assertIn("A-Life", code)
        self.assertIn("sense-think-act", code)


CALL_EMIT = FUNCS / "fnc_callEmit.sqf"


def emit(species, perception, state, trigger):
    return run_sqf(CALL_EMIT, [species, perception, state, trigger])


class TestCallEmit(unittest.TestCase):
    """fnc_callEmit runs from the real SQF."""

    def test_a_perceived_predator_emits_a_high_alarm(self):
        out = emit(
            [0.5, True], [0.9, 0.9, [0, 0], []], [0.1, 0.1, 0.9, 5, 0, 0], "predator"
        )
        self.assertEqual(out[0], "alarm")
        self.assertGreater(out[1], 0.5)

    def test_a_gregarious_group_emits_a_contact(self):
        out = emit(
            [0.9, False], [0.9, 0.1, [0, 0], []], [0.1, 0.1, 0.1, 5, 0, 0], "cohesion"
        )
        self.assertEqual(out[0], "contact")
        self.assertGreater(out[1], 0)

    def test_a_solitary_group_does_not_emit_a_contact(self):
        out = emit(
            [0.2, False], [0.9, 0.1, [0, 0], []], [0.1, 0.1, 0.1, 5, 0, 0], "cohesion"
        )
        self.assertEqual(out, [])

    def test_an_active_season_emits_mating(self):
        out = emit(
            [0.5, True], [0.9, 0.1, [0, 0], []], [0.1, 0.1, 0.1, 5, 0, 0], "season"
        )
        self.assertEqual(out[0], "mating")

    def test_an_inactive_season_emits_nothing(self):
        out = emit(
            [0.5, False], [0.9, 0.1, [0, 0], []], [0.1, 0.1, 0.1, 5, 0, 0], "season"
        )
        self.assertEqual(out, [])

    def test_a_heard_conspecific_emits_territorial(self):
        out = emit(
            [0.5, False],
            [0.9, 0.5, [0, 0], []],
            [0.1, 0.1, 0.5, 5, 0, 0],
            "conspecific",
        )
        self.assertEqual(out[0], "territorial")

    def test_a_resource_emits_food(self):
        out = emit(
            [0.5, False], [0.9, 0.1, [0, 0], []], [0.1, 0.1, 0.1, 5, 0, 0], "resource"
        )
        self.assertEqual(out[0], "food")

    def test_no_trigger_emits_no_call(self):
        self.assertEqual(
            emit([0.5, True], [0.9, 0.9, [0, 0], []], [0.1, 0.1, 0.9, 5, 0, 0], ""), []
        )

    def test_an_unknown_trigger_emits_no_call(self):
        self.assertEqual(
            emit([0.5, True], [0.9, 0.9, [0, 0], []], [0.1, 0.1, 0.9, 5, 0, 0], "warp"),
            [],
        )

    def test_the_urgency_is_bounded(self):
        out = emit([1.0, True], [1.0, 1.0, [0, 0], []], [0, 0, 1, 5, 0, 0], "predator")
        self.assertLessEqual(out[1], 1)
        self.assertGreaterEqual(out[1], 0)

    def test_same_inputs_are_deterministic(self):
        args = [
            [0.5, True],
            [0.9, 0.9, [0, 0], []],
            [0.1, 0.1, 0.9, 5, 0, 0],
            "predator",
        ]
        self.assertEqual(emit(*args), emit(*args))


class TestCallEmitSourceContracts(unittest.TestCase):
    def test_the_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/", "", CALL_EMIT.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_kernel_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(callEmit)", text)

    def test_the_emit_header_states_conditional_emission(self):
        code = CALL_EMIT.read_text(encoding="utf-8")
        self.assertIn("no trigger means no call", code)


CALL_RECEIVE = FUNCS / "fnc_callReceive.sqf"


def receive(call_type, urgency, distance, relation, receiver_state):
    return run_sqf(
        CALL_RECEIVE,
        [call_type, urgency, distance, relation, receiver_state],
    )


class TestCallReceive(unittest.TestCase):
    """fnc_callReceive runs from the real SQF."""

    def test_a_conspecific_alarm_flees_or_gathers(self):
        response = receive("alarm", 0.9, 20, 0, [200, 0.2])[0]
        self.assertIn(response, (2, 3))

    def test_a_gregarious_conspecific_alarm_gathers(self):
        self.assertEqual(receive("alarm", 0.9, 20, 0, [200, 0.9])[0], 3)

    def test_a_neutral_relation_ignores_the_alarm(self):
        self.assertEqual(receive("alarm", 0.9, 20, 3, [200, 0.5]), [0, 0])

    def test_a_neutral_relation_ignores_a_contact(self):
        self.assertEqual(receive("contact", 0.9, 20, 3, [200, 0.5]), [0, 0])

    def test_a_prey_flees_and_a_predator_investigates(self):
        self.assertEqual(receive("alarm", 0.9, 20, 2, [200, 0.2])[0], 2)
        self.assertEqual(receive("alarm", 0.9, 20, 1, [200, 0.2])[0], 5)

    def test_a_territorial_call_draws_a_reply(self):
        self.assertEqual(receive("territorial", 0.5, 20, 0, [200, 0.5])[0], 4)

    def test_an_urgent_alarm_is_stronger_than_a_low_one(self):
        high = receive("alarm", 0.9, 20, 0, [200, 0.2])[1]
        low = receive("alarm", 0.1, 20, 0, [200, 0.2])[1]
        self.assertGreater(high, low)

    def test_a_call_beyond_range_is_ignored(self):
        self.assertEqual(receive("alarm", 0.9, 500, 0, [200, 0.5]), [0, 0])

    def test_distance_attenuates_the_strength(self):
        near = receive("alarm", 0.9, 10, 0, [200, 0.2])[1]
        far = receive("alarm", 0.9, 150, 0, [200, 0.2])[1]
        self.assertGreater(near, far)

    def test_an_empty_type_is_ignored(self):
        self.assertEqual(receive("", 0.9, 20, 0, [200, 0.5]), [0, 0])

    def test_same_inputs_are_deterministic(self):
        args = ["alarm", 0.9, 20, 0, [200, 0.2]]
        self.assertEqual(receive(*args), receive(*args))


class TestCallReceiveSourceContracts(unittest.TestCase):
    def test_the_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/", "", CALL_RECEIVE.read_text(encoding="utf-8"), flags=re.DOTALL
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_kernel_is_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(callReceive)", text)

    def test_the_receive_header_states_the_relation_rule(self):
        code = CALL_RECEIVE.read_text(encoding="utf-8")
        self.assertIn("neutral relation does not decode", code)


ECOLOGY_BUDGET = FUNCS / "fnc_ecologyBudget.sqf"
ECOLOGY_TICK = FUNCS / "fnc_ecologyTick.sqf"


class TestEcologyBudget(unittest.TestCase):
    """fnc_ecologyBudget runs from the real SQF."""

    def test_the_first_animal_is_always_allowed(self):
        self.assertTrue(run_sqf(ECOLOGY_BUDGET, [0, 1, 1000, 0]))

    def test_the_count_budget_stops_the_sweep(self):
        self.assertTrue(run_sqf(ECOLOGY_BUDGET, [1, 2, 0, 100]))
        self.assertFalse(run_sqf(ECOLOGY_BUDGET, [2, 2, 0, 100]))

    def test_the_millisecond_budget_stops_the_sweep(self):
        self.assertTrue(run_sqf(ECOLOGY_BUDGET, [1, 100, 0, 1]))
        self.assertFalse(run_sqf(ECOLOGY_BUDGET, [1, 100, 5, 1]))

    def test_a_zero_ms_budget_completes_over_several_calls(self):
        # 40 agents, 0 ms budget: each call solves at least one, so no agent
        # is skipped.
        total = 40
        solved = 0
        calls = 0
        while (solved < total) and (calls < 100):
            processed = 0
            while ((solved + processed) < total) and run_sqf(
                ECOLOGY_BUDGET, [processed, total, 0, 0]
            ):
                processed += 1
            solved += processed
            calls += 1
        self.assertEqual(solved, total)
        self.assertGreater(calls, 1)

    def test_same_inputs_are_deterministic(self):
        self.assertEqual(
            run_sqf(ECOLOGY_BUDGET, [1, 3, 0, 1]),
            run_sqf(ECOLOGY_BUDGET, [1, 3, 0, 1]),
        )


class TestEcologyTickSourceContracts(unittest.TestCase):
    def test_the_budget_kernel_is_pure(self):
        code = re.sub(
            r"/\*.*?\*/",
            "",
            ECOLOGY_BUDGET.read_text(encoding="utf-8"),
            flags=re.DOTALL,
        )
        code = re.sub(r"//[^\n]*", "", code)
        for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
            self.assertNotIn(banned, code, banned)

    def test_the_kernels_are_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        for name in ("ecologyBudget", "ecologyTick"):
            self.assertIn(f"PREP({name})", text, name)

    def test_the_tick_requeues_the_remainder_at_the_front(self):
        code = ECOLOGY_TICK.read_text(encoding="utf-8")
        self.assertIn("_remainder = _pending select [_i]", code)
        self.assertIn(
            "missionNamespace setVariable [QGVAR(ecologyPending), _remainder]", code
        )

    def test_the_tick_runs_perceive_think_and_the_callback(self):
        code = ECOLOGY_TICK.read_text(encoding="utf-8")
        self.assertIn("call FUNC(wildlifePerceive)", code)
        self.assertIn("call FUNC(wildlifeThink)", code)
        self.assertIn("call _callback", code)

    def test_the_tick_is_gated_on_cognition(self):
        code = ECOLOGY_TICK.read_text(encoding="utf-8")
        self.assertIn("QGVAR(cognitionEnabled)", code)
        self.assertIn("setVariable [QEGVAR(ai,ecologyDriven), nil]", code)

    def test_the_substrate_skips_an_ecology_driven_agent(self):
        code = (ROOT / "addons" / "ai" / "functions" / "fnc_aiTick.sqf").read_text(
            encoding="utf-8"
        )
        self.assertIn("QGVAR(ecologyDriven)", code)
        self.assertIn("continue", code)

    def test_the_callback_consumes_the_plan_and_the_call_kernels(self):
        code = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("_plan", code)
        self.assertIn("call FUNC(callEmit)", code)
        self.assertIn("call FUNC(callReceive)", code)


CALL_PUBLISH = FUNCS / "fnc_callPublish.sqf"
CALL_SAMPLE = FUNCS / "fnc_callSample.sqf"

CALL_GLOBALS = {
    "WILDLIFE_CALL_HORIZON": 120,
    "WILDLIFE_CALL_BUDGET": 256,
}


def bus_publish(bus, key=(0, 0), call_type="alarm", urgency=0.9, species="bird", now=0):
    return run_sqf(
        CALL_PUBLISH,
        [bus, list(key), call_type, urgency, species, now],
        globals_=CALL_GLOBALS,
    )


def bus_sample(bus, key=(0, 0), now=0):
    return run_sqf(CALL_SAMPLE, [bus, list(key), now], globals_=CALL_GLOBALS)


class TestCallBus(unittest.TestCase):
    """fnc_callPublish and fnc_callSample run from the real SQF."""

    def test_a_published_call_is_appended(self):
        bus = bus_publish([])
        self.assertEqual(len(bus), 1)
        self.assertEqual(bus[0][1], "alarm")

    def test_the_bus_never_exceeds_its_cap(self):
        bus = []
        for i in range(400):
            bus = bus_publish(bus, urgency=(i % 10) / 10.0, now=i * 0.001)
        self.assertLessEqual(len(bus), CALL_GLOBALS["WILDLIFE_CALL_BUDGET"])

    def test_an_expired_call_is_dropped_on_publish(self):
        bus = bus_publish([], now=0)
        bus = bus_publish(bus, call_type="contact", now=200)
        types = [row[1] for row in bus]
        self.assertNotIn("alarm", types)

    def test_an_expired_call_is_never_sampled(self):
        bus = bus_publish([], now=0)
        self.assertEqual(bus_sample(bus, now=500), [])

    def test_a_live_call_is_sampled_at_its_cell(self):
        bus = bus_publish([], key=(0, 0), call_type="alarm", urgency=0.9, now=10)
        self.assertEqual(bus_sample(bus, key=(0, 0), now=10)[0], "alarm")

    def test_a_call_at_another_cell_is_not_sampled(self):
        bus = bus_publish([], key=(0, 0), now=10)
        self.assertEqual(bus_sample(bus, key=(5, 5), now=10), [])

    def test_the_strongest_live_call_is_returned(self):
        bus = bus_publish([], key=(0, 0), call_type="contact", urgency=0.1, now=10)
        bus = bus_publish(bus, key=(0, 0), call_type="alarm", urgency=0.9, now=10)
        self.assertEqual(bus_sample(bus, key=(0, 0), now=10)[0], "alarm")

    def test_an_empty_bus_is_silent(self):
        self.assertEqual(bus_sample([], now=0), [])

    def test_same_inputs_are_deterministic(self):
        self.assertEqual(bus_publish([], now=10), bus_publish([], now=10))
        bus = bus_publish([], now=10)
        self.assertEqual(bus_sample(bus, now=10), bus_sample(bus, now=10))

    def test_a_published_alarm_is_decoded_by_a_conspecific(self):
        bus = bus_publish([], key=(0, 0), call_type="alarm", urgency=0.9, now=10)
        call = bus_sample(bus, key=(0, 0), now=10)
        reaction = receive(call[0], call[1], 0, 0, [200, 0.2])
        self.assertIn(reaction[0], (2, 3))


class TestCallBusSourceContracts(unittest.TestCase):
    def test_the_kernels_are_pure(self):
        for path in (CALL_PUBLISH, CALL_SAMPLE):
            code = re.sub(
                r"/\*.*?\*/", "", path.read_text(encoding="utf-8"), flags=re.DOTALL
            )
            code = re.sub(r"//[^\n]*", "", code)
            for banned in ("missionNamespace", "GVAR(", "random", "diag_"):
                self.assertNotIn(banned, code, banned)

    def test_the_kernels_are_prepped(self):
        text = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        for name in ("callPublish", "callSample"):
            self.assertIn(f"PREP({name})", text, name)

    def test_the_tick_samples_the_bus(self):
        code = ECOLOGY_TICK.read_text(encoding="utf-8")
        self.assertIn("call FUNC(callSample)", code)
        self.assertIn("QGVAR(communicationEnabled)", code)

    def test_the_callback_publishes_the_bus(self):
        code = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("call FUNC(callPublish)", code)
        self.assertIn("QGVAR(callBus)", code)


if __name__ == "__main__":
    unittest.main()
