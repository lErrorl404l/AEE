#!/usr/bin/env python3
"""Surface-type normalisation regression (issue #204 follow-on).

The Arma 3 `surfaceType` command returns the surface CLASS NAME with NO
'#' prefix (GdtSnow, GdtDesert, GdtStratisConcrete).  The '#gdt*' form is an
Armed Assault / Arma 2 shape.  A live comparison of a `toLower (surfaceType
...)` result against a literal "#gdt..." string can NEVER match, so that
branch is dead.

These tests PARSE the real SQF mapping out of each fixed file and evaluate it
with the real runtime form (bare "GdtSnow" lowercased, and the already
stripped "#gdt"/"gdt" form).  A file that still compares the raw string
against '#gdt*' yields no match and the test fails.

Run: python3 -m unittest tools.tests.test_surface_type_normalisation
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ADDON = ROOT / "addons"

FILES = {
    "humidity": ADDON / "atmos" / "functions" / "state" / "fnc_updateHumidity.sqf",
    "turbulence": ADDON
    / "atmos"
    / "functions"
    / "physics"
    / "fnc_calculateTurbulence.sqf",
    "classify": ADDON / "material" / "functions" / "fnc_classifyBySurfaceType.sqf",
    "surface_material": ADDON
    / "fx"
    / "functions"
    / "particle"
    / "fnc_surfaceMaterial.sqf",
    "concealment": ADDON
    / "environmental"
    / "functions"
    / "terrain"
    / "fnc_calculateConcealment.sqf",
    "temperature": ADDON
    / "thermal"
    / "functions"
    / "environment"
    / "fnc_updateTemperature.sqf",
    "mirage": ADDON
    / "optics"
    / "functions"
    / "sensor"
    / "fnc_calculateMirageIntensity.sqf",
    "scan_signals": ADDON
    / "environmental"
    / "functions"
    / "biome"
    / "fnc_scanTerrainSignals.sqf",
    "biome_at_pos": ADDON
    / "environmental"
    / "functions"
    / "biome"
    / "fnc_getBiomeAtPosition.sqf",
    # Already normalised before this change - drift-lock only.
    "terrain_speed": ADDON / "mobility" / "functions" / "fnc_getTerrainSpeedFactor.sqf",
    "ground_state": ADDON / "mobility" / "functions" / "fnc_updateGroundState.sqf",
}


def read(name):
    return FILES[name].read_text(encoding="utf-8")


def code_only(text):
    """The SQF with block and // comments removed."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def normalise(surface):
    """Mirror of the SQF normalisation-on-read for a surfaceType result."""
    s = surface.lower()
    if s.startswith("#gdt"):
        return s[4:]
    if s.startswith("gdt"):
        return s[3:]
    return s


def extract_block(text, marker):
    """The bracketed block that follows `marker` (a createHashMapFromArray
    list or a variable table)."""
    start = text.index(marker)
    start = text.index("[", start)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise AssertionError(f"unbalanced block after {marker}")


def equality_cases(text, var):
    """{key: value} for `case (var == "key"): { value };`."""
    code = code_only(text)
    return {
        k: float(v)
        for k, v in re.findall(
            r'case\s*\(\s*%s\s*==\s*"([^"]+)"\s*\)\s*:\s*\{\s*(-?\d+(?:\.\d+)?)\s*\}'
            % var,
            code,
        )
    }


def membership_number_cases(text, var):
    """[(keys, number)] for `case (var in ["a","b"]): { number };`, in order."""
    code = code_only(text)
    rows = re.findall(
        r"case\s*\(\s*%s\s+in\s*\[([^\]]*)\]\s*\)\s*:\s*\{\s*(-?\d+(?:\.\d+)?)\s*\}"
        % var,
        code,
    )
    return [(re.findall(r'"([^"]+)"', keys), float(val)) for keys, val in rows]


def membership_string_cases(text, var):
    """[(keys, value)] for `case (var in ["a","b"]): { "value" };`, in order."""
    code = code_only(text)
    rows = re.findall(
        r'case\s*\(\s*%s\s+in\s*\[([^\]]*)\]\s*\)\s*:\s*\{\s*"([^"]+)"\s*\}' % var,
        code,
    )
    return [(re.findall(r'"([^"]+)"', keys), val) for keys, val in rows]


def first_match(groups, value, default):
    for keys, result in groups:
        if value in keys:
            return result
    return default


class TestNormalisationHelpers(unittest.TestCase):
    def test_bare_runtime_form(self):
        # surfaceType returns "GdtSnow"; the code lowercases it.
        self.assertEqual(normalise("GdtSnow"), "snow")
        self.assertEqual(normalise("GdtStratisConcrete"), "stratisconcrete")
        self.assertEqual(normalise("Default"), "default")

    def test_legacy_forms_still_resolve(self):
        self.assertEqual(normalise("#gdtasphalt"), "asphalt")
        self.assertEqual(normalise("gdtsnow"), "snow")

    def test_already_bare_token_is_unchanged(self):
        self.assertEqual(normalise("snow"), "snow")


class TestUpdateHumidity(unittest.TestCase):
    """fnc_updateHumidity surface modifier."""

    def setUp(self):
        self.cases = equality_cases(read("humidity"), "_type")

    def test_runtime_desert(self):
        self.assertEqual(self.cases[normalise("GdtDesert")], -15)

    def test_runtime_snow(self):
        self.assertEqual(self.cases[normalise("GdtSnow")], 5)

    def test_runtime_ice(self):
        self.assertEqual(self.cases[normalise("GdtIce")], -10)

    def test_legacy_prefixed_input_resolves(self):
        self.assertEqual(self.cases[normalise("#gdtsnow")], 5)

    def test_no_dead_prefix_keys(self):
        self.assertFalse([k for k in self.cases if k.startswith("#")])


class TestCalculateTurbulence(unittest.TestCase):
    """fnc_calculateTurbulence roughness source shape.

    Roughness now comes from the engine's own CfgSurfaces `rough`
    coefficient, so the source must read configFile and must no longer
    carry the static membership table keyed on a surface token.
    """

    def setUp(self):
        self.code = code_only(read("turbulence"))

    def test_reads_roughness_from_cfg_surfaces(self):
        self.assertIn('"CfgSurfaces"', self.code)
        self.assertIn('"rough"', self.code)

    def test_no_static_membership_table(self):
        self.assertNotIn("case (_type in [", self.code)

    def test_normalises_the_surface_token(self):
        self.assertIn('"#gdt"', self.code)


class TestClassifyBySurfaceType(unittest.TestCase):
    """fnc_classifyBySurfaceType material class for a '#'-less input."""

    def setUp(self):
        self.groups = membership_string_cases(read("classify"), "_name")

    def _classify(self, surface):
        return first_match(self.groups, normalise(surface), "ground")

    def test_runtime_desert_is_ground(self):
        self.assertEqual(self._classify("GdtDesert"), "ground")

    def test_runtime_asphalt(self):
        self.assertEqual(self._classify("GdtAsphalt"), "asphalt")

    def test_runtime_concrete(self):
        self.assertEqual(self._classify("GdtConcrete"), "concrete")

    def test_runtime_gravel(self):
        self.assertEqual(self._classify("GdtGravel"), "rock")

    def test_runtime_marsh_is_water(self):
        self.assertEqual(self._classify("GdtMarsh"), "water")

    def test_runtime_forest_is_vegetation(self):
        self.assertEqual(self._classify("GdtForest"), "vegetation")

    def test_legacy_prefixed_input_recovers_concrete(self):
        # A caller that still passes "#gdtconcrete" must resolve too.
        self.assertEqual(self._classify("#gdtconcrete"), "concrete")

    def test_dynamic_config_lookup_keeps_the_gdt_prefix(self):
        # The CfgSurfaces class is Gdt* WITH the prefix; the dynamic path
        # must strip only the '#', never the Gdt tag.
        code = code_only(read("classify"))
        self.assertIn('_clean find "#gdt"', code)
        self.assertIn("_clean select [4, (count _clean) - 4]", code)
        self.assertIn("the Gdt prefix is kept", read("classify"))
        self.assertNotIn('_clean find "gdt" == 0', code)

    def test_no_dead_prefix_keys(self):
        for keys, _ in self.groups:
            self.assertFalse([k for k in keys if k.startswith("#")])


class TestSurfaceMaterial(unittest.TestCase):
    """fnc_surfaceMaterial particle material table."""

    def setUp(self):
        code = code_only(read("surface_material"))
        block = extract_block(code, "_TABLE")
        # IN ORDER: [(key, material, density)].  The SQF matcher takes the
        # first row whose key is a PREFIX of the token, so order matters
        # (drygrass before grass).
        self.rows = [
            (k, m, d)
            for k, m, d in re.findall(
                r'\["([^"]+)",\s*"([^"]+)",\s*\[[^\]]*\],\s*([\d.]+)\]', block
            )
        ]
        # The matcher operator decides anchoring.  Read it out of the SQF so
        # a change from `find _key == 0` (anchored) to `find _key >= 0`
        # (contains) makes these tests fail.
        m = re.search(r"_s find _key\s*(==|>=|>)\s*0", code)
        assert m, "the SQF matcher operator is gone"
        self.op = m.group(1)

    def _match(self, surface):
        token = normalise(surface)
        for key, material, density in self.rows:
            if self._hits(token, key):
                return (material, density)
        return None

    def _hits(self, token, key):
        idx = token.find(key)
        if self.op == "==":
            return idx == 0
        if self.op == ">=":
            return idx >= 0
        return idx > 0

    def test_runtime_snow(self):
        self.assertEqual(self.rows and self._match("GdtSnow")[0], "snow")

    def test_runtime_drygrass_keeps_its_own_row(self):
        # The keys are prefix anchors: drygrass must win over grass for the
        # token gdtdrygrass, and the anchoring must not let grass win first.
        self.assertEqual(self._match("GdtDryGrass"), ("dirt", "0.80"))

    def test_runtime_grass_resolves_to_grass_row(self):
        self.assertEqual(self._match("GdtGrass"), ("dirt", "0.35"))

    def test_runtime_snow_does_not_resolve_to_drygrass(self):
        self.assertNotEqual(self._match("GdtSnow"), ("dirt", "0.80"))

    def test_runtime_mud(self):
        self.assertEqual(self._match("GdtMud")[0], "mud")

    def test_no_dead_prefix_keys(self):
        self.assertFalse([k for k, _, _ in self.rows if k.startswith("#")])


class TestConcealment(unittest.TestCase):
    """fnc_calculateConcealment surface branch tokens."""

    def setUp(self):
        code = code_only(read("concealment"))
        # `find "X"` branch tokens, excluding the normalisation guard literal.
        self.tokens = [
            t for t in re.findall(r'_surface find "([^"]+)"', code) if t != "#gdt"
        ]

    def test_runtime_forest_branch_bites(self):
        # The forest branch tests `find "forest"`; the runtime "gdtsnow"
        # style string must contain the bare token after normalisation.
        self.assertIn("forest", self.tokens)
        self.assertIn("forest", normalise("GdtForest"))

    def test_runtime_snow_branch_bites(self):
        self.assertIn("snow", self.tokens)
        self.assertIn("snow", normalise("GdtSnow"))

    def test_no_dead_prefix_tokens(self):
        self.assertFalse([t for t in self.tokens if t.startswith("#")])


class TestUpdateTemperature(unittest.TestCase):
    """fnc_updateTemperature surface modifier."""

    def setUp(self):
        self.cases = equality_cases(read("temperature"), "_type")

    def test_runtime_desert(self):
        self.assertEqual(self.cases[normalise("GdtDesert")], 4)

    def test_runtime_snow(self):
        self.assertEqual(self.cases[normalise("GdtSnow")], -3)

    def test_no_dead_prefix_keys(self):
        self.assertFalse([k for k in self.cases if k.startswith("#")])


class TestMirage(unittest.TestCase):
    """fnc_calculateMirageIntensity arid-surface test."""

    def setUp(self):
        code = code_only(read("mirage"))
        m = re.search(r"_isAridSurf\s*=\s*_surfaceType\s+in\s*\[([^\]]*)\]", code)
        assert m, "the arid-surface set is gone"
        self.surfaces = set(re.findall(r'"([^"]+)"', m.group(1)))

    def test_runtime_desert_is_arid(self):
        self.assertIn(normalise("GdtDesert"), self.surfaces)

    def test_runtime_asphalt_is_arid(self):
        self.assertIn(normalise("GdtAsphalt"), self.surfaces)

    def test_no_dead_prefix_tokens(self):
        self.assertFalse([s for s in self.surfaces if s.startswith("#")])


class TestScanTerrainSignals(unittest.TestCase):
    """fnc_scanTerrainSignals surface vote table."""

    def setUp(self):
        code = code_only(read("scan_signals"))
        block = extract_block(code, "_SURFACE_VOTES")
        self.rows = dict(re.findall(r'\["([^"]+)",\s*(\[\[.*?\]\])', block, re.S))

    def test_runtime_desert_votes_hot_desert(self):
        self.assertIn(normalise("GdtDesert"), self.rows)
        self.assertIn('["BWh",3]', self.rows[normalise("GdtDesert")])

    def test_runtime_snow_votes_subarctic(self):
        self.assertIn('["Dfc",3]', self.rows[normalise("GdtSnow")])

    def test_no_dead_prefix_keys(self):
        self.assertFalse([k for k in self.rows if k.startswith("#")])


class TestGetBiomeAtPosition(unittest.TestCase):
    """fnc_getBiomeAtPosition Tier-1 direct surface map."""

    def setUp(self):
        code = code_only(read("biome_at_pos"))
        block = extract_block(code, "_DIRECT_MAP")
        self.direct = dict(re.findall(r'\["([^"]+)",\s*"(\w+)"\]', block))

    def test_runtime_desert_is_bwh(self):
        self.assertEqual(self.direct[normalise("GdtDesert")], "BWh")

    def test_runtime_tundra_is_et(self):
        self.assertEqual(self.direct[normalise("GdtTundra")], "ET")

    def test_candidate_map_keys_are_bare(self):
        code = code_only(read("biome_at_pos"))
        self.assertNotIn('"#Gdt', code)
        self.assertIn('["forest", switch', code)
        self.assertIn('["snow", switch', code)

    def test_no_dead_prefix_keys(self):
        self.assertFalse([k for k in self.direct if k.startswith("#")])


class TestNoLivePrefixedLiterals(unittest.TestCase):
    """Drift-lock: every '#gdt' left in the audited code is a guard literal.

    The only sanctioned use of the string "#gdt" is the normalisation guard
    `find "#gdt"`.  Any other occurrence is a dead comparison target.
    """

    def test_audited_files(self):
        for name in FILES:
            code = code_only(read(name))
            with self.subTest(file=name):
                self.assertEqual(
                    code.count("#gdt"),
                    code.count('find "#gdt"'),
                    f"{name}: a '#gdt' literal is not a normalisation guard",
                )


class TestNoMapNameMaterialLiterals(unittest.TestCase):
    """Drift-lock: no SQF string literal names a map surface.

    A map name as a surface token makes the comparison map-specific and
    unsourced.  The engine's own CfgSurfaces data is the source instead.
    A map name may appear only inside a comment.
    """

    MAP_NAMES = {
        "stratis",
        "altis",
        "malena",
        "malden",
        "tanoa",
        "livonia",
        "enoch",
        "weferlingen",
        "kunduz",
        "takistan",
        "chernarus",
        "sahrani",
        "utes",
        "carthage",
        "lythium",
    }

    EXTRA = (
        ADDON / "atmos" / "functions" / "physics" / "fnc_calculateTurbulence.sqf",
        ADDON / "material" / "functions" / "fnc_classifyBySurfaceType.sqf",
        ADDON / "material" / "functions" / "fnc_getSurfaceMaterial.sqf",
    )

    def test_no_map_name_material_literals(self):
        for path in sorted({*FILES.values(), *self.EXTRA}):
            code = code_only(path.read_text(encoding="utf-8"))
            literals = re.findall(r'"([^"]*)"', code)
            hits = sorted(
                literal for literal in literals if literal.lower() in self.MAP_NAMES
            )
            with self.subTest(file=path.name):
                self.assertEqual(
                    hits,
                    [],
                    f"{path.name}: map name inside a string literal: {hits}",
                )


if __name__ == "__main__":
    unittest.main()
