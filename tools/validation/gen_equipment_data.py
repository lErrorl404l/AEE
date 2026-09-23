#!/usr/bin/env python3
"""Generate the item-mass resolver for the load-carriage library.

Every research capture lands as one JSON file under
data/equipment/sources/ (see data/equipment/SCHEMA.md). The generator
reads them all, so a new file joins the build with no code change.

A classname carries a family keyword (pvs14, peq15, prc152, alice). The
table holds the median published mass for each family and category, with
the number of published rows behind it. A product family with published
variants therefore resolves to its family tier, the same convention the
equipment library already uses for helmets, vests and packs.

Nothing is averaged across sources: a same-item disagreement is recorded
in the capture's `conflicts` list and the higher tier value stays on the
item. A tier 5 capture is a lead only, so its items are dropped here too.

Run:  python3 tools/validation/gen_equipment_data.py
"""

import json
import statistics
from pathlib import Path

REPO = Path(__file__).parents[2]
SRC = REPO / "data" / "equipment" / "sources"
OUT = REPO / "addons/physiology/functions/clothing/fnc_getItemMass.sqf"

# One spelling per category. The capture may use the plural.
CATEGORY_ALIASES = {"binoculars": "binocular", "binocs": "binocular"}

# A shorter family would match unrelated classnames.
MIN_FAMILY = 3

# Non-Latin letters that look like Latin ones. A keyword that carries a
# lookalike character can never match a classname, so it is folded here.
LOOKALIKES = str.maketrans(
    {
        "\u0430": "a",  # CYRILLIC A
        "\u0441": "c",  # CYRILLIC ES
        "\u0435": "e",  # CYRILLIC IE
        "\u043e": "o",  # CYRILLIC O
        "\u0440": "p",  # CYRILLIC ER
        "\u0445": "x",  # CYRILLIC HA
        "\u0443": "y",  # CYRILLIC U
        "\u0456": "i",  # CYRILLIC I
        "\u0455": "s",  # CYRILLIC DZE
        "\u0458": "j",  # CYRILLIC JE
        "\u03b1": "a",  # GREEK ALPHA
        "\u03bf": "o",  # GREEK OMICRON
        "\u03c1": "p",  # GREEK RHO
        "\u03b5": "e",  # GREEK EPSILON
    }
)


def load_rows():
    """Return (rows, skipped) from every capture in the source directory."""
    tier_of = {}
    collected = []
    skipped = {
        "tier5": 0,
        "no_source": 0,
        "no_mass": 0,
        "no_family": 0,
        "non_ascii": 0,
    }
    for path in sorted(SRC.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for source in doc.get("sources", []):
            tier_of.setdefault(source["source_id"], source.get("tier"))
        for item in doc.get("items", []):
            family = str(item.get("family", "")).strip().lower()
            family = family.translate(LOOKALIKES)
            mass = item.get("mass_kg")
            source_id = item.get("source_id")
            if any(ord(character) > 127 for character in family):
                skipped["non_ascii"] += 1
                continue
            if len(family) < MIN_FAMILY:
                skipped["no_family"] += 1
                continue
            if not isinstance(mass, (int, float)) or mass <= 0:
                skipped["no_mass"] += 1
                continue
            tier = tier_of.get(source_id)
            if tier is None:
                skipped["no_source"] += 1
                continue
            if tier >= 5:
                skipped["tier5"] += 1
                continue
            category = str(item.get("category", "")).strip().lower()
            category = CATEGORY_ALIASES.get(category, category)
            state = str(item.get("state", "")).strip().lower()
            collected.append((family, category, state, float(mass)))
    return collected, skipped


def build_table(rows):
    """Group by (family, category) and take the median mass."""
    groups = {}
    for family, category, state, mass in rows:
        groups.setdefault((family, category), []).append((state, mass))
    table = []
    for (family, category), entries in sorted(
        groups.items(), key=lambda kv: (-len(kv[0][0]), kv[0])
    ):
        masses = [mass for _state, mass in entries]
        # A rucksack enters the load EMPTY: fnc_getInventoryLoad weighs its
        # contents, so a filled mass would count the contents twice.
        if category == "rucksack":
            empty = [mass for state, mass in entries if "empty" in state]
            if empty:
                masses = empty
        table.append(
            (family, category, round(statistics.median(masses), 3), len(masses))
        )
    return table


TEMPLATE = """#include "..\\..\\script_component.hpp"
/*
Item mass (the load-carriage library). GENERATED FILE.

This is a runtime projection of the equipment research captures under
data/equipment/sources/. It is written by
tools/validation/gen_equipment_data.py and must not be edited by hand.

A classname carries a family keyword (pvs14, peq15, prc152, alice). The
table holds the median published mass for each family and category, with
the number of published rows behind it. A classname that carries no known
family returns 0: the item is unknown, not guessed, and the coverage test
reports it.

A caller that knows the slot category passes it as the second argument, so
a family keyword shared by two categories (a pack and a belt named ALICE)
resolves to the right row.

Arguments:
  0: item (STRING, a classname, default "")
  1: allowed categories (ARRAY of STRING, default [] = any)

Returns the published mass in kg, or 0 when no family matches.
*/

params [["_item", "", [""]], ["_allowed", [], [[]]]];
if (_item == "") exitWith { 0 };

private _hay = toLower _item;
{
    private _cfg = configFile >> _x >> _item;
    if (isClass _cfg) exitWith {
        _hay = _hay + " " + toLower (getText (_cfg >> "displayName"));
    };
} forEach ["CfgWeapons", "CfgVehicles", "CfgGlasses"];

// [family keyword, category, published mass kg, published rows]
private _TABLE = [
__ROWS__
];

// The table is ordered longest family first, so the more specific keyword
// wins (an "lv-119" row outranks a "119" row).
private _match = 0;
private _family = "";
{
    _x params ["_familyName", "_category", "_mass"];
    if ((_allowed isEqualTo [] || {_category in _allowed})
        && {_hay find _familyName >= 0}) exitWith {
        _match = _mass;
        _family = _familyName;
    };
} forEach _TABLE;

// The trace names what resolved and, when nothing did, says so: an item
// that falls to 0 is the case a carried-load figure is hardest to explain.
private _logMsg = format ["item mass: %1 -> %2 kg (family '%3')", _item, _match, _family];
AEE_LOG_DEBUG(_logMsg);
_match
"""


def main():
    rows, skipped = load_rows()
    table = build_table(rows)
    body = ",\n".join('    ["{}", "{}", {}, {}]'.format(*row) for row in table)
    OUT.write_text(TEMPLATE.replace("__ROWS__", body), encoding="utf-8")
    dropped = sum(skipped.values())
    print(
        "equipment families: {} rows from {} items; skipped {} {}; "
        "wrote {} ({} bytes)".format(
            len(table), len(rows), dropped, skipped, OUT.name, OUT.stat().st_size
        )
    )


if __name__ == "__main__":
    main()
