#!/usr/bin/env python3
"""The AEE APP-6 mission-task, modifier and echelon marker contract tests.

Pins data/symbology/modifiers.json to the generated addons/symbology/config_modifiers.hpp
and to the marker .paa set, so the three cannot drift apart.  The mission-task name
set is checked against the standard list (MIL-STD-2525D TABLE H-XXIV plus the
FM 3-90 Appendix B graphics), so no invented task can enter the set.

Run: python3 -m unittest tools.tests.test_symbology_modifiers -v
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
CONFIG = REPO / "addons" / "symbology" / "config_modifiers.hpp"
JSON = REPO / "data" / "symbology" / "modifiers.json"
MARKERS = REPO / "addons" / "symbology" / "data" / "markers"

ADDON_PREFIX = "\\z\\aee\\addons\\symbology\\data\\markers\\"
PREFIX = {"mission_task": "AEE_MT_", "modifier": "AEE_MOD_", "echelon": "AEE_Ech_"}
EXPECTED_COUNTS = {"mission_task": 33, "modifier": 11, "echelon": 13}

# The complete canonical mission-task list the standard defines.  It includes the
# tasks that have no drawable graphic; those must be recorded as unavailable.
STANDARD_MISSION_TASKS = [
    "Mission_Tasks",
    "Block",
    "Breach",
    "Bypass",
    "Canalize",
    "Clear",
    "Counterattack",
    "Counterattack_by_Fire",
    "Delay",
    "Destroy",
    "Disrupt",
    "Fix",
    "Follow_and_Assume",
    "Follow_and_Support",
    "Interdict",
    "Isolate",
    "Neutralize",
    "Occupy",
    "Penetrate",
    "Relief_in_Place",
    "Retire",
    "Secure",
    "Security_Cover",
    "Security_Guard",
    "Security_Screen",
    "Seize",
    "Withdraw",
    "Under_Pressure",
    "Attack_by_Fire",
    "Ambush",
    "Contain",
    "Escort",
    "Exfiltrate",
    "Pursuit",
    "Reduce",
    "Retain",
    "Suppress",
    "Support_by_Fire",
    "Turn",
]


def load() -> dict:
    return json.loads(JSON.read_text(encoding="utf-8"))


def parse_config() -> dict[str, str]:
    """Parse config_modifiers.hpp into {class name: icon path}."""
    text = CONFIG.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for m in re.finditer(
        r"class (\w+): AEE_MarkerBase \{\s*"
        r'name = "[^"]*";\s*'
        r'icon = "([^"]+)";\s*'
        r'texture = "([^"]+)";',
        text,
    ):
        found[m.group(1)] = m.group(2)
    return found


def asset_name(icon: str) -> str:
    return icon.replace("\\", "/").rsplit("/", 1)[-1]


class TestRegistration(unittest.TestCase):
    """Every emitted marker is registered and backed by a real asset."""

    def setUp(self) -> None:
        self.doc = load()
        self.markers = self.doc["markers"]
        self.config = parse_config()

    def test_expected_counts_per_group(self) -> None:
        counts: dict[str, int] = {}
        for m in self.markers:
            counts[m["kind"]] = counts.get(m["kind"], 0) + 1
        self.assertEqual(counts, EXPECTED_COUNTS)
        self.assertEqual(self.doc["counts"], EXPECTED_COUNTS)

    def test_every_marker_is_registered(self) -> None:
        for m in self.markers:
            with self.subTest(marker=m["name"]):
                self.assertIn(m["name"], self.config)

    def test_config_has_no_orphan_classes(self) -> None:
        names = {m["name"] for m in self.markers}
        for cls in self.config:
            with self.subTest(cls=cls):
                self.assertIn(cls, names)

    def test_every_registered_asset_exists(self) -> None:
        for cls, icon in self.config.items():
            with self.subTest(cls=cls):
                self.assertTrue(
                    (MARKERS / asset_name(icon)).is_file(),
                    f"{cls} points at a missing asset {asset_name(icon)}",
                )

    def test_every_asset_carries_its_prefix(self) -> None:
        for m in self.markers:
            with self.subTest(marker=m["name"]):
                self.assertTrue(
                    m["name"].startswith(PREFIX[m["kind"]]),
                    f"{m['name']} must carry the {PREFIX[m['kind']]} prefix",
                )

    def test_every_icon_is_under_the_addon_prefix(self) -> None:
        for cls, icon in self.config.items():
            with self.subTest(cls=cls):
                self.assertTrue(icon.startswith(ADDON_PREFIX))


class TestMissionTaskSet(unittest.TestCase):
    """The mission-task set equals the standard list; no invented task."""

    def setUp(self) -> None:
        self.doc = load()
        self.emitted = {
            m["name"][len("AEE_MT_") :]
            for m in self.doc["markers"]
            if m["kind"] == "mission_task"
        }
        self.unavailable = {
            e["name"][len("AEE_MT_") :] for e in self.doc["unavailable"]
        }

    def test_union_equals_the_standard_list(self) -> None:
        self.assertEqual(self.emitted | self.unavailable, set(STANDARD_MISSION_TASKS))

    def test_no_invented_task(self) -> None:
        self.assertEqual(self.emitted - set(STANDARD_MISSION_TASKS), set())
        self.assertEqual(self.unavailable - set(STANDARD_MISSION_TASKS), set())

    def test_drawn_and_unavailable_are_disjoint(self) -> None:
        self.assertEqual(self.emitted & self.unavailable, set())

    def test_every_unavailable_task_has_a_reason_and_no_asset(self) -> None:
        config = parse_config()
        for e in self.doc["unavailable"]:
            with self.subTest(task=e["name"]):
                self.assertTrue(e.get("reason", "").strip())
                self.assertNotIn(e["name"], config)
                self.assertFalse((MARKERS / f"{e['name']}.paa").exists())


class TestModifierAndEchelonShape(unittest.TestCase):
    """The modifier and echelon groups are complete and well-formed."""

    def setUp(self) -> None:
        self.doc = load()

    def test_echelon_ladder_is_present_in_order(self) -> None:
        expected = [
            "Team",
            "Squad",
            "Section",
            "Platoon",
            "Company",
            "Battalion",
            "Regiment",
            "Brigade",
            "Division",
            "Corps",
            "Army",
            "Army_Group",
            "Region",
        ]
        got = [
            m["name"][len("AEE_Ech_") :]
            for m in self.doc["markers"]
            if m["kind"] == "echelon"
        ]
        self.assertEqual(got, expected)

    def test_modifier_set(self) -> None:
        expected = {
            "Strength_Reinforced",
            "Strength_Reduced",
            "Strength_Both",
            "Feint_Dummy",
            "Task_Force_Bracket",
            "HQ_Staff",
            "Installation",
            "Planned_Friend",
            "Planned_Hostile",
            "Planned_Neutral",
            "Planned_Unknown",
        }
        got = {
            m["name"][len("AEE_MOD_") :]
            for m in self.doc["markers"]
            if m["kind"] == "modifier"
        }
        self.assertEqual(got, expected)

    def test_license_is_declared(self) -> None:
        self.assertEqual(self.doc["license"], "GPL-2.0-or-later")
        self.assertIn("GPL-2.0-or-later", self.doc["geometry_license"])

    def test_every_marker_has_a_source_citation(self) -> None:
        for m in self.doc["markers"]:
            with self.subTest(marker=m["name"]):
                self.assertTrue(m.get("source", "").strip())
                self.assertTrue(m.get("description", "").strip())


if __name__ == "__main__":
    unittest.main()
