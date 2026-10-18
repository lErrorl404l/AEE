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

import ast
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


# The helper builds the flag with one format call.  A version-only flag
# ("%1") returns one key for every caller; a pair-set flag ("%1_%2") returns
# a key per module.  The rule is read from the helper source, so the
# simulation below cannot drift from the helper.
_FLAG_FORMAT_RE = re.compile(
    r'private _flag = format \["(aee_settings_migrated_v[^"]*)", _version(?:,\s*([^\]]+))?\]'
)
_PAIR_TAG_ASSIGNMENT = '_pairTag = (_pairs select 0) param [1, ""]'
_TABLE_COMMENT_RE = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)


def flag_rule(src: str):
    """The helper's flag key, as a ``key(version, pairs)`` callable."""
    match = _FLAG_FORMAT_RE.search(src)
    assert match is not None, "the helper must build the flag with format"
    template, tag = match.group(1), match.group(2)
    if "%2" not in template:
        return lambda version, pairs: template.replace("%1", version)
    assert tag is not None and _PAIR_TAG_ASSIGNMENT in src, (
        "a per-set flag must be keyed on the caller's pairs"
    )
    return lambda version, pairs: template.replace("%1", version).replace(
        "%2", str(pairs[0][1])
    )


def migration_tables() -> dict[str, list[tuple[str, str]]]:
    """module -> [oldName, newName] pairs, from every addon migration table."""
    tables: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(ADDONS.glob("*/data/settingsMigration.sqf")):
        text = _TABLE_COMMENT_RE.sub(" ", path.read_text(encoding="utf-8"))
        tables[path.parent.parent.name] = ast.literal_eval(text[text.index("[") :])
    return tables


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
        old, new = "aee_hud_hudEnabled", "aee_hud_hudEnabled"
        profile = {old: True}
        self.assertTrue(migrate(profile, [(old, new)]))
        self.assertEqual(profile[new], True)
        self.assertEqual(profile[FLAG], True)

    def test_second_call_is_a_no_op(self):
        old, new = "aee_hud_hudEnabled", "aee_hud_hudEnabled"
        profile = {old: True}
        migrate(profile, [(old, new)])
        snapshot = dict(profile)
        self.assertFalse(migrate(profile, [(old, new)]))
        self.assertEqual(profile, snapshot)

    def test_unset_old_name_is_skipped(self):
        profile: dict = {}
        self.assertTrue(
            migrate(profile, [("aee_hud_hudEnabled", "aee_hud_hudEnabled")])
        )
        self.assertNotIn("aee_hud_hudEnabled", profile)
        self.assertEqual(profile[FLAG], True)

    def test_set_new_name_wins(self):
        old, new = "aee_hud_hudEnabled", "aee_hud_hudEnabled"
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


class TestEveryModuleMigrates(unittest.TestCase):
    """Issue #249: the one-shot flag is per module, not global.

    Every module's XEH_preInit passes version "1" and its own pair table, so
    a flag keyed on the version alone let the first caller migrate and made
    every later table a silent no-op.  This test drives each module's real
    table through the flag rule the helper source implements.
    """

    def test_every_module_table_copies_its_renames(self):
        rule = flag_rule(helper_source())
        tables = migration_tables()
        self.assertGreaterEqual(len(tables), 20, f"found {len(tables)} tables")

        profile: dict = {}
        for _module, pairs in tables.items():
            for old, new in pairs:
                if old != new:
                    profile[old] = f"legacy:{old}"

        unmigrated = []
        for module, pairs in tables.items():
            renames = [(old, new) for old, new in pairs if old != new]
            self.assertTrue(renames, f"{module} declares no renamed pair")
            flag = rule(VERSION, pairs)
            if not profile.get(flag, False):
                for old, new in renames:
                    if new not in profile and old in profile:
                        profile[new] = profile[old]
                profile[flag] = True
            if any(profile.get(new) != f"legacy:{old}" for old, new in renames):
                unmigrated.append(module)

        self.assertEqual(
            unmigrated,
            [],
            f"modules whose legacy values did not migrate: {unmigrated}",
        )


class TestMigrationPrecedesRegistration(unittest.TestCase):
    """Issue #249, the second half: the copy must precede the registration.

    A module that includes initSettings.inc.sqf before the migration call
    registers the new names first, so CBA_fnc_addSetting reads the unset name
    and the copy lands too late.  symbology did exactly that, with the call
    wedged between two copies of the include: every symbology setting
    registered twice and no legacy value migrated.
    """

    @staticmethod
    def preinit_lines() -> dict[str, list[str]]:
        return {
            path.parent.name: path.read_text(encoding="utf-8").splitlines()
            for path in sorted(ADDONS.glob("*/XEH_preInit.sqf"))
        }

    def test_every_module_with_a_table_calls_the_migration(self):
        """A count lock: the call sites and the pair tables are the same set.

        A spot check passes while a module is skipped; this fails on the one
        module left out, in either direction.
        """
        callers = {
            module
            for module, lines in self.preinit_lines().items()
            if any("migrateLegacySettings" in line for line in lines)
        }
        self.assertEqual(
            callers,
            set(migration_tables()),
            "the modules that call the migration and the modules that declare "
            "a pair table differ",
        )

    def test_every_migration_call_precedes_the_settings_include(self):
        late = []
        for module, lines in self.preinit_lines().items():
            call = [
                index
                for index, line in enumerate(lines)
                if "migrateLegacySettings" in line and line.strip().startswith("[")
            ]
            register = [
                index
                for index, line in enumerate(lines)
                if "#include" in line and "initSettings.inc.sqf" in line
            ]
            if call and (not register or call[0] > register[0]):
                late.append(module)
        self.assertEqual(
            late, [], f"modules that register their settings before migrating: {late}"
        )

    def test_the_settings_include_appears_once(self):
        """A second include re-registers every setting under the same name."""
        repeated = {}
        for module, lines in self.preinit_lines().items():
            count = sum(
                1
                for line in lines
                if "#include" in line and "initSettings.inc.sqf" in line
            )
            if count > 1:
                repeated[module] = count
        self.assertEqual(
            repeated,
            {},
            f"modules that include the settings more than once: {repeated}",
        )


if __name__ == "__main__":
    unittest.main()
