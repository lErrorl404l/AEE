#!/usr/bin/env python3
"""Vehicle class inventory tests (vehicle research corpus, wave 1 task 1).

The inventory is identity evidence. It lists the class tokens the addon
code already branches on. It is derived from the code, never hand-written.

Run: python3 -m unittest tools.tests.test_vehicle_inventory -v
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
sys.path.insert(0, str(REPO))

from tools.validation import gen_vehicle_class_inventory as gen  # noqa: E402

ADDONS = REPO / "addons"
COMMITTED = REPO / "data" / "vehicle" / "classes.json"
GENERATOR = REPO / "tools" / "validation" / "gen_vehicle_class_inventory.py"

# The ground tokens the mobility and armour code branches on.
GROUND_TOKENS = ("Tank", "Tracked_APC", "Wheeled_APC", "Car", "Truck", "MRAP")
# The two explicit non-ground exclusions the plan names.
AIR_TOKENS = ("Air", "Helicopter")

PROVENANCE_RE = re.compile(r"^(?P<path>.+):(?P<line>[0-9]+)$")


def _by_token(payload):
    return {entry["token"]: entry for entry in payload["tokens"]}


class TestClassInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = gen.build_inventory(ADDONS)
        cls.tokens = _by_token(cls.payload)
        cls._line_cache = {}

    def _line(self, loc):
        match = PROVENANCE_RE.match(loc)
        self.assertIsNotNone(match, f"provenance is not file:line: {loc}")
        path = REPO / match.group("path")
        self.assertTrue(path.is_file(), f"provenance file is missing: {loc}")
        lines = self._line_cache.get(str(path))
        if lines is None:
            lines = path.read_text(encoding="utf-8").splitlines()
            self._line_cache[str(path)] = lines
        number = int(match.group("line"))
        self.assertLessEqual(
            number, len(lines), f"provenance line is out of range: {loc}"
        )
        return lines[number - 1]

    def test_ground_tokens_are_supported(self):
        for token in GROUND_TOKENS:
            self.assertIn(token, self.tokens, f"{token} is not in the inventory")
            self.assertTrue(self.tokens[token]["is_ground"], f"{token} is not ground")

    def test_air_tokens_are_not_ground(self):
        for token in AIR_TOKENS:
            self.assertIn(token, self.tokens, f"{token} is not in the inventory")
            self.assertFalse(
                self.tokens[token]["is_ground"], f"{token} is marked ground"
            )

    def test_every_token_has_provenance(self):
        self.assertTrue(self.tokens)
        for token, entry in self.tokens.items():
            self.assertTrue(entry["provenance"], f"{token} has no provenance")
            for loc in entry["provenance"]:
                self._line(loc)

    def test_provenance_points_at_the_token(self):
        # A provenance line must contain the token. A stale or invented
        # location fails here.
        for token, entry in self.tokens.items():
            self.assertTrue(
                any(f'"{token}"' in self._line(loc) for loc in entry["provenance"]),
                f"no provenance line states the token {token}",
            )

    def test_kind_is_a_closed_vocabulary(self):
        for token, entry in self.tokens.items():
            self.assertIn(entry["kind"], ("engine_base", "mod_token"), token)

    def test_kind_follows_the_reference_style(self):
        # A token the code asserts with isKindOf is an engine base token.
        # A token that occurs only in an addon table is a mod token.
        self.assertEqual(self.tokens["Car"]["kind"], "engine_base")
        self.assertEqual(self.tokens["Tank"]["kind"], "engine_base")
        self.assertEqual(self.tokens["MRAP"]["kind"], "mod_token")
        self.assertEqual(self.tokens["Wheeled_APC"]["kind"], "mod_token")

    def test_non_ground_tokens_have_a_reason(self):
        for token, entry in self.tokens.items():
            if entry["is_ground"]:
                self.assertIsNone(entry["exclusion_reason"], token)
            else:
                self.assertTrue(entry["exclusion_reason"], token)

    def test_a_fresh_build_is_deterministic(self):
        first = json.dumps(gen.build_inventory(ADDONS), sort_keys=True)
        second = json.dumps(gen.build_inventory(ADDONS), sort_keys=True)
        self.assertEqual(first, second)

    def test_committed_output_matches_a_fresh_build(self):
        self.assertTrue(COMMITTED.is_file(), f"{COMMITTED} is missing")
        committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
        self.assertEqual(committed, gen.build_inventory(ADDONS))

    def test_a_new_token_is_discovered_from_the_code(self):
        # A temp tree with one unknown literal proves the tool derives the
        # token set. A hand-written list would miss it.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "addons"
            (root / "mod" / "functions").mkdir(parents=True)
            (root / "mod" / "functions" / "fake.sqf").write_text(
                'if (_v isKindOf "NotAVehicle") then { true };\n', encoding="utf-8"
            )
            out = Path(tmp) / "classes.json"
            subprocess.run(
                [
                    sys.executable,
                    str(GENERATOR),
                    "--root",
                    str(root),
                    "--out",
                    str(out),
                ],
                check=True,
                cwd=str(REPO),
            )
            payload = json.loads(out.read_text(encoding="utf-8"))
            tokens = _by_token(payload)
            self.assertIn("NotAVehicle", tokens)
            self.assertFalse(tokens["NotAVehicle"]["is_ground"])
            self.assertTrue(tokens["NotAVehicle"]["provenance"])

    def test_two_cli_runs_are_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "first.json"
            second = Path(tmp) / "second.json"
            for out in (first, second):
                subprocess.run(
                    [sys.executable, str(GENERATOR), "--out", str(out)],
                    check=True,
                    cwd=str(REPO),
                )
            self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
