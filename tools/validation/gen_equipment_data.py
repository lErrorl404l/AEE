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
import re
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).parents[2]
SRC = REPO / "data" / "equipment" / "sources"
OUT = REPO / "addons/physiology/functions/clothing/fnc_getItemMass.sqf"
BANDS_OUT = REPO / "addons/physiology/functions/clothing/fnc_getEquipmentBands.sqf"

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


def classifier_rows():
    """Researched weights from the slot classifiers, as table rows.

    The slot classifiers hold a researched weight for every family they
    know (helmet 60 keywords, vest 92, rucksack 34, goggle 41).  Those
    weights already cover the VANILLA classnames, which carry a generic
    name rather than a product name: a soldier wears H_HelmetB and
    V_PlateCarrier1, not "mich" or "spcs".  Without this the equipment
    table resolves none of them and the soldier's own kit weighs nothing.

    Seeding from the classifiers removes that gap without duplicating the
    research, and keeps one source of truth: the classifier states the
    value, and this reads it.
    """
    slots = (
        ("helmet", "fnc_getHelmetProperties.sqf"),
        ("vest", "fnc_getVestProperties.sqf"),
        ("rucksack", "fnc_getPackProperties.sqf"),
    )
    rows = []
    for category, filename in slots:
        path = REPO / "addons/physiology/functions/clothing" / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        body = re.search(r"switch \(true\) do \{(.*?)\n\};", text, re.S)
        if not body:
            continue
        for case in re.finditer(
            r"case\s*\((.*?)\):\s*\{\s*\[\s*([0-9.]+)", body.group(1), re.S
        ):
            weight = float(case.group(2))
            if weight <= 0:
                continue
            for keyword in re.findall(r'find "([^"]+)"', case.group(1)):
                keyword = keyword.strip().lower()
                if len(keyword) < MIN_FAMILY:
                    continue
                rows.append((keyword, category, "tier value", weight, 4))
    return rows


def load_rows():
    """Return (rows, skipped) from every capture in the source directory.

    A tier 5 source (a compilation, e.g. Wikipedia) is weaker than a maker
    page, but a labelled weak value beats a silent zero.  Such a row enters
    as grade "claimed" and is counted, so the confidence mix is visible.  A
    tier 1-4 value always displaces it for the same family and category.
    A physically impossible mass is rejected outright.
    """
    tier_of = {}
    collected = []
    skipped = {
        "tier5_kept": 0,
        "no_source": 0,
        "no_mass": 0,
        "no_family": 0,
        "non_ascii": 0,
        "no_category": 0,
        "impossible": 0,
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
            # A row without a category is a capture defect, not a lookup
            # miss: the row silently cannot match a filtered lookup.
            # medical_mass.json shipped 56 such rows, and the whole capture
            # was unusable for a category-filtered call until it was fixed.
            if not str(item.get("category", "")).strip():
                skipped["no_category"] += 1
                continue
            if not isinstance(mass, (int, float)) or mass <= 0:
                skipped["no_mass"] += 1
                continue
            # A hand-held item cannot exceed 40 kg and nothing carried on a
            # soldier is under a gram.  A value outside that band is a data
            # error, not a weak source, so it is rejected whatever the tier.
            if mass > 40 or mass < 0.001:
                skipped["impossible"] += 1
                continue
            tier = tier_of.get(source_id)
            if tier is None:
                skipped["no_source"] += 1
                continue
            claimed = tier >= 5
            if claimed:
                skipped["tier5_kept"] += 1
            category = str(item.get("category", "")).strip().lower()
            category = CATEGORY_ALIASES.get(category, category)
            state = str(item.get("state", "")).strip().lower()
            collected.append((family, category, state, float(mass), tier))
    return collected, skipped


def build_table(rows):
    """Group by (family, category) and take the median mass.

    A tier 1-4 value always displaces a tier 5 value for the same family
    and category, so a weak compilation can never override a maker page.
    Within one tier the median stands, which is the existing convention for
    a family with several published variants.
    """
    groups = {}
    for family, category, state, mass, tier in rows:
        groups.setdefault((family, category), []).append((state, mass, tier))
    table = []
    claimed_rows = 0
    for (family, category), entries in sorted(
        groups.items(), key=lambda kv: (-len(kv[0][0]), kv[0])
    ):
        # A published tier 1-4 figure beats a tier 5 compilation outright.
        strong = [e for e in entries if e[2] < 5]
        selected = strong if strong else entries
        if not strong:
            claimed_rows += 1
        masses = [mass for _state, mass, _tier in selected]
        # A rucksack enters the load EMPTY: fnc_getInventoryLoad weighs its
        # contents, so a filled mass would count the contents twice.
        if category == "rucksack":
            empty = [mass for state, mass, _tier in selected if "empty" in state]
            if empty:
                masses = empty
        table.append(
            (family, category, round(statistics.median(masses), 3), len(masses))
        )
    return table, claimed_rows


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

// The core addon stays ACE-free. A caller passes the categories it accepts
// when it holds the slot itself; an ACE category tag is not consulted here,
// because that convention belongs to the optional ACE layer.
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
private _familyCategory = "";
{
    _x params ["_familyName", "_category", "_mass"];
    if ((_allowed isEqualTo [] || {_category in _allowed}) && {_hay find _familyName >= 0}) exitWith {
        _match = _mass;
        _family = _familyName;
        _familyCategory = _category;
    };
} forEach _TABLE;

// The caller may know WHAT KIND of item this is.  A classifier registered
// by an optional layer answers it, and the caller's own category is the
// fallback.  A family of a different kind may not claim the item:
// kat_IO_FAST is an intraosseous drill, and without this it matched the
// helmet family "fast" and was weighed as headgear.
private _known = "";
{
    _known = [_item] call _x;
    if (_known != "") exitWith {};
} forEach (missionNamespace getVariable [QGVAR(categoryResolvers), []]);
if (_known == "" && _allowed isNotEqualTo []) then { _known = _allowed select 0; };
// Only a known category that the family contradicts is rejected.  An
// empty family category means the row states none, which is not a
// contradiction.
if (_known != "" && _familyCategory != "" && _familyCategory != _known) then {
    _match = 0;
    _family = "";
};

// ─── Band: the live item mass ────────────────────────────────────────────
// An item whose identity text carries no family keyword is matched by its
// own config mass against the researched family masses of its category.
// The config mass is the engine's identity signal, never a source value. A
// miss stays 0, exactly as before.
if ((_match == 0) && (_known != "")) then {
    private _liveMass = 0;
    {
        private _bandCfg = configFile >> _x >> _item;
        if (isClass _bandCfg) exitWith {
            _liveMass = getNumber (_bandCfg >> "mass");
            if (_liveMass <= 0) then {
                _liveMass = getNumber (_bandCfg >> "ItemInfo" >> "mass");
            };
        };
    } forEach ["CfgWeapons", "CfgVehicles", "CfgGlasses"];
    if (_liveMass > 0) then {
        private _band = [call FUNC(getEquipmentBands), _known, _liveMass, 0]
            call FUNC(selectBand);
        if (_band isNotEqualTo []) then {
            _match = _band select 2;
            _family = _band select 0;
        };
    };
};

// The trace names what resolved and, when nothing did, says so: an item
// that falls to 0 is the case a carried-load figure is hardest to explain.
private _logMsg = format ["item mass: %1 -> %2 kg (family '%3')", _item, _match, _family];
AEE_LOG_DEBUG(_logMsg);
_match
"""


BAND_TEMPLATE = """#include "..\\..\\script_component.hpp"
/*
Equipment identity band table. GENERATED FILE.

This is a runtime projection of the equipment research captures under
data/equipment/sources/. It is written by
tools/validation/gen_equipment_data.py and must not be edited by hand.

The band table is the property fallback of the item-mass resolver
aee_physiology_fnc_getItemMass. An item whose identity text carries no
family keyword is matched by its own engine config mass against the
researched family masses of its slot category. The category is the discrete
token, the published family mass is the primary selector, and the number of
published rows behind it is the payload. The selector reads the table and
the live property only. The engine mass is an identity signal, never a
source value.

A row has five columns:

  0 family       string, the family keyword, the stable key
  1 category     string, the slot category, the discrete token
  2 mass_kg      number, the published family mass in kg, 0 absent
  3 (reserved)   number, 0: no secondary property
  4 rows         number, the published rows behind the mass

Returns the band table, one row per family and category, longest family
first, as the matcher table is ordered.

Arguments: none.
Public: No
*/

private _table = [
__ROWS__
];

_table
"""


def build_equipment_table():
    """Return (table, claimed_rows, item_count, skipped) for the build."""
    rows, skipped = load_rows()
    # The captured research wins where it exists; the classifier tiers fill
    # the families the captures do not hold (the generic vanilla names).
    captured = {(f, c) for f, c, _s, _m, _t in rows}
    seeded = [r for r in classifier_rows() if (r[0], r[1]) not in captured]
    rows = rows + seeded
    table, claimed_rows = build_table(rows)
    return table, claimed_rows, len(rows), skipped


def render_match(table):
    body = ",\n".join('    ["{}", "{}", {}, {}]'.format(*row) for row in table)
    return TEMPLATE.replace("__ROWS__", body)


def render_bands(table):
    body = ",\n".join('    ["{}", "{}", {}, 0, {}]'.format(*row) for row in table)
    return BAND_TEMPLATE.replace("__ROWS__", body)


def write_outputs():
    table, claimed_rows, item_count, skipped = build_equipment_table()
    OUT.write_text(render_match(table), encoding="utf-8")
    BANDS_OUT.write_text(render_bands(table), encoding="utf-8")
    return table, claimed_rows, item_count, skipped


def check_outputs():
    """Return 0 when every generated file matches a fresh render."""
    table, _claimed, _items, _skipped = build_equipment_table()
    stale = False
    expected = ((OUT, render_match(table)), (BANDS_OUT, render_bands(table)))
    for path, text in expected:
        if not path.is_file():
            print(f"equipment projection: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"equipment projection: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(f"equipment projection: {len(table)} family rows and band rows (fresh)")
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--check" in argv:
        return check_outputs()
    table, claimed_rows, item_count, skipped = write_outputs()
    dropped = (
        skipped["no_source"]
        + skipped["no_mass"]
        + skipped["no_family"]
        + skipped["non_ascii"]
        + skipped["no_category"]
        + skipped["impossible"]
    )
    # The confidence mix is printed, so a table that leans on compilations
    # is visible in the build output rather than silently trusted.
    print(
        "equipment families: {} rows from {} items; "
        "{} row(s) grade claimed (tier 5, no stronger source); "
        "dropped {} {}; wrote {} and {}".format(
            len(table),
            item_count,
            claimed_rows,
            dropped,
            skipped,
            OUT.name,
            BANDS_OUT.name,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
