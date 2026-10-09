#!/usr/bin/env python3
"""Self-test for tools/compartmentalise/rewrite_paths.py.

Run as a script or under unittest:

    python3 tools/compartmentalise/test_rewrite_paths.py
    python3 -m unittest tools/compartmentalise/test_rewrite_paths.py

Every rewrite assertion uses a temporary tree with synthetic maps, never the
real repository.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rewrite_paths as rw  # noqa: E402


def _write_tree(
    root: Path,
    addon_map: dict,
    settings_map: dict,
    texts: dict[str, str],
    dest_dirs: set[str],
) -> None:
    maps_dir = root / "docs" / "architecture"
    maps_dir.mkdir(parents=True, exist_ok=True)
    (maps_dir / "addon-map.json").write_text(json.dumps(addon_map), encoding="utf-8")
    (maps_dir / "settings-map.json").write_text(
        json.dumps(settings_map), encoding="utf-8"
    )
    for addon in dest_dirs:
        (root / "addons" / addon).mkdir(parents=True, exist_ok=True)
    for rel, text in texts.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _run(
    root: Path, *, apply: bool, step: int | None = None, to: str | None = None
) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return rw.run(root, apply=apply, step=step, to=to)


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def _maps(
    files: dict[str, str] | None = None,
    data: dict | None = None,
    symbols: dict | None = None,
    addons: dict | None = None,
    targets: list[str] | None = None,
) -> dict:
    return {
        "version": 1,
        "target_addons": targets or ["optics", "eye"],
        "addons": addons or {},
        "files": files or {},
        "data": data or {},
        "symbols": symbols or {},
    }


class TestRewritePaths(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="rwpaths-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_one_pair_rewrites_only_the_mapped_occurrence(self) -> None:
        addon_map = _maps(
            files={
                "addons/optics/functions/eye/fnc_eyeThing.sqf": "eye",
                "addons/optics/functions/eye/fnc_stayThing.sqf": "optics",
            }
        )
        settings_map = {"settings": {}}
        text = (
            "load addons/optics/functions/eye/fnc_eyeThing.sqf\n"
            "load addons/optics/functions/eye/fnc_stayThing.sqf\n"
            "load addons/optics/functions/eye/fnc_eyeThing.sqf\n"
        )
        _write_tree(
            self.root,
            addon_map,
            settings_map,
            {"addons/optics/consumer.sqf": text},
            {"eye"},
        )

        self.assertEqual(_run(self.root, apply=True), 0)
        got = _read(self.root, "addons/optics/consumer.sqf")
        self.assertEqual(got.count("addons/eye/functions/eye/fnc_eyeThing.sqf"), 2)
        self.assertNotIn("addons/optics/functions/eye/fnc_eyeThing.sqf", got)
        self.assertIn("addons/optics/functions/eye/fnc_stayThing.sqf", got)

    def test_apply_is_idempotent(self) -> None:
        addon_map = _maps(
            files={
                "addons/optics/functions/eye/fnc_eyeThing.sqf": "eye",
            }
        )
        text = "load addons/optics/functions/eye/fnc_eyeThing.sqf\n"
        _write_tree(
            self.root,
            addon_map,
            {"settings": {}},
            {"addons/optics/consumer.sqf": text},
            {"eye"},
        )

        self.assertEqual(_run(self.root, apply=True), 0)
        once = _read(self.root, "addons/optics/consumer.sqf")
        self.assertEqual(_run(self.root, apply=True), 0)
        twice = _read(self.root, "addons/optics/consumer.sqf")
        self.assertEqual(once, twice)
        self.assertEqual(_run(self.root, apply=False), 0)

    def test_check_pending_then_clean(self) -> None:
        addon_map = _maps(
            files={
                "addons/optics/functions/eye/fnc_eyeThing.sqf": "eye",
            }
        )
        _write_tree(
            self.root,
            addon_map,
            {"settings": {}},
            {
                "addons/optics/consumer.sqf": "addons/optics/functions/eye/fnc_eyeThing.sqf\n"
            },
            {"eye"},
        )

        self.assertEqual(_run(self.root, apply=False), 1)
        self.assertEqual(_run(self.root, apply=True), 0)
        self.assertEqual(_run(self.root, apply=False), 0)

    def test_no_misfire_when_destination_addon_is_absent(self) -> None:
        addon_map = _maps(
            files={
                "addons/optics/functions/eye/fnc_eyeThing.sqf": "eye",
            }
        )
        text = "addons/optics/functions/eye/fnc_eyeThing.sqf\n"
        _write_tree(
            self.root,
            addon_map,
            {"settings": {}},
            {"addons/optics/consumer.sqf": text},
            set(),
        )
        self.assertEqual(_run(self.root, apply=False), 0)
        self.assertEqual(_run(self.root, apply=True), 0)
        self.assertEqual(_read(self.root, "addons/optics/consumer.sqf"), text)

    def test_efunc_and_egvar_component_repointing(self) -> None:
        addon_map = _maps(
            files={"addons/core/functions/geo/fnc_utmToWorld.sqf": "lib"},
            symbols={"aee_optics_symbologyTables": "symbology"},
            targets=["core", "optics", "lib", "symbology"],
        )
        text = (
            "EFUNC(core,utmToWorld)\n"
            "EGVAR(optics,symbologyTables)\n"
            "EFUNC(core,getSmoothedWeather)\n"
            "EFUNC(core,utmToWorldExtra)\n"
        )
        _write_tree(
            self.root,
            addon_map,
            {"settings": {}},
            {"addons/core/consumer.sqf": text},
            {"lib", "symbology"},
        )

        self.assertEqual(_run(self.root, apply=True), 0)
        got = _read(self.root, "addons/core/consumer.sqf")
        self.assertIn("EFUNC(lib,utmToWorld)", got)
        self.assertIn("EGVAR(symbology,symbologyTables)", got)
        self.assertIn("EFUNC(core,getSmoothedWeather)", got)
        self.assertIn("EFUNC(core,utmToWorldExtra)", got)
        self.assertNotIn("EFUNC(core,utmToWorld)", got)

    def test_setting_name_uses_word_boundaries(self) -> None:
        addon_map = _maps(targets=["optics", "hud", "core"])
        settings_map = {
            "settings": {
                "aee_optics_hudEnabled": "aee_hud_hudEnabled",
                "aee_core_enabled": "aee_core_enabled",
            }
        }
        text = (
            "aee_optics_hudEnabled\n"
            "aee_optics_hudEnabledExtra\n"
            "aee_optics_hudEnabledMore\n"
            "aee_core_enabled\n"
        )
        _write_tree(
            self.root,
            addon_map,
            settings_map,
            {"addons/optics/consumer.sqf": text},
            {"hud"},
        )

        self.assertEqual(_run(self.root, apply=True), 0)
        got = _read(self.root, "addons/optics/consumer.sqf")
        self.assertEqual(got.count("aee_hud_hudEnabled"), 1)
        self.assertIn("aee_optics_hudEnabledExtra", got)
        self.assertIn("aee_optics_hudEnabledMore", got)
        self.assertIn("aee_core_enabled", got)

    def test_path_and_backslash_prefix_repointing(self) -> None:
        addon_map = _maps(
            data={
                "addons/optics/data/terrain/**": {
                    "destination": "cartography",
                    "files": 1,
                }
            },
            addons={"main": {"verdict": "INFRASTRUCTURE", "destinations": ["lib"]}},
            targets=["optics", "cartography", "main", "lib"],
        )
        text = (
            "load addons/optics/data/terrain/x.paa\n"
            "load z\\aee\\addons\\optics\\data\\terrain\\x.paa\n"
            '#include "\\z\\aee\\addons\\main\\script_mod.hpp"\n'
        )
        _write_tree(
            self.root,
            addon_map,
            {"settings": {}},
            {"addons/optics/consumer.sqf": text},
            {"cartography", "lib"},
        )

        self.assertEqual(_run(self.root, apply=True), 0)
        got = _read(self.root, "addons/optics/consumer.sqf")
        self.assertIn("addons/cartography/data/terrain/x.paa", got)
        self.assertIn("z\\aee\\addons\\cartography\\data\\terrain\\x.paa", got)
        self.assertIn("\\z\\aee\\addons\\lib\\script_mod.hpp", got)
        self.assertNotIn("addons/optics/data/terrain", got)
        self.assertNotIn("addons\\main", got)

    def test_stringtable_key_when_the_module_moves(self) -> None:
        addon_map = _maps(targets=["optics", "eye"])
        settings_map = {
            "settings": {
                "aee_optics_eyeAdaptationEnabled": "aee_eye_eyeAdaptationEnabled",
            }
        }
        text = (
            "STR_AEE_Optics_eyeAdaptationEnabled_Name\n"
            "STR_AEE_Optics_eyeAdaptationEnabled_Description\n"
        )
        _write_tree(
            self.root,
            addon_map,
            settings_map,
            {"addons/optics/stringtable.xml": text},
            {"eye"},
        )

        self.assertEqual(_run(self.root, apply=True), 0)
        got = _read(self.root, "addons/optics/stringtable.xml")
        self.assertIn("STR_AEE_Eye_eyeAdaptationEnabled_Name", got)
        self.assertIn("STR_AEE_Eye_eyeAdaptationEnabled_Description", got)
        self.assertNotIn("STR_AEE_Optics_eyeAdaptationEnabled", got)

    def test_cli_check_and_apply_exit_codes(self) -> None:
        addon_map = _maps(
            files={
                "addons/optics/functions/eye/fnc_eyeThing.sqf": "eye",
            }
        )
        _write_tree(
            self.root,
            addon_map,
            {"settings": {}},
            {
                "addons/optics/consumer.sqf": "addons/optics/functions/eye/fnc_eyeThing.sqf\n"
            },
            {"eye"},
        )
        script = str(HERE / "rewrite_paths.py")

        def cli(mode: str) -> int:
            result = subprocess.run(
                [sys.executable, script, mode, "--root", str(self.root)],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode

        self.assertEqual(cli("--check"), 1)
        self.assertEqual(cli("--apply"), 0)
        self.assertEqual(cli("--check"), 0)

    def test_omo_evidence_tree_is_skipped(self) -> None:
        addon_map = _maps(
            files={
                "addons/optics/functions/eye/fnc_eyeThing.sqf": "eye",
            }
        )
        rewritten = "addons/optics/functions/eye/fnc_eyeThing.sqf\n"
        _write_tree(
            self.root,
            addon_map,
            {"settings": {}},
            {
                ".omo/evidence/note.txt": rewritten,
                "addons/optics/consumer.sqf": rewritten,
            },
            {"eye"},
        )

        self.assertEqual(_run(self.root, apply=False), 1)
        self.assertEqual(_run(self.root, apply=True), 0)
        self.assertEqual(_read(self.root, ".omo/evidence/note.txt"), rewritten)
        self.assertEqual(
            _read(self.root, "addons/optics/consumer.sqf"),
            "addons/eye/functions/eye/fnc_eyeThing.sqf\n",
        )


if __name__ == "__main__":
    unittest.main()
