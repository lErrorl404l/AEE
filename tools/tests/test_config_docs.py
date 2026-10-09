#!/usr/bin/env python3
"""Freshness and completeness gate for the generated configuration chapter.

The generator once parsed only the explicit `[...] call CBA_fnc_addSetting`
blocks and missed every AEE_SETTING_* macro, so it found 24 of 196 settings
and truncated docs/wiki/chapters/configuration.qmd. These tests prove the
parser finds every declared setting from both registration forms, that the
committed chapter is fresh and complete, that a stale chapter fails the
check without being overwritten, and that a write never drops a documented
name.

Run: python3 -m unittest tools.tests.test_config_docs -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_config_docs as gen  # noqa: E402
from tools.validation import validate_cba_settings as validate  # noqa: E402

# Names the chapter documents that are not CBA settings, or that are kept as
# historical aliases. They must never disappear from the chapter.
PRESERVED_NAMES = (
    "aee_exhaustTier",
    "aee_exhaustAfterburner",
    "aee_enginePowerFraction",
    "aee_engineRatedPowerW",
    "aee_exhaustGasTempC",
    "aee_exhaustPlumeM",
    "aee_optics_nightGrainMax",
    "aee_optics_rainGrainMax",
    "aee_optics_fogGrainMax",
)

# The four thermal display settings the source registers as macros.
THERMAL_DISPLAY_NAMES = (
    "aee_thermal_thermalDisplayMode",
    "aee_thermal_thermalPalette",
    "aee_thermal_thermalManualMinC",
    "aee_thermal_thermalManualMaxC",
)


class ConfigDocsParserTest(unittest.TestCase):
    """The parser sees both registration forms and invents nothing."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = gen.collect_settings()
        cls.names = {setting.name for setting in cls.settings}

    def test_parser_finds_every_declared_setting(self) -> None:
        declared, _reads, _writes = validate.scan()
        self.assertEqual(self.names, set(declared))

    def test_parser_finds_macro_settings(self) -> None:
        # aee_thermal_objectScanInterval is a macro registration.
        self.assertIn("aee_thermal_objectScanInterval", self.names)
        self.assertIn("aee_fx_exhaustShimmerAlpha", self.names)

    def test_parser_finds_explicit_settings(self) -> None:
        # aee_core_enabled and aee_core_computeMode are explicit blocks.
        self.assertIn("aee_core_enabled", self.names)
        self.assertIn("aee_core_computeMode", self.names)

    def test_every_setting_carries_a_description(self) -> None:
        missing = [s.name for s in self.settings if not s.description]
        self.assertEqual(missing, [])

    def test_render_lists_every_setting(self) -> None:
        rendered = gen.render(self.settings)
        self.assertTrue(self.names.issubset(gen.names_in_doc(rendered)))

    def test_render_never_has_fewer_rows_than_settings(self) -> None:
        rendered = gen.render(self.settings)
        self.assertGreaterEqual(len(gen.names_in_doc(rendered)), len(self.settings))

    def test_every_setting_has_a_table_row(self) -> None:
        rendered = gen.render(self.settings)
        for setting in self.settings:
            with self.subTest(setting=setting.name):
                self.assertIn(f"| `{setting.name}` |", rendered)


class ConfigDocsChapterTest(unittest.TestCase):
    """The committed chapter is fresh, complete and protected."""

    def test_the_committed_chapter_is_fresh(self) -> None:
        self.assertEqual(gen.check(), 0)

    def test_the_cli_check_passes(self) -> None:
        self.assertEqual(gen.main(["--check"]), 0)

    def test_the_chapter_lists_every_setting(self) -> None:
        text = gen.DOC.read_text(encoding="utf-8")
        listed = gen.names_in_doc(text)
        missing = {setting.name for setting in gen.collect_settings()} - listed
        self.assertEqual(missing, set())

    def test_preserved_names_are_present(self) -> None:
        text = gen.DOC.read_text(encoding="utf-8")
        for name in PRESERVED_NAMES + THERMAL_DISPLAY_NAMES:
            with self.subTest(name=name):
                self.assertIn(name, text)

    def test_a_stale_chapter_fails_the_check_without_a_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stale = Path(tmp) / "configuration.qmd"
            stale.write_text("stale\n", encoding="utf-8")
            self.assertEqual(gen.check(stale), 1)
            self.assertEqual(stale.read_text(encoding="utf-8"), "stale\n")

    def test_a_missing_chapter_fails_the_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(gen.check(Path(tmp) / "absent.qmd"), 1)

    def test_write_produces_a_fresh_chapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "configuration.qmd"
            self.assertEqual(gen.write(doc), 0)
            self.assertEqual(gen.check(doc), 0)

    def test_write_refuses_to_drop_a_documented_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "configuration.qmd"
            doc.write_text(
                "| `aee_a_setting_no_longer_in_source` |\n", encoding="utf-8"
            )
            before = doc.read_text(encoding="utf-8")
            self.assertEqual(gen.write(doc), 1)
            self.assertEqual(doc.read_text(encoding="utf-8"), before)


class TestLogDebugSwitches(unittest.TestCase):
    """Every settings addon carries a logDebug switch and its two keys."""

    def test_every_settings_addon_has_the_switch_and_keys(self) -> None:
        files = sorted((REPO / "addons").glob("*/initSettings.inc.sqf"))
        self.assertEqual(len(files), 24)
        self.assertIn("core", {path.parent.name for path in files})
        for path in files:
            addon = path.parent
            with self.subTest(addon=addon.name):
                settings = path.read_text(encoding="utf-8")
                declares = (
                    "AEE_SETTING_CHECKBOX(logDebug," in settings
                    or "QGVAR(logDebug)," in settings
                )
                self.assertTrue(
                    declares,
                    f"{addon.name} declares no logDebug switch",
                )
                strings = (addon / "stringtable.xml").read_text(encoding="utf-8")
                self.assertIn(
                    "_logDebug_Name",
                    strings,
                    f"{addon.name} lacks the logDebug name key",
                )
                self.assertIn(
                    "_logDebug_Description",
                    strings,
                    f"{addon.name} lacks the logDebug description key",
                )


if __name__ == "__main__":
    unittest.main()
