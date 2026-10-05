#!/usr/bin/env python3
"""Wildlife ecology kernel and source-contract tests.

The pure kernels run from their real SQF through tools/tests/sqf_lite.py, so a
test failure is a source failure, not a mirror drift.  The source contracts
read the engine wiring, which the harness cannot execute.

Run: python3 -m unittest tools.tests.test_wildlife -v
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
MANIFEST = DATA / "sound_manifest.sqf"
SPECIES_TABLE = DATA / "species_table.sqf"

SPECIES_FOR_BIOME = FUNCS / "fnc_speciesForBiome.sqf"
SPAWN_BUDGET = FUNCS / "fnc_spawnBudget.sqf"
NEEDS_TICK = FUNCS / "fnc_needsTick.sqf"
RESOURCE_SCORE = FUNCS / "fnc_resourceScore.sqf"
PICK_RESOURCE = FUNCS / "fnc_pickResourceTarget.sqf"
SOUND_BED = FUNCS / "fnc_soundBedForContext.sqf"
SPOOK_RANGE = FUNCS / "fnc_spookRange.sqf"
DISTURBANCE_SILENCE = FUNCS / "fnc_disturbanceSilence.sqf"

# A tiny manifest for the pure kernel tests.  The real manifest has the same
# row shape.
TEST_MANIFEST = [
    ["water", "Sound_Stream", 120, 0.8],
    ["night", "Owl", 120, 0.6],
    ["day_temperate", "a3\\sounds_f\\ambient\\animals\\birds1.wss", 120, 0.7],
    ["day_arid", "a3\\sounds_f\\ambient\\animals\\birds3.wss", 120, 0.5],
]


def sound_bed(biome, is_night, near_water, wind, disturbance, manifest=None, rain=0):
    if manifest is None:
        manifest = TEST_MANIFEST
    return run_sqf(
        SOUND_BED, [biome, is_night, near_water, wind, disturbance, manifest, rain]
    )


def spook_range(magnitude, sensitivity, base_range):
    return run_sqf(SPOOK_RANGE, [magnitude, sensitivity, base_range])


def disturbance_silence(disturbance, decay):
    return run_sqf(DISTURBANCE_SILENCE, [disturbance, decay])


# The only CfgSFX classes the manifest may name.  Each is a confirmed vanilla
# class (BIKI CfgSFX).  A new class here needs a dossier citation.
ALLOWED_CFGSFX = {"Owl", "Sound_Stream"}
ALLOWED_EXTENSIONS = {".wss", ".ogg", ".wav"}


def load_manifest():
    """The manifest rows from the real data file."""
    return run_sqf(MANIFEST, [])


class TestSoundManifest(unittest.TestCase):
    """The vanilla sound manifest carries no third-party media."""

    def test_manifest_is_a_non_empty_list_of_four_element_rows(self):
        rows = load_manifest()
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)
        for row in rows:
            self.assertEqual(len(row), 4, f"bad manifest row: {row}")

    def test_every_source_is_a_vanilla_path_or_a_listed_cfg_sfx_class(self):
        for key, source, _distance, _gain in load_manifest():
            self.assertIsInstance(key, str)
            self.assertNotEqual(key, "")
            self.assertIsInstance(source, str)
            if "." in source:
                self.assertTrue(
                    source.lower().startswith("a3\\"),
                    f"non-vanilla path: {source}",
                )
            else:
                self.assertIn(
                    source,
                    ALLOWED_CFGSFX,
                    f"unlisted CfgSFX class: {source}",
                )

    def test_no_third_party_prefix_and_only_known_media_extensions(self):
        for _key, source, _distance, _gain in load_manifest():
            self.assertFalse(
                source.lower().startswith(("x\\", "z\\")),
                f"third-party prefix: {source}",
            )
            if "." in source:
                extension = source[source.rfind(".") :].lower()
                self.assertIn(
                    extension,
                    ALLOWED_EXTENSIONS,
                    f"unexpected media extension: {source}",
                )

    def test_every_distance_and_gain_is_a_number(self):
        for row in load_manifest():
            self.assertIsInstance(row[2], (int, float))
            self.assertIsInstance(row[3], (int, float))
            self.assertGreater(row[2], 0)
            self.assertGreater(row[3], 0)


class TestSoundBedForContext(unittest.TestCase):
    """fnc_soundBedForContext runs from the real SQF."""

    def test_water_wins_over_night_and_day(self):
        key, _gain = sound_bed("Cfb", True, 0.9, 0, 0)
        self.assertEqual(key, "water")

    def test_night_wins_when_water_is_absent(self):
        key, _gain = sound_bed("Cfb", True, 0.1, 0, 0)
        self.assertEqual(key, "night")

    def test_day_when_neither_water_nor_night(self):
        key, _gain = sound_bed("Cfb", False, 0.1, 0, 0)
        self.assertTrue(key.startswith("day"), key)

    def test_biome_family_selects_the_day_key(self):
        self.assertEqual(sound_bed("BWh", False, 0, 0, 0)[0], "day_arid")
        self.assertEqual(sound_bed("Af", False, 0, 0, 0)[0], "day_tropical")
        self.assertEqual(sound_bed("Dfb", False, 0, 0, 0)[0], "day_cold")

    def test_gain_decreases_as_disturbance_rises(self):
        _key, quiet = sound_bed("Cfb", False, 0, 0, 0.0)
        _key, loud = sound_bed("Cfb", False, 0, 0, 0.8)
        self.assertLess(loud, quiet)

    def test_gain_rises_with_rain(self):
        _key, dry = sound_bed("Cfb", False, 0, 0, 0.0, rain=0.0)
        _key, wet = sound_bed("Cfb", False, 0, 0, 0.0, rain=1.0)
        self.assertGreater(wet, dry)


class TestSpookRange(unittest.TestCase):
    """fnc_spookRange runs from the real SQF."""

    def test_range_doubles_with_the_base_range(self):
        single = spook_range(0.5, 1, 10)
        double = spook_range(0.5, 1, 20)
        self.assertAlmostEqual(double, single * 2)

    def test_zero_base_range_is_zero(self):
        self.assertEqual(spook_range(0.5, 1, 0), 0)

    def test_magnitude_clamps_at_zero(self):
        self.assertAlmostEqual(spook_range(-3, 1, 20), spook_range(0, 1, 20))

    def test_sensitivity_scales_the_range(self):
        self.assertAlmostEqual(spook_range(0.5, 2, 20), spook_range(0.5, 1, 20) * 2)


class TestDisturbanceSilence(unittest.TestCase):
    """fnc_disturbanceSilence runs from the real SQF."""

    def test_zero_disturbance_is_full_gain(self):
        self.assertAlmostEqual(disturbance_silence(0, 0.05), 1.0)

    def test_full_disturbance_is_silent(self):
        self.assertAlmostEqual(disturbance_silence(1, 0.05), 0.0)

    def test_mid_disturbance_sits_between(self):
        value = disturbance_silence(0.5, 0.05)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)


def pick_target(pos, want_water, search_radius, step, water_fn, veg_fn):
    """Run fnc_pickResourceTarget with stub water and vegetation providers."""
    return run_sqf(
        PICK_RESOURCE,
        [pos, want_water, search_radius, step, water_fn, veg_fn],
        globals_={
            "__FUNC__resourceScore": lambda d, w, v, ww: run_sqf(
                RESOURCE_SCORE, [d, w, v, ww]
            )
        },
    )


class TestPickResourceTarget(unittest.TestCase):
    """fnc_pickResourceTarget runs from the real SQF with stub providers."""

    @staticmethod
    def zero(_point):
        return 0.0

    def test_want_water_picks_a_water_side_point(self):
        result = pick_target(
            [0, 0, 0],
            True,
            100,
            25,
            lambda point: 1.0 if point[0] > 0 else 0.0,
            self.zero,
        )
        self.assertGreater(result[0], 0)

    def test_food_picks_a_vegetation_side_point(self):
        result = pick_target(
            [0, 0, 0],
            False,
            100,
            25,
            self.zero,
            lambda point: 1.0 if point[1] > 0 else 0.0,
        )
        self.assertGreater(result[1], 0)

    def test_no_resource_returns_the_origin(self):
        result = pick_target([0, 0, 0], True, 100, 25, self.zero, self.zero)
        self.assertEqual(result, [0, 0, 0])


class TestFaunaSourceContracts(unittest.TestCase):
    """The fauna engine wiring the harness cannot execute."""

    def test_behaviour_uses_the_resource_target(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("pickResourceTarget", text)

    def test_resource_providers_use_the_published_facts(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("EFUNC(environmental,getCoastDistance)", text)
        self.assertIn("QEGVAR(environmental,terrainSignals)", text)

    def test_herd_anchor_is_recorded_and_leashed(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("herdAnchor", text)
        self.assertIn("herds", text)

    def test_spawn_uses_create_agent(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("createAgent", text)

    def test_spawn_sets_the_animal_behaviour_disable_flag(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("BIS_fnc_animalBehaviour_disable", text)

    def test_spawn_requires_has_interface_and_a_local_unit(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("hasInterface", text)
        self.assertIn("CBA_fnc_currentUnit", text)

    def test_spawn_gates_on_the_fauna_switch(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("animalsEnabled", text)

    def test_behaviour_registers_with_the_substrate(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("agentRegister", text)
        self.assertIn("moveTo", text)
        self.assertIn("setDestination", text)

    def test_cull_deletes_beyond_the_despawn_radius(self):
        text = (FUNCS / "fnc_cullFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("deleteVehicle", text)
        self.assertIn("despawnRadius", text)

    def test_fauna_honours_the_force_species_hook(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("aee_wildlife_forceSpecies", text)

    def test_wildlife_tick_wires_the_fauna_driver(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("spawnFauna", text)
        self.assertIn("cullFauna", text)


class TestWildlifeSourceContracts(unittest.TestCase):
    """The engine wiring the harness cannot execute."""

    def test_every_play_sound_3d_sets_the_local_argument_true(self):
        calls = 0
        for path in WILDLIFE.rglob("*.sqf"):
            text = path.read_text(encoding="utf-8")
            for match in re.findall(r"playSound3D\s*\[([^\]]*)\]", text):
                calls += 1
                arguments = [part.strip() for part in match.split(",")]
                self.assertEqual(
                    arguments[-1],
                    "true",
                    f"{path.name} does not set playSound3D local true",
                )
        self.assertGreaterEqual(calls, 1)

    def test_cfg_sfx_bed_uses_the_client_local_sound_source(self):
        text = (FUNCS / "fnc_playAmbientBed.sqf").read_text(encoding="utf-8")
        match = re.search(r"createSoundSourceLocal\s*\[(.*?)\]\s*;", text, re.DOTALL)
        self.assertIsNotNone(match, "no createSoundSourceLocal call in the bed")
        arguments = [part.strip() for part in match.group(1).split(",")]
        self.assertEqual(len(arguments), 4, match.group(0))

    def test_no_network_global_sound_source_under_wildlife(self):
        pattern = re.compile(r"\bcreateSoundSource\b")
        for path in WILDLIFE.rglob("*.sqf"):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(
                pattern.search(text),
                f"{path.name} uses the network-global createSoundSource",
            )

    def test_the_bed_is_deleted_before_recreation(self):
        text = (FUNCS / "fnc_playAmbientBed.sqf").read_text(encoding="utf-8")
        self.assertIn("deleteVehicle", text)
        self.assertLess(
            text.index("deleteVehicle"),
            text.index("createSoundSourceLocal"),
            "the previous bed is not deleted before the new local source",
        )

    def test_init_wildlife_gates_on_has_interface(self):
        text = (FUNCS / "fnc_initWildlife.sqf").read_text(encoding="utf-8")
        self.assertIn("hasInterface", text)

    def test_wildlife_tick_gates_on_has_interface_and_a_local_unit(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("hasInterface", text)
        self.assertIn("CBA_fnc_currentUnit", text)

    def test_tick_reads_rain_and_the_soil_facts(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("rain", text)
        self.assertIn("soilMoisture", text)
        self.assertIn("surfaceWetness", text)

    def test_tick_senses_nearby_units_and_stance(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("nearEntities", text)
        self.assertIn("stance", text)

    def test_spawn_reads_the_biome_through_the_guarded_helper(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("EFUNC(core,readState)", text)

    def test_dry_run_is_the_last_tick_parameter(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        block = text[text.index("params [") : text.index("];", text.index("params ["))]
        self.assertLess(block.index("_anchor"), block.index("_dryRun"))
        self.assertIn("[false]", block)

    def test_no_object_creation_and_no_do_move(self):
        forbidden = ("createVehicle", "createVehicleLocal", "doMove", "doStop")
        for path in WILDLIFE.rglob("*.sqf"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path.name} contains {token}")

    def test_sound_instance_cap_is_enforced(self):
        text = (FUNCS / "fnc_playOneShot.sqf").read_text(encoding="utf-8")
        self.assertIn("WILDLIFE_SOUND_INSTANCE_CAP", text)


class TestSoundBedDeterminism(unittest.TestCase):
    """Two identical inputs give the same mix, and one change moves it."""

    def test_same_inputs_give_the_same_result(self):
        first = sound_bed("Cfb", False, 0.0, 2.0, 0.2)
        second = sound_bed("Cfb", False, 0.0, 2.0, 0.2)
        self.assertEqual(first, second)

    def test_a_changed_input_changes_the_result(self):
        base = sound_bed("Cfb", False, 0.0, 2.0, 0.2)
        changed = sound_bed("Cfb", False, 0.0, 2.0, 0.9)
        self.assertNotEqual(base, changed)


class TestNewAddonsLogDebugContract(unittest.TestCase):
    """The two new addons declare logDebug and both stringtable keys."""

    ADDONS = ("ai", "wildlife")

    def test_each_new_addon_declares_log_debug_and_both_keys(self):
        for name in self.ADDONS:
            with self.subTest(addon=name):
                directory = ROOT / "addons" / name
                settings = (directory / "initSettings.inc.sqf").read_text(
                    encoding="utf-8"
                )
                self.assertTrue(
                    "AEE_SETTING_CHECKBOX(logDebug," in settings
                    or "QGVAR(logDebug)," in settings,
                    f"{name} declares no logDebug switch",
                )
                strings = (directory / "stringtable.xml").read_text(encoding="utf-8")
                self.assertIn("_logDebug_Name", strings)
                self.assertIn("_logDebug_Description", strings)


# The confirmed vanilla CfgVehicles Animals classes the species table may name
# (BIKI CfgVehicles Animals, Wayback 2025-01-16).  A new class here needs a
# dossier citation.  There is no cow, no owl unit and no dolphin in vanilla.
VANILLA_ANIMAL_CLASSES = {
    "Sheep_random_F",
    "Goat_random_F",
    "Hen_random_F",
    "Cock_random_F",
    "Cock_white_F",
    "Rabbit_F",
    "Snake_random_F",
    "Snake_vipera_random_F",
    "Turtle_F",
    "Fin_sand_F",
    "Fin_blackwhite_F",
    "Fin_ocherwhite_F",
    "Fin_tricolour_F",
    "Fin_random_F",
    "Alsatian_Sand_F",
    "Alsatian_Black_F",
    "Alsatian_Sandblack_F",
    "Alsatian_Random_F",
    "Salema_F",
    "Ornate_random_F",
    "Mackerel_F",
    "Tuna_F",
    "Mullet_F",
    "CatShark_F",
}
WATER_ANIMAL_CLASSES = {
    "Turtle_F",
    "Salema_F",
    "Ornate_random_F",
    "Mackerel_F",
    "Tuna_F",
    "Mullet_F",
    "CatShark_F",
}


def load_species_table():
    """The species rows from the real data file."""
    return run_sqf(SPECIES_TABLE, [])


def species_for_biome(biome, is_night, water_frac, veg_score, seed, table):
    return run_sqf(
        SPECIES_FOR_BIOME, [biome, is_night, water_frac, veg_score, seed, table]
    )


class TestSpeciesForBiome(unittest.TestCase):
    """fnc_speciesForBiome runs from the real SQF against the real table."""

    @classmethod
    def setUpClass(cls):
        cls.TABLE = load_species_table()

    def test_table_has_the_four_families_and_two_overlays(self):
        keys = {row[0] for row in self.TABLE}
        self.assertEqual(
            keys, {"cold", "temperate", "arid", "tropical", "water", "settlement"}
        )

    def test_every_table_class_is_a_confirmed_vanilla_animal(self):
        for _family, classes in self.TABLE:
            for cls in classes:
                self.assertIn(cls, VANILLA_ANIMAL_CLASSES)

    def test_each_family_returns_only_confirmed_classes(self):
        for biome in ("Cfb", "BWh", "Af", "Dfb"):
            result = species_for_biome(biome, False, 0.0, 0.8, 7, self.TABLE)
            for cls, count in result:
                self.assertIn(cls, VANILLA_ANIMAL_CLASSES)
                self.assertGreaterEqual(count, 1)

    def test_high_water_fraction_includes_a_water_class(self):
        result = species_for_biome("Cfb", False, 0.9, 0.8, 7, self.TABLE)
        classes = {cls for cls, _count in result}
        self.assertTrue(classes & WATER_ANIMAL_CLASSES, classes)

    def test_zero_vegetation_returns_nothing(self):
        self.assertEqual(species_for_biome("Cfb", False, 0.0, 0.0, 7, self.TABLE), [])

    def test_same_seed_is_deterministic(self):
        first = species_for_biome("Cfb", False, 0.0, 0.8, 7, self.TABLE)
        second = species_for_biome("Cfb", False, 0.0, 0.8, 7, self.TABLE)
        self.assertEqual(first, second)

    def test_a_seed_step_change_moves_the_mix(self):
        base = species_for_biome("Cfb", False, 0.0, 0.8, 7, self.TABLE)
        changed = species_for_biome("Cfb", False, 0.0, 0.8, 8, self.TABLE)
        self.assertNotEqual(base, changed)

    def test_night_drops_the_farm_birds(self):
        day = {
            cls
            for cls, _count in species_for_biome("Cfb", False, 0.0, 0.8, 7, self.TABLE)
        }
        night = {
            cls
            for cls, _count in species_for_biome("Cfb", True, 0.0, 0.8, 7, self.TABLE)
        }
        self.assertIn("Hen_random_F", day)
        self.assertNotIn("Hen_random_F", night)


class TestSpawnBudget(unittest.TestCase):
    """fnc_spawnBudget runs from the real SQF."""

    @staticmethod
    def budget(distance, live_count, spawn_radius=350, despawn_radius=600, cap=16):
        return run_sqf(
            SPAWN_BUDGET,
            [distance, spawn_radius, despawn_radius, live_count, cap],
        )

    def test_spawns_inside_the_radius_with_room(self):
        allowed, should_spawn, should_despawn = self.budget(100, 0)
        self.assertTrue(should_spawn)
        self.assertFalse(should_despawn)
        self.assertEqual(allowed, 16)

    def test_no_spawn_beyond_the_spawn_radius(self):
        _allowed, should_spawn, _should_despawn = self.budget(400, 0)
        self.assertFalse(should_spawn)

    def test_no_spawn_at_the_cap(self):
        allowed, should_spawn, _should_despawn = self.budget(100, 16)
        self.assertFalse(should_spawn)
        self.assertEqual(allowed, 0)

    def test_despawns_beyond_the_despawn_radius(self):
        _allowed, should_spawn, should_despawn = self.budget(700, 4)
        self.assertTrue(should_despawn)
        self.assertFalse(should_spawn)

    def test_allowance_never_goes_negative(self):
        allowed, _should_spawn, _should_despawn = self.budget(100, 40)
        self.assertEqual(allowed, 0)


class TestNeedsTick(unittest.TestCase):
    """fnc_needsTick runs from the real SQF."""

    @staticmethod
    def needs(hunger, thirst, dt, hunger_rate=0.02, thirst_rate=0.03):
        return run_sqf(NEEDS_TICK, [hunger, thirst, dt, hunger_rate, thirst_rate])

    def test_thirst_above_its_threshold_wants_water(self):
        _h, _t, goal = self.needs(0.1, 0.9, 0)
        self.assertEqual(goal, 2)

    def test_hunger_only_wants_food(self):
        _h, _t, goal = self.needs(0.9, 0.1, 0)
        self.assertEqual(goal, 1)

    def test_both_low_want_nothing(self):
        _h, _t, goal = self.needs(0.1, 0.1, 0)
        self.assertEqual(goal, 0)

    def test_both_needs_rise_with_dt(self):
        hunger0, thirst0, _goal = self.needs(0.0, 0.0, 0)
        hunger1, thirst1, _goal = self.needs(0.0, 0.0, 10)
        self.assertGreater(hunger1, hunger0)
        self.assertGreater(thirst1, thirst0)

    def test_needs_clamp_at_one(self):
        hunger, thirst, _goal = self.needs(0.99, 0.99, 100)
        self.assertEqual(hunger, 1.0)
        self.assertEqual(thirst, 1.0)


class TestResourceScore(unittest.TestCase):
    """fnc_resourceScore runs from the real SQF."""

    @staticmethod
    def score(distance, water, veg, want_water):
        return run_sqf(RESOURCE_SCORE, [distance, water, veg, want_water])

    def test_full_wanted_resource_at_zero_distance_is_one(self):
        self.assertAlmostEqual(self.score(0, 1.0, 0.0, True), 1.0)

    def test_long_distance_is_near_zero(self):
        self.assertAlmostEqual(self.score(200, 1.0, 0.0, True), 0.0, places=6)

    def test_food_uses_the_vegetation_score(self):
        self.assertAlmostEqual(self.score(0, 0.0, 0.5, False), 0.5)

    def test_the_wanted_resource_selects_the_strength(self):
        water = self.score(0, 0.9, 0.1, True)
        food = self.score(0, 0.9, 0.1, False)
        self.assertNotEqual(water, food)


class TestWildlifeSettingsStrings(unittest.TestCase):
    """Every wildlife setting declares both stringtable keys."""

    def test_every_setting_has_both_stringtable_keys(self):
        settings = (WILDLIFE / "initSettings.inc.sqf").read_text(encoding="utf-8")
        strings = (WILDLIFE / "stringtable.xml").read_text(encoding="utf-8")
        names = re.findall(r"AEE_SETTING_\w+\(\s*(\w+)", settings)
        self.assertGreater(len(names), 0)
        for name in names:
            with self.subTest(setting=name):
                self.assertIn(f"STR_AEE_Wildlife_{name}_Name", strings)
                self.assertIn(f"STR_AEE_Wildlife_{name}_Description", strings)


if __name__ == "__main__":
    unittest.main()
