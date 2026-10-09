#!/usr/bin/env python3
"""Wildlife ecology kernel and source-contract tests.

The pure kernels run from their real SQF through tools/tests/sqf_lite.py, so a
test failure is a source failure, not a mirror drift.  The source contracts
read the engine wiring, which the harness cannot execute.

Run: python3 -m unittest tools.tests.test_wildlife -v
"""

import math
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sqf_lite import Lambda, Params, load_sqf, run_sqf  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
WILDLIFE = ROOT / "addons" / "wildlife"
FUNCS = WILDLIFE / "functions"
AMBIENCE = ROOT / "addons" / "ambience" / "functions"
DATA = WILDLIFE / "data"
MANIFEST = DATA / "sound_manifest.sqf"
SPECIES_TABLE = DATA / "species_table.sqf"

SPECIES_FOR_BIOME = FUNCS / "fnc_speciesForBiome.sqf"
SPECIES_MATCH = FUNCS / "fnc_getSpeciesMatch.sqf"
SPAWN_BUDGET = FUNCS / "fnc_spawnBudget.sqf"
NEEDS_TICK = FUNCS / "fnc_needsTick.sqf"
RESOURCE_SCORE = FUNCS / "fnc_resourceScore.sqf"
PICK_RESOURCE = FUNCS / "fnc_pickResourceTarget.sqf"
SOUND_BED = AMBIENCE / "fnc_soundBedForContext.sqf"
SPOOK_RANGE = FUNCS / "fnc_spookRange.sqf"
DISTURBANCE_SILENCE = AMBIENCE / "fnc_disturbanceSilence.sqf"
MONITOR = FUNCS / "fnc_monitorWildlife.sqf"
EMITTER_PLAN = AMBIENCE / "fnc_emitterPlan.sqf"
EMITTER_CLASS = AMBIENCE / "fnc_emitterClass.sqf"
CALL_PITCH = AMBIENCE / "fnc_callPitch.sqf"
SHOT_AUDIO = AMBIENCE / "fnc_shotAudio.sqf"

# A tiny manifest for the pure kernel tests.  The real manifest has the same
# row shape.
TEST_MANIFEST = [
    ["water", "Sound_Stream", 120, 0.8],
    ["night", "Owl", 120, 0.6],
    ["day_temperate", "a3\\sounds_f\\ambient\\animals\\birds1.wss", 120, 0.7],
    ["day_temperate_forest", "a3\\sounds_f\\ambient\\animals\\birds1.wss", 120, 0.9],
    ["day_arid", "a3\\sounds_f\\ambient\\animals\\birds3.wss", 120, 0.5],
    ["day_arid_forest", "a3\\sounds_f\\ambient\\animals\\birds3.wss", 120, 0.7],
]


def sound_bed(
    biome,
    is_night,
    near_water,
    wind,
    disturbance,
    manifest=None,
    rain=0,
    veg=0,
    settlement=0,
    coastal=False,
):
    if manifest is None:
        manifest = TEST_MANIFEST
    return run_sqf(
        SOUND_BED,
        [
            biome,
            is_night,
            near_water,
            wind,
            disturbance,
            manifest,
            rain,
            veg,
            settlement,
            coastal,
        ],
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

    def test_vegetation_selects_a_forest_context_apart_from_open_ground(self):
        # Same biome, night, water, wind and rain.  The only change is the
        # vegetation score, so any difference is the forest/open distinction.
        open_key, open_gain = sound_bed("Cfb", False, 0.1, 0, 0.0, rain=0.0, veg=0.0)
        forest_key, forest_gain = sound_bed(
            "Cfb", False, 0.1, 0, 0.0, rain=0.0, veg=1.0
        )
        self.assertNotEqual(forest_key, open_key)
        self.assertEqual(open_key, "day_temperate")
        self.assertEqual(forest_key, "day_temperate_forest")
        self.assertGreater(forest_gain, open_gain)

    def test_the_forest_key_follows_the_biome_family(self):
        self.assertEqual(
            sound_bed("BWh", False, 0, 0, 0, veg=1.0)[0], "day_arid_forest"
        )
        self.assertEqual(
            sound_bed("Dfb", False, 0, 0, 0, veg=1.0)[0], "day_cold_forest"
        )

    def test_vegetation_does_not_override_water_or_night(self):
        self.assertEqual(sound_bed("Cfb", False, 0.9, 0, 0, veg=1.0)[0], "water")
        self.assertEqual(sound_bed("Cfb", True, 0.1, 0, 0, veg=1.0)[0], "night")

    def test_below_the_vegetation_threshold_stays_open(self):
        self.assertEqual(
            sound_bed("Cfb", False, 0.1, 0, 0, veg=0.49)[0], "day_temperate"
        )


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
        self.assertIn("EFUNC(weather,getCoastDistance)", text)
        self.assertIn("QEGVAR(weather,terrainSignals)", text)

    def test_herd_anchor_is_recorded_and_leashed(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("herdAnchor", text)
        self.assertIn("herds", text)

    def test_herd_size_setting_drives_the_herd(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("QGVAR(herdSize)", text)

    def test_cull_releases_the_herd_slot(self):
        text = (FUNCS / "fnc_cullFauna.sqf").read_text(encoding="utf-8")
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
        for path in list(WILDLIFE.rglob("*.sqf")) + list(AMBIENCE.rglob("*.sqf")):
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
        text = (AMBIENCE / "fnc_playAmbientBed.sqf").read_text(encoding="utf-8")
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
        text = (AMBIENCE / "fnc_playAmbientBed.sqf").read_text(encoding="utf-8")
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

    def test_tick_reads_the_vegetation_signal_and_passes_it_to_the_bed(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("QEGVAR(weather,terrainSignals)", text)
        self.assertIn("EFUNC(lib,readState)", text)
        self.assertIn("_vegScore", text)
        # The score and the settlement and coastal overlays are appended to
        # the bed selector.
        self.assertIn("_vegScore, _settlement, _coastal", text)
        self.assertIn("call EFUNC(ambience,soundBedForContext)", text)
        kernel = (AMBIENCE / "fnc_soundBedForContext.sqf").read_text(encoding="utf-8")
        self.assertIn('["_vegScore", 0, [0]]', kernel)
        self.assertIn("_forest", kernel)

    def test_tick_senses_nearby_units_and_stance(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("nearEntities", text)
        self.assertIn("stance", text)

    def test_spawn_reads_the_biome_through_the_guarded_helper(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("EFUNC(lib,readState)", text)

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
        text = (AMBIENCE / "fnc_playOneShot.sqf").read_text(encoding="utf-8")
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


def _strip_sqf_comments(text):
    """The source with block and line comments removed, newlines kept."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", text)


class TestWildlifeStateLineContract(unittest.TestCase):
    """The consolidated state line keeps the night-sky cost pattern."""

    @classmethod
    def setUpClass(cls):
        cls.text = (FUNCS / "fnc_logWildlifeState.sqf").read_text(encoding="utf-8")
        body = _strip_sqf_comments(cls.text)
        cls.code = [
            line.strip()
            for line in body.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]

    def test_the_first_statement_is_the_trace_guard(self):
        first = self.code[0]
        self.assertTrue(first.startswith("if ("), first)
        self.assertIn("stateLogStarted", first)
        self.assertIn("exitWith", first)
        self.assertIn("AEE_TRACE_ON", first)
        self.assertIn("aee_ai_logDebug", first)

    def test_the_line_is_emitted_info_then_debug(self):
        self.assertEqual(self.text.count("AEE_LOG_INFO(_logMsg)"), 1)
        self.assertEqual(self.text.count("AEE_LOG_DEBUG(_logMsg)"), 1)
        # The first call sets the started flag and emits INFO.  Every later
        # call takes the DEBUG branch.
        started = self.text.index("setVariable [QGVAR(stateLogStarted), true]")
        guard = self.text.index("getVariable [QGVAR(stateLogStarted), false]")
        info = self.text.index("AEE_LOG_INFO(_logMsg)")
        self.assertLess(guard, info)
        self.assertLess(started, info)
        # The DEBUG line sits in the then-branch, so later calls take it.
        self.assertIn("AEE_LOG_DEBUG(_logMsg);", self.text)

    def test_the_format_carries_every_required_field(self):
        self.assertIn("private _logMsg = format [", self.text)
        for token in (
            "wildlife state |",
            "ai=agents:",
            "field=",
            "bed=",
            "fauna=",
            "sound=",
            "gates=",
            "forces=",
            "tick=",
            "fauna=%10/%11 sound=%12/%13",
            "tick=%24ms",
        ):
            self.assertIn(token, self.text)

    def test_the_line_reads_the_guarded_registries_and_gates(self):
        for token in (
            "QEGVAR(ai,agents)",
            "QEGVAR(ai,disturbance)",
            "aee_ai_forceDecide",
            "QGVAR(fauna)",
            "QGVAR(maxAnimals)",
            "QEGVAR(ambience,soundInstances)",
            "WILDLIFE_SOUND_INSTANCE_CAP",
            "QGVAR(ambientSource)",
            "QGVAR(enabled)",
            "QEGVAR(ambience,ambientEnabled)",
            "QGVAR(animalsEnabled)",
            "QGVAR(density)",
            "aee_wildlife_forceBiome",
            "aee_wildlife_forceNight",
            "aee_wildlife_forceSilence",
            "aee_wildlife_forceSpook",
            "aee_wildlife_forceSpecies",
        ):
            self.assertIn(token, self.text)

    def test_the_force_night_hook_type_is_shared_with_the_tick(self):
        # The logger and the tick accept the same hook type, so the line never
        # reports a value the tick ignored, and no Bool reaches a numeric
        # operator.
        tick = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("_forceNight isEqualType false", tick)
        self.assertIn("_forceNightHook isEqualType false", self.text)
        self.assertNotIn("isEqualTypeAny [0, false]", self.text)
        self.assertNotIn("round _forceNight", self.text)


class TestMonitorWildlifeContract(unittest.TestCase):
    """The on-demand monitor stays read-only and dry-run."""

    @classmethod
    def setUpClass(cls):
        cls.text = MONITOR.read_text(encoding="utf-8")

    def test_the_function_exists_and_is_prepped(self):
        self.assertTrue(MONITOR.is_file())
        prep = (WILDLIFE / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(monitorWildlife);", prep)

    def test_it_calls_the_wildlife_tick_with_the_dry_run_flag(self):
        self.assertIn("[[0, 0, 0], true] call FUNC(wildlifeTick)", self.text)

    def test_it_calls_the_ai_tick_with_the_dry_run_flag(self):
        self.assertIn("aee_ai_fnc_aiTick", self.text)
        self.assertIn("[true], _iters] call _measure", self.text)

    def test_it_never_plays_or_spawns(self):
        body = _strip_sqf_comments(self.text)
        for token in ("playSound3D", "createSoundSourceLocal", "createAgent"):
            self.assertNotIn(token, body, f"the monitor uses {token}")

    def test_it_prints_the_counts_and_the_gates(self):
        for token in (
            "agents=%3",
            "field=%4",
            "fauna=%5/%6",
            "sound=%7/%8",
            "gates=on=%9",
            "ambient=%10",
            "animals=%11",
            "density=%12",
        ):
            self.assertIn(token, self.text)

    def test_it_returns_the_prefixed_line_with_a_tick_token(self):
        self.assertIn('"wildlife monitor |', self.text)
        self.assertIn("tick=%1", self.text)
        # The last expression is the composed line, so the function returns it.
        self.assertTrue(self.text.rstrip().endswith("_line"))


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


def _kernel(path):
    """A callable Lambda built from a real kernel file, params pre-bound."""
    stmts = load_sqf(path)
    params, body = [], stmts
    if stmts and isinstance(stmts[0], Params):
        params = [name for name, _default in stmts[0].specs]
        body = stmts[1:]
    return Lambda(params, body, {})


def species_for_biome(biome, is_night, water_frac, veg_score, seed, table):
    # The shim forwards to the matcher and logs through the deprecation helper.
    # Both are bound here so the kernel runs from its real source.
    return run_sqf(
        SPECIES_FOR_BIOME,
        [biome, is_night, water_frac, veg_score, seed, table],
        globals_={
            "__FUNC__getSpeciesMatch": _kernel(SPECIES_MATCH),
            "__FUNC__speciesDeprecation": lambda: None,
        },
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


class TestNeedsRateWiring(unittest.TestCase):
    """The behaviour callback passes the operator rates to fnc_needsTick.

    The rates are declared settings (aee_wildlife_hungerRate / thirstRate).
    Before this wiring the callback passed the literals 0.02 and 0.03, so the
    settings were dead.  Reverting the callback to the literals fails these
    tests and makes tools/validation/validate_cba_settings.py report two dead
    settings again.
    """

    def setUp(self):
        src = WILDLIFE / "functions" / "fnc_applyAnimalBehaviour.sqf"
        self.src = src.read_text(encoding="utf-8")

    def test_reads_both_rate_settings(self):
        self.assertIn("QGVAR(hungerRate)", self.src)
        self.assertIn("QGVAR(thirstRate)", self.src)

    def test_passes_the_rates_not_literals(self):
        self.assertIn(
            "[_hunger, _thirst, 1, _hungerRate, _thirstRate] call FUNC(needsTick)",
            self.src,
        )
        self.assertNotIn(
            "[_hunger, _thirst, 1, 0.02, 0.03] call FUNC(needsTick)", self.src
        )


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


ASSET_MAP = DATA / "asset_map.sqf"
SPECIES_SOUND = AMBIENCE / "fnc_speciesSound.sqf"
MEDIA_EXTENSIONS = {".wss", ".ogg", ".wav"}


def load_asset_map():
    """The generated sound and fauna identity rows."""
    return run_sqf(ASSET_MAP, [])


def species_sound(group, platforms=None):
    """Run fnc_speciesSound against the real asset map."""
    if platforms is None:
        platforms = []
    return run_sqf(SPECIES_SOUND, [group, platforms, load_asset_map()])


class TestSpeciesSound(unittest.TestCase):
    """fnc_speciesSound runs from the real SQF against the real asset map."""

    def test_owl_resolves_to_the_raw_paths_not_the_cfg_sfx_class(self):
        media, gap = species_sound("owl", ["enoch"])
        self.assertFalse(gap)
        self.assertEqual(
            [path.rsplit("\\", 1)[-1] for path in media],
            ["owl1.wss", "owl2.wss", "owl3.wss"],
        )
        self.assertNotIn("Owl", media)

    def test_songbird_resolves_to_the_five_bird_files(self):
        media, gap = species_sound("songbird", ["enoch"])
        self.assertFalse(gap)
        self.assertEqual(len(media), 5)
        self.assertTrue(all("birds" in path for path in media))

    def test_fear_resolves_to_the_seven_distress_clips(self):
        media, gap = species_sound("fear", [])
        self.assertFalse(gap)
        self.assertEqual(len(media), 7)

    def test_deer_and_wolf_resolve_only_with_the_enoch_platform(self):
        deer, deer_gap = species_sound("deer", ["enoch"])
        self.assertFalse(deer_gap)
        self.assertEqual(len(deer), 11)
        self.assertTrue(all("sounds_f_enoch" in path.lower() for path in deer))
        wolf, wolf_gap = species_sound("wolf", ["enoch"])
        self.assertFalse(wolf_gap)
        self.assertEqual(len(wolf), 6)

    def test_deer_and_wolf_fall_back_to_the_base_night_bed_without_enoch(self):
        deer, deer_gap = species_sound("deer", [])
        self.assertTrue(deer_gap)
        self.assertGreater(len(deer), 0)
        self.assertTrue(all("sounds_f_enoch" not in path.lower() for path in deer))
        wolf, wolf_gap = species_sound("wolf", [])
        self.assertTrue(wolf_gap)
        self.assertGreater(len(wolf), 0)
        self.assertTrue(all("sounds_f_enoch" not in path.lower() for path in wolf))

    def test_the_water_group_never_resolves_to_the_silent_stream(self):
        media, gap = species_sound("water", [])
        self.assertEqual(media, [])
        self.assertTrue(gap)
        self.assertNotIn("Sound_Stream", media)

    def test_an_unknown_recording_is_never_mapped(self):
        for group in ("chicken_grill", "cicada", "frog", "none"):
            with self.subTest(group=group):
                media, _gap = species_sound(group, ["enoch"])
                self.assertEqual(media, [])

    def test_cricket_resolves_to_the_legacy_sarance_set(self):
        media, gap = species_sound("cricket", [])
        self.assertFalse(gap)
        self.assertEqual(len(media), 4)
        self.assertTrue(all("sarance" in path for path in media))

    def test_every_returned_path_passes_the_media_rules(self):
        groups = [row[1] for row in load_asset_map() if row[0] == "sound"]
        for group in groups:
            for platforms in ([], ["enoch"]):
                media, _gap = species_sound(group, platforms)
                for path in media:
                    self.assertTrue(path.lower().startswith("a3\\"), path)
                    extension = path[path.rfind(".") :].lower()
                    self.assertIn(extension, MEDIA_EXTENSIONS, path)

    def test_the_enoch_paths_are_all_under_the_enoch_prefix(self):
        asset_rows = load_asset_map()
        deer = [r for r in asset_rows if r[0] == "sound" and r[1] == "deer"][0]
        self.assertGreater(len(deer[3]), 0)
        self.assertTrue(all("sounds_f_enoch" in p.lower() for p in deer[3]))


PICK_BED = FUNCS / "fnc_pickBedSource.sqf"


def pick_bed_source(manifest, key, seed):
    """Run fnc_pickBedSource against a manifest."""
    return run_sqf(PICK_BED, [manifest, key, seed])


def produced_bed_keys():
    """Every context key the selector can emit, plus the fear key."""
    keys = set()
    for biome in ("Cfb", "BWh", "Af", "Dfc", ""):
        for night in (False, True):
            for water in (0.0, 0.3, 0.9):
                for veg in (0.0, 0.8):
                    for settle in (0.0, 0.8):
                        for coastal in (False, True):
                            key, _gain = sound_bed(
                                biome,
                                night,
                                water,
                                0,
                                0,
                                rain=0,
                                veg=veg,
                                settlement=settle,
                                coastal=coastal,
                            )
                            keys.add(key)
    keys.add("fear")
    return keys


class TestSoundBedOverlays(unittest.TestCase):
    """The farm and coast overlays the old selector could never return."""

    def test_the_settlement_overlay_selects_farm(self):
        self.assertEqual(sound_bed("Cfb", False, 0.1, 0, 0, settlement=0.8)[0], "farm")

    def test_the_coastal_overlay_selects_coast(self):
        self.assertEqual(sound_bed("Cfb", False, 0.3, 0, 0, coastal=True)[0], "coast")

    def test_water_and_night_still_win_over_the_overlays(self):
        self.assertEqual(
            sound_bed("Cfb", False, 0.9, 0, 0, settlement=0.9, coastal=True)[0],
            "water",
        )
        self.assertEqual(
            sound_bed("Cfb", True, 0.1, 0, 0, settlement=0.9, coastal=True)[0],
            "night",
        )


class TestPickBedSource(unittest.TestCase):
    """fnc_pickBedSource runs from the real SQF."""

    def test_a_key_with_no_rows_returns_empty(self):
        self.assertEqual(pick_bed_source(load_manifest(), "no_such_key", 1), "")

    def test_the_same_seed_returns_the_same_source(self):
        manifest = load_manifest()
        self.assertEqual(
            pick_bed_source(manifest, "farm", 42),
            pick_bed_source(manifest, "farm", 42),
        )

    def test_a_multi_row_key_reaches_every_row(self):
        manifest = load_manifest()
        reached = {pick_bed_source(manifest, "farm", s) for s in range(1000)}
        rows = {row[1] for row in manifest if row[0] == "farm"}
        self.assertEqual(reached, rows)
        self.assertGreater(len(rows), 1)

    def test_a_higher_gain_row_is_drawn_more_often(self):
        # Two rows, gains 1 and 3: the heavier row takes three of every four
        # draws, so a 1000-seed sweep counts it about three times as often.
        manifest = [
            ["k", "light", 120, 1.0],
            ["k", "heavy", 120, 3.0],
        ]
        counts = {"light": 0, "heavy": 0}
        for seed in range(1000):
            counts[pick_bed_source(manifest, "k", seed)] += 1
        self.assertGreater(counts["heavy"], counts["light"])


class TestSoundDefectFixes(unittest.TestCase):
    """Every manifest row is reachable and the six named defects are fixed."""

    def test_the_weighted_pick_covers_every_manifest_row(self):
        # Defect 1: the first-match scan is replaced by the weighted pick.
        tick = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("call FUNC(pickBedSource)", tick)
        self.assertNotIn("if ((_row select 0) == _bedKey) then", tick)
        manifest = load_manifest()
        keys = produced_bed_keys()
        for row in manifest:
            with self.subTest(row=row):
                self.assertIn(row[0], keys)
                reached = {
                    pick_bed_source(manifest, row[0], seed) for seed in range(1000)
                }
                self.assertIn(row[1], reached)

    def test_no_manifest_row_is_a_cfg_sfx_class(self):
        # Defect 4: every played source is a raw path, never a CfgSFX name.
        for _key, source, _distance, _gain in load_manifest():
            self.assertIn(".", source, source)

    def test_the_silent_water_row_is_gone(self):
        # Defect 3: the water bed was the silent Sound_Stream dummy.
        sources = [row[1] for row in load_manifest()]
        self.assertNotIn("Sound_Stream", sources)
        self.assertFalse(any("dummysound" in s.lower() for s in sources))

    def test_there_is_no_grass_key_and_sheep_are_livestock(self):
        # Defect 5: sheep are livestock, so they sit under the farm key.
        manifest = load_manifest()
        keys = {row[0] for row in manifest}
        self.assertNotIn("grass", keys)
        sheep = [row for row in manifest if "sheep" in row[1].lower()]
        self.assertGreater(len(sheep), 0)
        self.assertTrue(all(row[0] == "farm" for row in sheep))

    def test_farm_and_coast_rows_are_not_dead(self):
        # Defect 2: the selector now returns farm and coast.
        keys = produced_bed_keys()
        self.assertIn("farm", keys)
        self.assertIn("coast", keys)
        manifest = load_manifest()
        self.assertTrue(any(row[0] == "farm" for row in manifest))
        self.assertTrue(any(row[0] == "coast" for row in manifest))

    def test_the_fear_source_is_chosen_per_species(self):
        # Defect 6: the hardcoded scared_animal1 is replaced by the map.
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn('["fear", [], _assetMap] call EFUNC(ambience,speciesSound)', text)
        self.assertIn("speciesGroup", text)
        self.assertNotIn("scared_animal1", text)

    def test_no_cfg_sfx_name_is_passed_to_create_sound_source_local(self):
        # Defect 4 at the call site: a CfgSFX class has no CfgVehicles wrapper.
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("call FUNC(pickBedSource)", text)
        for _key, source, _distance, _gain in load_manifest():
            self.assertIn(".", source, source)


PICK_BED = FUNCS / "fnc_pickBedSource.sqf"
SOUND_TICK = AMBIENCE / "fnc_soundTick.sqf"
CALL_PATTERN = AMBIENCE / "fnc_getCallPattern.sqf"

# The corpus temporal bins for the two groups the day fixture drives:
# pre_dawn, dawn, morning, midday, afternoon, dusk, night.
BIRD_BINS = [0.6, 1, 0.5, 0.05, 0.05, 0.4, 0]
CRICKET_BINS = [0.3, 0, 0, 0, 0, 0.6, 1]


def sun_elevation(hour):
    """A simple diurnal sun elevation, degrees, for the day fixture."""
    if 6 <= hour < 18:
        return 60.0 * math.sin(math.pi * (hour - 6) / 12)
    return -30.0


def sound_tick(hour, sun_elev, month, temp, wind, rain, gain, mix, seed=7):
    """Run fnc_soundTick over the real asset map with the real pattern kernel."""
    return run_sqf(
        SOUND_TICK,
        [
            hour,
            sun_elev,
            month,
            temp,
            wind,
            rain,
            gain,
            mix,
            load_asset_map(),
            [],
            seed,
        ],
        globals_={
            "__FUNC__getCallPattern": lambda *a: run_sqf(CALL_PATTERN, list(a)),
            "__FUNC__speciesSound": lambda *a: run_sqf(SPECIES_SOUND, list(a)),
        },
    )


class TestSoundTick(unittest.TestCase):
    """fnc_soundTick runs from the real SQF over a simulated day."""

    def test_the_bird_emission_count_peaks_at_dawn_and_lulls_midday(self):
        counts = []
        for hour in range(24):
            mix = [["temperate_bird_dawn", "songbird", 1.0, BIRD_BINS]]
            emitted = sound_tick(hour, sun_elevation(hour), 6, 18, 0, 0, 1.0, mix)
            counts.append(len(emitted))
        peak = max(range(24), key=lambda h: counts[h])
        self.assertIn(peak, (5, 6, 7, 8), counts)
        self.assertGreater(counts[peak], 0)
        # The mid-day lull is near silence against the dawn peak.
        self.assertLess(counts[13], counts[peak] / 10)

    def test_a_cricket_at_10c_emits_at_the_dolbear_rate_and_at_2c_is_silent(self):
        mix = lambda: [["temperate_insect_cricket", "cricket", 1.0, CRICKET_BINS]]
        hot = sound_tick(23, -30, 6, 10, 0, 0, 1.0, mix())
        cold = sound_tick(23, -30, 6, 2, 0, 0, 1.0, mix())
        mild = sound_tick(23, -30, 6, 6, 0, 0, 1.0, mix())
        self.assertGreater(len(hot), 0)
        self.assertEqual(len(cold), 0)
        # The Dolbear rate rises with the temperature.
        self.assertGreater(len(hot), len(mild))
        self.assertGreater(len(mild), 0)

    def test_rain_suppresses_the_emissions(self):
        mix = [["temperate_bird_dawn", "songbird", 1.0, BIRD_BINS]]
        dry = sound_tick(7, 30, 6, 18, 0, 0, 1.0, mix)
        wet = sound_tick(7, 30, 6, 18, 0, 1.0, 1.0, mix)
        self.assertGreater(len(dry), len(wet))

    def test_a_fixed_seed_gives_the_same_schedule(self):
        mix = [["temperate_bird_dawn", "songbird", 1.0, BIRD_BINS]]
        self.assertEqual(
            sound_tick(7, 30, 6, 18, 0, 0, 1.0, mix, 42),
            sound_tick(7, 30, 6, 18, 0, 0, 1.0, mix, 42),
        )

    def test_a_group_with_zero_weight_emits_nothing(self):
        # The alarm gate: a group whose call did not fire carries weight zero.
        mix = [["temperate_bird_dawn", "songbird", 0.0, BIRD_BINS]]
        self.assertEqual(sound_tick(7, 30, 6, 18, 0, 0, 1.0, mix), [])

    def test_a_silent_listener_emits_nothing(self):
        mix = [["temperate_bird_dawn", "songbird", 1.0, BIRD_BINS]]
        self.assertEqual(sound_tick(7, 30, 6, 18, 0, 0, 0.0, mix), [])

    def test_a_group_without_confirmed_media_emits_nothing(self):
        # The frog sound group is UNKNOWN in vanilla, so the amphibian chorus
        # produces no emission even when the pattern allows it.
        mix = [["temperate_amphibian", "frog", 1.0, [0.4, 0.1, 0, 0, 0, 0.5, 0.9]]]
        self.assertEqual(sound_tick(23, -30, 6, 20, 0, 1.0, 1.0, mix), [])

    def test_the_emitted_volume_carries_the_silence_gain(self):
        mix = [["temperate_bird_dawn", "songbird", 1.0, BIRD_BINS]]
        loud = sound_tick(7, 30, 6, 18, 0, 0, 1.0, mix)
        quiet = sound_tick(7, 30, 6, 18, 0, 0, 0.5, mix)
        self.assertGreater(len(loud), 0)
        self.assertTrue(all(row[2] == 1.0 for row in loud))
        self.assertTrue(all(row[2] == 0.5 for row in quiet))

    def test_the_tick_wires_the_scheduler(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("call EFUNC(ambience,soundTick)", text)
        self.assertIn("call FUNC(getSpeciesMatch)", text)
        self.assertIn("QGVAR(soundSchedule)", text)


class TestBedStability(unittest.TestCase):
    """The ambient bed is stable across ticks (task 21)."""

    def test_the_bed_recreates_only_on_a_key_change(self):
        text = (AMBIENCE / "fnc_playAmbientBed.sqf").read_text(encoding="utf-8")
        # The recreate is guarded by the stored key.
        self.assertIn("QGVAR(ambientKey)", text)
        self.assertIn("_key == _source", text)
        # Exactly one delete and one create, delete first, guard before both.
        self.assertEqual(text.count("deleteVehicle"), 1)
        self.assertEqual(text.count("createSoundSourceLocal"), 1)
        self.assertLess(text.index("_key == _source"), text.index("deleteVehicle"))
        self.assertLess(
            text.index("deleteVehicle"), text.index("createSoundSourceLocal")
        )

    def test_the_bed_documents_the_cfg_sfx_gain_limit(self):
        text = (AMBIENCE / "fnc_playAmbientBed.sqf").read_text(encoding="utf-8")
        self.assertIn("takes no gain", text)
        self.assertIn("playOneShot", text)


class TestEmitterPlan(unittest.TestCase):
    """The bounded attached-emitter registry (task 27) runs from the real SQF."""

    def plan(self, registry, active, cap=8, radius=150):
        return run_sqf(EMITTER_PLAN, [registry, active, cap, radius])

    def test_a_new_animal_gets_an_emitter(self):
        create, keep, release = self.plan([], [["a", "owl", 10]])
        self.assertEqual(create, [["a", "owl"]])
        self.assertEqual(keep, [])
        self.assertEqual(release, [])

    def test_an_unchanged_animal_is_kept(self):
        create, keep, release = self.plan([["a", "owl"]], [["a", "owl", 10]])
        self.assertEqual(create, [])
        self.assertEqual(keep, ["a"])
        self.assertEqual(release, [])

    def test_a_despawn_releases_the_emitter(self):
        # 'z' is gone from the active list, so its emitter is released.
        create, keep, release = self.plan(
            [["a", "owl"], ["z", "owl"]], [["a", "owl", 10]]
        )
        self.assertEqual(create, [])
        self.assertEqual(keep, ["a"])
        self.assertEqual(release, ["z"])

    def test_a_key_change_recreates_the_emitter(self):
        create, keep, release = self.plan([["a", "owl"]], [["a", "deer", 10]])
        self.assertEqual(create, [["a", "deer"]])
        self.assertEqual(keep, [])
        self.assertEqual(release, ["a"])

    def test_an_animal_beyond_the_radius_is_released(self):
        create, keep, release = self.plan([["a", "owl"]], [["a", "owl", 200]])
        self.assertEqual(create, [])
        self.assertEqual(keep, [])
        self.assertEqual(release, ["a"])

    def test_the_cap_bounds_the_live_total(self):
        registry = [["a", "owl"], ["b", "owl"], ["c", "owl"]]
        active = [["a", "owl", 10], ["b", "owl", 20], ["c", "owl", 30]]
        create, keep, release = self.plan(registry, active, cap=2)
        self.assertEqual(create, [])
        self.assertEqual(keep, ["a", "b"])
        self.assertEqual(release, ["c"])

    def test_the_nearest_animals_are_kept_first(self):
        create, keep, release = self.plan(
            [], [["a", "owl", 30], ["b", "owl", 10]], cap=1
        )
        self.assertEqual(create, [["b", "owl"]])

    def test_an_empty_input_is_an_empty_plan(self):
        create, keep, release = self.plan([], [])
        self.assertEqual(create, [])
        self.assertEqual(keep, [])
        self.assertEqual(release, [])


# The concurrent animal-call density target.  The measured density was eight of
# eight one-shot slots busy at once, which reads as a disturbed soundscape.  The
# acoustic niche hypothesis (Krause 1987; Pijanowski et al. 2011, BioScience
# 61(3):203-216) holds that species partition the auditory spectrum in time and
# frequency, so a real forest has few overlapping calls.  No published figure
# gives a simultaneous-caller count, so three is a stated ceiling.
DENSITY_TARGET = 3


class TestSoundDensityCap(unittest.TestCase):
    """The concurrent animal-call density is capped at the stated target."""

    @classmethod
    def setUpClass(cls):
        cls.header = (WILDLIFE / "script_component.hpp").read_text(encoding="utf-8")

    def _define(self, name):
        match = re.search(rf"#define\s+{name}\s+(\d+)", self.header)
        self.assertIsNotNone(match, f"{name} is not defined")
        return int(match.group(1))

    def test_the_one_shot_cap_is_the_density_target(self):
        self.assertEqual(self._define("WILDLIFE_SOUND_INSTANCE_CAP"), DENSITY_TARGET)

    def test_the_emitter_cap_is_the_density_target(self):
        self.assertEqual(self._define("WILDLIFE_EMITTER_CAP"), DENSITY_TARGET)

    def test_the_one_shot_kernel_enforces_the_cap(self):
        text = (AMBIENCE / "fnc_playOneShot.sqf").read_text(encoding="utf-8")
        self.assertIn(">= WILDLIFE_SOUND_INSTANCE_CAP) exitWith { false }", text)

    def test_the_tick_bounds_the_per_tick_top_up_by_the_cap(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn('for "_k" from 0 to (WILDLIFE_SOUND_INSTANCE_CAP - 1)', text)

    def test_the_emitter_plan_defaults_to_the_cap(self):
        text = (AMBIENCE / "fnc_emitterPlan.sqf").read_text(encoding="utf-8")
        self.assertIn('["_cap", WILDLIFE_EMITTER_CAP, [0]]', text)

    def test_the_state_line_reports_the_cap(self):
        text = (FUNCS / "fnc_logWildlifeState.sqf").read_text(encoding="utf-8")
        self.assertIn("_soundLive, WILDLIFE_SOUND_INSTANCE_CAP", text)


class TestEmitterClass(unittest.TestCase):
    """fnc_emitterClass runs from the real SQF."""

    ASSET_MAP = [
        ["sound", "owl", "CONFIRMED", ["a3\\sounds_f\\animals\\owl1.wss"], []],
        ["sound", "deer", "CONFIRMED", ["DeerCall", "Deer_Call.wss"], []],
        ["sound", "water", "CONFIRMED", [], []],
    ]

    def test_a_class_entry_is_the_looping_source(self):
        self.assertEqual(run_sqf(EMITTER_CLASS, ["deer", self.ASSET_MAP]), "DeerCall")

    def test_a_raw_path_is_not_a_looping_source(self):
        self.assertEqual(run_sqf(EMITTER_CLASS, ["owl", self.ASSET_MAP]), "")

    def test_a_group_with_no_media_has_no_source(self):
        self.assertEqual(run_sqf(EMITTER_CLASS, ["water", self.ASSET_MAP]), "")

    def test_an_unknown_group_has_no_source(self):
        self.assertEqual(run_sqf(EMITTER_CLASS, ["nope", self.ASSET_MAP]), "")

    def test_an_empty_group_has_no_source(self):
        self.assertEqual(run_sqf(EMITTER_CLASS, ["", self.ASSET_MAP]), "")


class TestEmitterSourceContracts(unittest.TestCase):
    """The engine wiring the harness cannot execute (task 27)."""

    def test_the_one_shot_passes_the_emitter_object(self):
        text = (AMBIENCE / "fnc_playOneShot.sqf").read_text(encoding="utf-8")
        self.assertIn('["_attachTo", objNull, [objNull]]', text)
        # The object branch takes the animal as the sound source.
        self.assertIn("playSound3D [_source, _attachTo,", text)
        self.assertIn("getPosASL _attachTo", text)
        # The positional branch is kept for the ambient layer.
        self.assertIn("playSound3D [_source, objNull,", text)

    def test_the_fear_call_passes_the_fleeing_agent(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn(
            "WILDLIFE_SOUND_MAX_DISTANCE, _agent, _callPitch] call EFUNC(ambience,playOneShot)",
            text,
        )

    def test_the_emitter_functions_are_prepped(self):
        text = (AMBIENCE.parent / "XEH_PREP.hpp").read_text(encoding="utf-8")
        for name in ("emitterPlan", "emitterClass", "emitterSync", "emitterRelease"):
            self.assertIn(f"PREP({name})", text, name)

    def test_the_emitter_constants_are_declared(self):
        text = (WILDLIFE / "script_component.hpp").read_text(encoding="utf-8")
        self.assertIn("WILDLIFE_EMITTER_CAP", text)
        self.assertIn("WILDLIFE_EMITTER_RADIUS", text)

    def test_the_sync_attaches_and_bounds_the_emitter(self):
        text = (AMBIENCE / "fnc_emitterSync.sqf").read_text(encoding="utf-8")
        self.assertIn("call FUNC(emitterPlan)", text)
        self.assertIn("createSoundSourceLocal", text)
        self.assertIn("attachTo [_agent", text)
        self.assertIn("WILDLIFE_EMITTER_CAP", text)
        self.assertIn("WILDLIFE_EMITTER_RADIUS", text)
        self.assertIn("QGVAR(emitters)", text)

    def test_a_culled_animal_releases_its_emitter(self):
        text = (FUNCS / "fnc_cullFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("EFUNC(ambience,emitterRelease)", text)

    def test_a_teardown_releases_every_emitter(self):
        text = (FUNCS / "fnc_teardownWildlife.sqf").read_text(encoding="utf-8")
        self.assertIn("QGVAR(emitters)", text)
        self.assertIn("deleteVehicle", text)

    def test_the_tick_syncs_the_emitters(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("EFUNC(ambience,emitterSync)", text)

    def test_the_spawn_records_the_sound_group(self):
        text = (FUNCS / "fnc_spawnFauna.sqf").read_text(encoding="utf-8")
        self.assertIn("QGVAR(soundGroup)", text)

    def test_the_emitter_is_client_local(self):
        for name in ("fnc_emitterSync.sqf", "fnc_emitterRelease.sqf"):
            text = (AMBIENCE / name).read_text(encoding="utf-8")
            self.assertIn("hasInterface", text, name)


PITCH_GLOBALS = {
    "WILDLIFE_PITCH_JITTER": 0.04,
    "WILDLIFE_PITCH_RATE_COUPLING": 0.25,
    "WILDLIFE_PITCH_MIN": 0.5,
    "WILDLIFE_PITCH_MAX": 2.0,
}


def call_pitch(seed, species, temperature, radial, base=1):
    return run_sqf(
        CALL_PITCH,
        [seed, species, temperature, radial, base],
        globals_=PITCH_GLOBALS,
    )


class TestCallPitch(unittest.TestCase):
    """The call-pitch kernel (task 28) runs from the real SQF."""

    def test_same_inputs_give_the_same_pitch(self):
        self.assertEqual(call_pitch(42, "owl", 15, 0), call_pitch(42, "owl", 15, 0))

    def test_a_new_seed_moves_the_pitch(self):
        self.assertNotEqual(call_pitch(42, "owl", 15, 0), call_pitch(43, "owl", 15, 0))

    def test_a_closing_source_is_higher_than_an_opening_source(self):
        closing = call_pitch(42, "owl", 15, 40)
        opening = call_pitch(42, "owl", 15, -40)
        self.assertGreater(closing, opening)

    def test_the_cricket_pitch_rises_with_temperature(self):
        cold = call_pitch(42, "cricket", 10, 0)
        mild = call_pitch(42, "cricket", 20, 0)
        warm = call_pitch(42, "cricket", 30, 0)
        self.assertLess(cold, mild)
        self.assertLess(mild, warm)

    def test_a_small_bird_is_higher_than_an_owl(self):
        self.assertGreater(
            call_pitch(42, "temperate_bird_dawn", 20, 0),
            call_pitch(42, "owl", 20, 0),
        )

    def test_the_pitch_is_clamped(self):
        # An extreme opening velocity is clamped to the pitch floor.
        self.assertGreaterEqual(call_pitch(42, "owl", 50, -300), 0.5)
        self.assertLessEqual(call_pitch(42, "owl", 50, 300), 2.0)


class TestPitchSourceContracts(unittest.TestCase):
    """No fixed pitch anywhere in the wildlife sound path (task 28)."""

    def test_the_one_shot_uses_the_derived_pitch(self):
        text = (AMBIENCE / "fnc_playOneShot.sqf").read_text(encoding="utf-8")
        self.assertIn('["_pitch", 1, [0]]', text)
        self.assertIn(", _volume, _pitch, _distance", text)

    def test_the_bed_carries_the_pitch(self):
        text = (AMBIENCE / "fnc_playAmbientBed.sqf").read_text(encoding="utf-8")
        self.assertIn('["_pitch", 1, [0]]', text)
        self.assertIn(", objNull, _pitch] call FUNC(playOneShot)", text)

    def test_the_tick_derives_the_pitch(self):
        text = (FUNCS / "fnc_wildlifeTick.sqf").read_text(encoding="utf-8")
        self.assertIn("call EFUNC(ambience,callPitch)", text)

    def test_the_fear_call_derives_the_pitch(self):
        text = (FUNCS / "fnc_applyAnimalBehaviour.sqf").read_text(encoding="utf-8")
        self.assertIn("call EFUNC(ambience,callPitch)", text)
        self.assertIn("vectorDotProduct", text)

    def test_the_pitch_constants_and_prep(self):
        constants = (WILDLIFE / "script_component.hpp").read_text(encoding="utf-8")
        for name in (
            "WILDLIFE_PITCH_MIN",
            "WILDLIFE_PITCH_MAX",
            "WILDLIFE_PITCH_JITTER",
            "WILDLIFE_PITCH_RATE_COUPLING",
        ):
            self.assertIn(name, constants, name)
        preps = (AMBIENCE.parent / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(callPitch)", preps)


SHOT_GLOBALS = {
    "WILDLIFE_SHOT_REPORT_DB": 160,
    "WILDLIFE_SHOT_REPORT_REF_MV": 900,
    "WILDLIFE_SHOT_PITCH_PER_MACH": 0.15,
    "WILDLIFE_SHOT_CRACK_DB": 150,
    "WILDLIFE_SHOT_SNAP_RADIUS_M": 5,
    "WILDLIFE_SHOT_SNAP_DB": 140,
    "WILDLIFE_SHOT_RICOCHET_DB": 130,
    "WILDLIFE_SHOT_RICOCHET_ANGLE_DEG": 30,
    "WILDLIFE_SHOT_RICOCHET_REF_J": 500,
}


def speed_of_sound(temperature_c):
    return 20.05 * math.sqrt(temperature_c + 273.15)


def shot_audio(
    caliber=7.62,
    muzzle_v=900,
    current_v=None,
    temp=15,
    distance=15,
    closest=-1,
    angle=-1,
    energy=0,
):
    if current_v is None:
        current_v = muzzle_v
    return run_sqf(
        SHOT_AUDIO,
        [caliber, muzzle_v, current_v, temp, distance, closest, angle, energy],
        globals_=SHOT_GLOBALS,
    )


class TestShotAudio(unittest.TestCase):
    """The ballistics-coupled shot-audio kernel (task 26) runs from the real SQF."""

    def test_a_supersonic_round_has_a_crack(self):
        self.assertTrue(shot_audio(current_v=speed_of_sound(15) + 50)[2])

    def test_a_subsonic_round_has_no_crack(self):
        self.assertFalse(shot_audio(current_v=speed_of_sound(15) - 50)[2])

    def test_a_hot_day_raises_the_crack_threshold(self):
        # 345 m/s is supersonic at 15 C (c=340) and subsonic at 40 C (c=356).
        self.assertTrue(shot_audio(current_v=345, temp=15)[2])
        self.assertFalse(shot_audio(current_v=345, temp=40)[2])

    def test_the_report_pitch_rises_with_velocity(self):
        slow = shot_audio(muzzle_v=300)[1]
        fast = shot_audio(muzzle_v=1100)[1]
        self.assertGreater(fast, slow)

    def test_a_near_pass_has_a_snap(self):
        self.assertGreater(shot_audio(closest=1)[4], 0)
        self.assertEqual(shot_audio(closest=50)[4], 0)

    def test_a_grazing_impact_ricochets(self):
        self.assertGreater(shot_audio(angle=5, energy=500)[5], 0)
        self.assertEqual(shot_audio(angle=80, energy=500)[5], 0)

    def test_same_inputs_give_the_same_result(self):
        self.assertEqual(shot_audio(), shot_audio())


class TestShotAudioSourceContracts(unittest.TestCase):
    """The ballistics reuse and the constants (task 26)."""

    def test_the_shot_kernel_is_prepped(self):
        preps = (AMBIENCE.parent / "XEH_PREP.hpp").read_text(encoding="utf-8")
        self.assertIn("PREP(shotAudio)", preps)

    def test_the_shot_constants_are_declared(self):
        constants = (WILDLIFE / "script_component.hpp").read_text(encoding="utf-8")
        for name in (
            "WILDLIFE_SHOT_REPORT_DB",
            "WILDLIFE_SHOT_CRACK_DB",
            "WILDLIFE_SHOT_SNAP_RADIUS_M",
            "WILDLIFE_SHOT_RICOCHET_ANGLE_DEG",
        ):
            self.assertIn(name, constants, name)

    def test_the_fired_handler_reuses_the_ballistics_kernel(self):
        text = (FUNCS / "fnc_initWildlife.sqf").read_text(encoding="utf-8")
        self.assertIn("EFUNC(ballistics,getLoadData)", text)
        self.assertIn("EFUNC(ballistics,parseCaliber)", text)
        self.assertIn("EFUNC(ambience,shotAudio)", text)

    def test_the_kernel_names_the_ballistics_reuse(self):
        text = (AMBIENCE / "fnc_shotAudio.sqf").read_text(encoding="utf-8")
        self.assertIn("fnc_calculateBallisticDrag.sqf", text)
        self.assertIn("fnc_parseCaliber.sqf", text)


class TestWildlifeTeardownWiring(unittest.TestCase):
    """The wildlife teardown is wired on mission end."""

    def test_the_ended_handler_calls_the_teardown(self):
        post = (WILDLIFE / "XEH_postInit.sqf").read_text(encoding="utf-8")
        self.assertIn('addMissionEventHandler ["Ended"', post)
        self.assertIn("[] call FUNC(teardownWildlife)", post)


if __name__ == "__main__":
    unittest.main()
