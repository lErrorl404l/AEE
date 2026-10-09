#!/usr/bin/env python3
"""Guard for the ADR-032 settings migration.

The compartmentalisation (docs/architecture/settings-map.json) renames every
setting to ``aee_<module>_<leaf>``.  A renamed CBA setting loses its stored
``profileNamespace`` value unless the value is copied before the setting
registers, so lib owns ``fnc_migrateLegacySettings.sqf`` (plan section 3).

This suite pins four contracts:

  1. the helper is PREP'd (registered) exactly once;
  2. the helper is guarded by the version flag and sets it exactly once;
  3. the migration is idempotent (a faithful Python model of the helper);
  4. when a destination addon exists, every rename into it has a migration
     entry and its old name is no longer declared as a live setting.

Contracts 1 to 3 hold on the unchanged tree.  Contract 4 is gated on the
destination addon directory: before the first ``git mv`` no destination addon
exists, so the check is vacuous, exactly as rewrite_paths.py is a no-op before
a move.  After a step moves files, the gate opens for that step's destinations.

The helper is located by GLOB under ``addons/``, so the step-1 ``main`` ->
``lib`` rename cannot break this suite.

Run: python3 -m unittest tools.tests.test_settings_migration -v
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ADDONS = REPO / "addons"
SETTINGS_MAP = REPO / "docs" / "architecture" / "settings-map.json"
ADDON_MAP = REPO / "docs" / "architecture" / "addon-map.json"

# The migration version tag.  The helper defaults _version to this tag and
# builds "aee_settings_migrated_v<version>" from it; the module call sites
# pass the same tag.  It is asserted here, in the helper source, and in the
# Python model, so the three cannot drift.
VERSION = "1"
FLAG_PREFIX = "aee_settings_migrated_v"
FLAG = FLAG_PREFIX + VERSION

_HELPER_GLOB = "*/functions/settings/fnc_migrateLegacySettings.sqf"
_PREP_RE = re.compile(
    r"\bPREP(?:S)?\(\s*(?:settings\s*,\s*)?migrateLegacySettings\s*\)"
)


def helper_paths() -> list[Path]:
    """The helper file, by glob so the main -> lib rename cannot break it."""
    return sorted(ADDONS.glob(_HELPER_GLOB))


def helper_source() -> str:
    paths = helper_paths()
    assert len(paths) == 1, f"expected one helper, found {paths}"
    return paths[0].read_text(encoding="utf-8")


def target_addons() -> set[str]:
    with ADDON_MAP.open(encoding="utf-8") as handle:
        return set(json.load(handle)["target_addons"])


def renamed_pairs() -> list[tuple[str, str]]:
    with SETTINGS_MAP.open(encoding="utf-8") as handle:
        settings = json.load(handle)["settings"]
    return [(old, new) for old, new in settings.items() if old != new]


def module_of(name: str, addons: set[str]) -> str | None:
    """``aee_<module>_<leaf>`` -> <module>, using the longest known addon name."""
    if not name.startswith("aee_"):
        return None
    rest = name[4:]
    matches = [a for a in addons if rest == a or rest.startswith(a + "_")]
    if not matches:
        return None
    return max(matches, key=len)


def declared_settings() -> dict[str, str]:
    """name -> declaring file, from the canonical validator scanner.

    ``validate_cba_settings.scan`` resolves GVAR/QGVAR and the AEE_SETTING_*
    macros against the owning addon, so a name it reports is a live
    ``CBA_fnc_addSetting`` registration in an ``initSettings.inc.sqf``.
    """
    from tools.validation import validate_cba_settings as v

    declared, _reads, _writes = v.scan()
    return declared


def migration_text() -> str:
    """The concatenated text of every per-module migration table."""
    chunks = [
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(ADDONS.rglob("settingsMigration.sqf"))
    ]
    return "\n".join(chunks)


def migrate(profile: dict, pairs, version: str = VERSION) -> bool:
    """Faithful transcription of fnc_migrateLegacySettings.sqf.

    ``profile`` models profileNamespace.  Returns True when this call ran the
    migration, False when the version flag was already set.
    """
    flag = FLAG_PREFIX + version
    if profile.get(flag, False):
        return False
    for old, new in pairs:
        if new not in profile and old in profile:
            profile[new] = profile[old]
    profile[flag] = True
    return True


class TestHelperRegistered(unittest.TestCase):
    def test_exactly_one_helper_exists(self):
        paths = helper_paths()
        self.assertEqual(len(paths), 1, f"expected one helper, found {paths}")

    def test_helper_is_prep_registered_once(self):
        registrations = []
        for path in sorted(ADDONS.glob("*/XEH_PREP.hpp")):
            text = path.read_text(encoding="utf-8")
            if _PREP_RE.search(text):
                registrations.append(path)
        self.assertEqual(
            [p.as_posix() for p in registrations],
            [p.as_posix() for p in registrations][:1],
            "the helper is PREP'd more than once",
        )
        self.assertEqual(len(registrations), 1, "the helper is not PREP'd")


class TestHelperContract(unittest.TestCase):
    def test_helper_reads_the_version_flag(self):
        src = helper_source()
        self.assertIn(FLAG_PREFIX, src)
        self.assertIn(
            "profileNamespace getVariable [_flag, false]",
            src,
            "the helper must guard on the version flag",
        )
        self.assertIn("exitWith { false }", src)

    def test_helper_defaults_to_the_asserted_version(self):
        src = helper_source()
        self.assertIn(f'["_version", "{VERSION}", [""]]', src)

    def test_version_flag_is_set_exactly_once(self):
        src = helper_source()
        self.assertEqual(src.count("setVariable [_flag, true]"), 1)
        # No other path sets the flag, e.g. a second "aee_settings_migrated_v".
        sets = re.findall(r"setVariable\s*\[\s*[\"']" + FLAG_PREFIX, src)
        self.assertEqual(sets, [])


class TestMigrationLogic(unittest.TestCase):
    """The logic demo: seed an old name, migrate, then prove idempotence."""

    def test_seed_migrates_and_flag_is_set_once(self):
        old, new = "aee_optics_hudEnabled", "aee_hud_hudEnabled"
        profile = {old: True}
        self.assertTrue(migrate(profile, [(old, new)]))
        self.assertEqual(profile[new], True)
        self.assertEqual(profile[FLAG], True)

    def test_second_call_is_a_no_op(self):
        old, new = "aee_optics_hudEnabled", "aee_hud_hudEnabled"
        profile = {old: True}
        migrate(profile, [(old, new)])
        snapshot = dict(profile)
        self.assertFalse(migrate(profile, [(old, new)]))
        self.assertEqual(profile, snapshot)

    def test_unset_old_name_is_skipped(self):
        profile: dict = {}
        self.assertTrue(
            migrate(profile, [("aee_optics_hudEnabled", "aee_hud_hudEnabled")])
        )
        self.assertNotIn("aee_hud_hudEnabled", profile)
        self.assertEqual(profile[FLAG], True)

    def test_set_new_name_wins(self):
        old, new = "aee_optics_hudEnabled", "aee_hud_hudEnabled"
        profile = {old: True, new: False}
        migrate(profile, [(old, new)])
        self.assertEqual(profile[new], False)


class TestMigrationCoverage(unittest.TestCase):
    """The tree-level contract, gated on the destination addon."""

    def setUp(self):
        self.targets = target_addons()
        self.enabled = {p.name for p in ADDONS.iterdir() if p.is_dir()}

    def gated(self) -> list[tuple[str, str, str]]:
        """(old, new, dest_module) for renames whose destination now exists."""
        out = []
        for old, new in renamed_pairs():
            dest = module_of(new, self.targets)
            if dest and dest in self.enabled:
                out.append((old, new, dest))
        return out

    def test_target_map_parses_every_new_name(self):
        unparsed = [
            new for _old, new in renamed_pairs() if module_of(new, self.targets) is None
        ]
        self.assertEqual(unparsed, [], f"target_addons cannot parse {unparsed}")

    def test_every_renamed_pair_into_an_existing_addon_has_a_migration_entry(self):
        text = migration_text()
        missing = []
        for old, new, _dest in self.gated():
            if f'"{old}"' not in text or f'"{new}"' not in text:
                missing.append((old, new))
        self.assertEqual(
            missing,
            [],
            f"renamed settings with no migration entry: {missing}",
        )

    def test_no_old_name_is_still_a_live_setting(self):
        declared = declared_settings()
        stale = [old for old, _new, _dest in self.gated() if old in declared]
        self.assertEqual(
            stale,
            [],
            f"renamed settings still registered as live knobs: {stale}",
        )


if __name__ == "__main__":
    unittest.main()
