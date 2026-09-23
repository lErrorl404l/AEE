#!/usr/bin/env python3
"""The item-mass resolver and the inventory walk (the load library).

The generated fnc_getItemMass.sqf must project the research captures
under data/equipment/sources/ exactly.  This test recomputes the family
medians from the captures and compares them with the table in the SQF, so
a capture that lands without a regenerated projection fails the gate.

The walk (fnc_getInventoryLoad) must weigh the container contents, the
assigned slot items and the weapon attachments, and must skip the worn
slots, the carried weapons and the magazines - otherwise an item is
counted twice in the combined load.

Run: python3 -m unittest tools/tests/test_inventory_load.py
"""

import json
import re
import statistics
import unittest
from pathlib import Path

REPO = Path(__file__).parents[2]
CLOTHING = REPO / "addons/physiology/functions/clothing"
SOURCES = REPO / "data" / "equipment" / "sources"
FNC_ITEM = (CLOTHING / "fnc_getItemMass.sqf").read_text(encoding="utf-8")
FNC_WALK = (CLOTHING / "fnc_getInventoryLoad.sqf").read_text(encoding="utf-8")
FNC_EQUIP = (CLOTHING / "fnc_getEquipmentProperties.sqf").read_text(encoding="utf-8")
SLOT_FILES = [
    "fnc_getUniformProperties.sqf",
    "fnc_getVestProperties.sqf",
    "fnc_getHelmetProperties.sqf",
    "fnc_getPackProperties.sqf",
    "fnc_getGoggleProperties.sqf",
]
XEH = (REPO / "addons/physiology/XEH_PREP.hpp").read_text(encoding="utf-8")

CATEGORY_ALIASES = {"binoculars": "binocular", "binocs": "binocular"}
MIN_FAMILY = 3

# The lookalike fold, mirrored from the generator.
LOOKALIKES = str.maketrans(
    {
        "\u0430": "a",
        "\u0441": "c",
        "\u0435": "e",
        "\u043e": "o",
        "\u0440": "p",
        "\u0445": "x",
        "\u0443": "y",
        "\u0456": "i",
        "\u0455": "s",
        "\u0458": "j",
        "\u03b1": "a",
        "\u03bf": "o",
        "\u03c1": "p",
        "\u03b5": "e",
    }
)


def research_table():
    """The table the captures imply: median per family and category."""
    tier_of = {}
    groups = {}
    for path in sorted(SOURCES.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for source in doc.get("sources", []):
            tier_of.setdefault(source["source_id"], source.get("tier"))
        for item in doc.get("items", []):
            family = str(item.get("family", "")).strip().lower().translate(LOOKALIKES)
            mass = item.get("mass_kg")
            if len(family) < MIN_FAMILY or any(ord(c) > 127 for c in family):
                continue
            if not isinstance(mass, (int, float)) or mass <= 0:
                continue
            tier = tier_of.get(item.get("source_id"))
            if tier is None or tier >= 5:
                continue
            category = str(item.get("category", "")).strip().lower()
            category = CATEGORY_ALIASES.get(category, category)
            groups.setdefault((family, category), []).append(
                (str(item.get("state", "")).lower(), float(mass))
            )
    table = []
    for (family, category), entries in sorted(
        groups.items(), key=lambda kv: (-len(kv[0][0]), kv[0])
    ):
        masses = [mass for _state, mass in entries]
        if category == "rucksack":
            empty = [mass for state, mass in entries if "empty" in state]
            if empty:
                masses = empty
        table.append(
            (family, category, round(statistics.median(masses), 3), len(masses))
        )
    return table


def sqf_table():
    """The rows of the generated resolver."""
    rows = re.findall(
        r'\[\s*"([^"]+)",\s*"([^"]*)",\s*([0-9.]+),\s*(\d+)\s*\]', FNC_ITEM
    )
    return [(f, c, float(m), int(n)) for f, c, m, n in rows]


class TestResolverMatchesResearch(unittest.TestCase):
    def test_header_marks_generated(self):
        self.assertIn("GENERATED FILE", FNC_ITEM)
        self.assertIn("gen_equipment_data.py", FNC_ITEM)

    def test_table_equals_capture_medians(self):
        # The projection must equal the captures.  A capture that lands
        # without a regenerated resolver fails here.
        expected = research_table()
        self.assertEqual(
            sqf_table(),
            expected,
            "fnc_getItemMass.sqf is stale: run tools/validation/gen_equipment_data.py",
        )

    def test_table_not_empty_when_sources_exist(self):
        if list(SOURCES.glob("*.json")):
            self.assertGreater(len(sqf_table()), 0)

    def test_longest_family_first(self):
        # The resolver takes the first match, so the more specific
        # keyword must come first.
        lengths = [len(row[0]) for row in sqf_table()]
        self.assertEqual(lengths, sorted(lengths, reverse=True))

    def test_unknown_returns_zero(self):
        # The resolver must return 0, never a guess, for an unknown item.
        self.assertIn("private _match = 0;", FNC_ITEM)
        self.assertIn("_match\n", FNC_ITEM)

    def test_category_filter_supported(self):
        self.assertIn("_allowed isEqualTo []", FNC_ITEM)
        self.assertIn("_category in _allowed", FNC_ITEM)


class TestInventoryWalk(unittest.TestCase):
    def test_walk_reads_every_source(self):
        for command in (
            "items _unit",
            "assignedItems _unit",
            "hmd _unit",
            "binocular _unit",
            "primaryWeaponItems _unit",
            "secondaryWeaponItems _unit",
            "handgunItems _unit",
            "weaponCargo (unitBackpack _unit)",
        ):
            self.assertIn(command, FNC_WALK, f"walk misses {command}")

    def test_walk_skips_magazines(self):
        # Magazines are weighed by fnc_getMagazineLoad.
        self.assertIn('isClass (configFile >> "CfgMagazines" >> _x)', FNC_WALK)

    def test_walk_skips_worn_slots_and_weapons(self):
        # The slots and the carried weapons are counted elsewhere.
        self.assertIn("uniform _unit", FNC_WALK)
        self.assertIn("backpack _unit", FNC_WALK)
        self.assertIn("primaryWeapon _unit", FNC_WALK)
        self.assertIn("!(_x in _worn)", FNC_WALK)
        self.assertIn("!(_x in _held)", FNC_WALK)

    def test_walk_uses_both_resolvers(self):
        self.assertIn("[_x] call FUNC(getItemMass)", FNC_WALK)
        self.assertIn("[_x] call FUNC(getWeaponMass)", FNC_WALK)

    def test_ratio_defect_gone(self):
        # The engine `load` command returns 0..1 of the capacity, a
        # fraction and not a mass: it must not enter the combined load.
        self.assertNotIn("load (unitBackpack _unit)", FNC_EQUIP)
        self.assertIn("[_unit] call FUNC(getInventoryLoad)", FNC_EQUIP)

    def test_registered(self):
        for name in ("getItemMass", "getInventoryLoad"):
            self.assertIn(f"PREPS(clothing,{name})", XEH)

    def test_slots_consult_the_research_table(self):
        # The published family mass outranks the family tier.
        for name in SLOT_FILES:
            source = (CLOTHING / name).read_text(encoding="utf-8")
            self.assertIn("FUNC(getItemMass)", source, f"{name} misses the lookup")
            self.assertIn("_tier set [0, _mass", source, f"{name} misses the override")


class TestMagazineLoadRowShape(unittest.TestCase):
    """A magazinesAmmoFull row is [classname, round count, isLoaded, ...].

    The round count is the SECOND element.  Binding the third element
    (isLoaded, a Boolean) raised "max: Type Bool, expected Number" for
    every unit that carried a magazine, and the rounds never entered the
    load.  Docker phase 58 caught it once the probe gave a unit a magazine.
    """

    def test_count_is_the_second_element(self):
        src = (CLOTHING / "fnc_getMagazineLoad.sqf").read_text(encoding="utf-8")
        self.assertIn('params ["_magazine", "_count"]', src)
        self.assertNotIn('"_ammo", "_count", "_loaded"', src)

    def test_rounds_enter_the_total(self):
        src = (CLOTHING / "fnc_getMagazineLoad.sqf").read_text(encoding="utf-8")
        self.assertIn("(_count max 0) * _round / 1000", src)


if __name__ == "__main__":
    unittest.main()
