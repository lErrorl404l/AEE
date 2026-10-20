#!/usr/bin/env python3
"""Generate the runtime munition matcher and lookup from the catalogue.

The munition catalogue holds one entry per real munition, which is usually
a FAMILY: an article on the AGM-114 Hellfire states the Hellfire's figures,
and the derived designations let that entry name AGM-114K, AGM-114L and
AGM-114N alike. An entry carries a value, a unit, a source, a locator, a
state and a grade per field.

Two SQF files are written:

  addons/blast/functions/munition/fnc_getMunitionMatch.sqf  the ladder
  addons/blast/functions/munition/fnc_getMunitionData.sqf   the lookup

The ladder is the one every AEE matcher uses, so a munition from a mod
nobody has written yet resolves on the same rules as a base-game one:

  1 exact class   the normalised class equals a mapped game class
  2 alias         a query token equals a curated alias
  3 keyword       the query holds a derived designation
  4 closest       the best-scoring entry, with a strictly lower runner-up

The matcher reads the class name and the display name, nothing else. It
reads no config value as a figure. A missing value is a labelled zero, so
an entry the sources give nothing about still NAMES its munition and says
plainly that no figure is held. An unknown class and an ambiguous match
both return an empty array. There is no default.

A class that names equipment rather than a munition - a cockpit switch, a
targeting pod, a countermeasure discharger, an aircraft weapon bay - never
resolves. The kinds are the ones in tools/validation/munition_kind.py,
which the coverage tool shares, so the runtime and the measurement agree.

Run:  python3 tools/validation/gen_munition_data.py
      python3 tools/validation/gen_munition_data.py --check
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue
from tools.validation.identity_designations import designations as _designations
from tools.validation.identity_designations import fold as _fold
from tools.validation.munition_kind import SCREEN_TERMS

ROOT = _REPO
DATA = ROOT / "data" / "munition"
MATCH_OUT = (
    ROOT / "addons" / "blast" / "functions" / "munition" / "fnc_getMunitionMatch.sqf"
)
DATA_OUT = (
    ROOT / "addons" / "blast" / "functions" / "munition" / "fnc_getMunitionData.sqf"
)

# The shortest designation the substring layer will scan for. Three is the
# floor every AEE matcher uses: "S-8" folds to three characters and names a
# real rocket.
SCAN_MIN = 3
# A designation this many entries advertise names a CATEGORY, not a thing.
SHARED_WORD_MAX = 3

# The value fields the runtime row carries, in order. Each is a published
# figure or a labelled zero; none is ever estimated.
FIELDS = (
    "total_mass_kg",
    "warhead_mass_kg",
    "charge_mass_kg",
    "calibre_mm",
    "length_mm",
)
# The explosive filling, which is what gives the fragmentation kernel its
# Gurney energy. An empty string means no source names it.
TEXT_FIELDS = ("filling",)


def load() -> list[dict]:
    out = []
    for path in sorted((DATA / "catalogue").glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for entry in doc.get("entries", []):
            if entry.get("catalogue_id"):
                out.append(entry)
    return out


def row_designations(entries: list[dict]) -> dict[str, list[str]]:
    """Every designation each entry is published under, ambiguity removed.

    Two rules keep the derived set honest, and they are the ones the
    vehicle and aircraft matchers already use:

      RESERVED  a designation that IS another entry's whole folded name
                belongs to that entry alone. "Mk 82" must not be claimed
                by the Mk 80 series entry that also derives it.
      SHARED    a designation without a digit that more than three entries
                advertise names a category ("missile", "paveway"), and a
                category match makes every query ambiguous.
    """
    derived = {
        e["catalogue_id"]: _designations(
            e.get("canonical_name", ""), *(e.get("aliases") or [])
        )
        for e in entries
    }
    whole = {}
    for entry in entries:
        key = _fold(entry.get("canonical_name", ""))
        if key:
            whole.setdefault(key, entry["catalogue_id"])
    counts: dict[str, int] = {}
    for keys in derived.values():
        for key in set(keys):
            counts[key] = counts.get(key, 0) + 1
    shared = {
        key
        for key, n in counts.items()
        if n > SHARED_WORD_MAX and not any(c.isdigit() for c in key)
    }
    out = {}
    for cid, keys in derived.items():
        out[cid] = [
            key for key in keys if key not in shared and whole.get(key, cid) == cid
        ]
    return out


def number(entry: dict, field: str) -> float:
    value = (entry.get("values") or {}).get(field)
    if not value or not isinstance(value.get("value"), (int, float)):
        return 0.0
    return round(float(value["value"]), 4)


def text(entry: dict, field: str) -> str:
    value = (entry.get("values") or {}).get(field)
    if not value or not isinstance(value.get("value"), str):
        return ""
    return value["value"].replace('"', "'")


def source_of(entry: dict) -> str:
    for value in (entry.get("values") or {}).values():
        if value.get("source"):
            return str(value["source"])
    return ""


def rows(entries: list[dict], family_words: frozenset[str] = frozenset()) -> list[str]:
    """Render the mark table. A family-owned designation is dropped here.

    A family entry owns its designation, so no mark may carry it: while both
    the GBU-31 and the GBU-38 published JDAM, every query naming the munition
    family tied and no mark could answer.
    """
    keys = row_designations(entries)
    out = []
    for entry in sorted(entries, key=lambda e: e["catalogue_id"]):
        cid = entry["catalogue_id"]
        aliases = "|".join(
            sorted(
                {
                    _fold(a)
                    for a in (entry.get("aliases") or [])
                    if _fold(a) and _fold(a) not in family_words
                }
            )
        )
        keywords = "|".join(k for k in keys[cid] if k not in family_words)
        classes = "|".join(
            sorted({_fold(c) for c in (entry.get("classes") or []) if _fold(c)})
        )
        values = ", ".join(f"{number(entry, f):g}" for f in FIELDS)
        extra = ", ".join(f'"{text(entry, f)}"' for f in TEXT_FIELDS)
        out.append(
            f'    ["{cid}", "{entry.get("munition_type", "")}", "{classes}", '
            f'"{aliases}", "{keywords}", "{source_of(entry)}", '
            f"[{values}, {extra}]]"
        )
    return out


def is_family(entry: dict) -> bool:
    """True when the entry names a family and no mark."""
    return entry.get("family") is True


def family_rows(entries: list[dict]) -> list[str]:
    """The family table: identity-only rows that name a family and no mark.

    A family row carries no class, no alias, no source and no value. Its
    designation is the entry's own keyword list and is never derived, so a
    family cannot pick up a mark's term from a name.
    """
    out = []
    for entry in sorted(entries, key=lambda e: e["catalogue_id"]):
        keywords = "|".join(
            sorted({_fold(key) for key in (entry.get("keywords") or []) if _fold(key)})
        )
        values = ", ".join(f"{0:g}" for _ in FIELDS)
        extra = ", ".join('""' for _ in TEXT_FIELDS)
        out.append(
            f'    ["{entry["catalogue_id"]}", "{entry.get("munition_type", "")}", '
            f'"", "", "{keywords}", "", [{values}, {extra}]]'
        )
    return out


MATCH_TEMPLATE = """#include "..\\..\\script_component.hpp"
/*
Munition identity matcher.

Function: aee_blast_fnc_getMunitionMatch.

This file is GENERATED. The generator tools/validation/gen_munition_data.py
writes it from the munition catalogue under data/munition/. Do not edit it
by hand. Edit the corpus and regenerate it.

What a round carries is a real, published figure, and the blast and
fragmentation kernels need it. This resolves a game class - vanilla, modded
or one nobody has written yet - to the real munition it names, using only
the text the class carries: its classname and its display name. No per-mod
class list exists anywhere in this file.

An entry is usually a FAMILY: the AGM-114 Hellfire row answers for
AGM-114K, AGM-114L and AGM-114N, because the figures the sources publish
are the family's.

The ladder, in order:

  1 exact class   the normalised class equals a mapped game class
  2 alias         a query token equals a curated alias
  3 keyword       the query holds a derived designation of at least {scan}
                  characters
  4 closest       the best-scoring entry, where a designation carrying a
                  type number counts double because a type number
                  identifies while a plain word only describes
  5 family        the class text names a family and no mark: exactly one
                  row of the family table carries a designation of {scan}
                  or more characters in the query. A family row is
                  identity-only and answers only when it is the only
                  one, so it never takes an answer from a mark

An ambiguous match returns an empty array, and so does an unknown class.
There is no default: the caller falls back on its own documented estimate
and says so.

Returns [catalogue_id, munition_type, confidence, matched_by, source, values],
or an empty array. The value row is
[totalMassKg, warheadMassKg, chargeMassKg, calibreMm, lengthMm, filling]
and a zero or an empty string means the corpus holds no published figure
for that field.

A class that names equipment rather than a munition - a cockpit switch, a
targeting pod, a countermeasure discharger, an aircraft weapon bay - returns
an empty array whatever it declares. The kinds are the ones in
tools/validation/munition_kind.py, so the runtime and the coverage
measurement share one filter.

Arguments:
  0: className (STRING, a CfgAmmo, CfgMagazines or CfgWeapons classname,
     default "")
*/
params [["_className", "", [""]]];
if (_className == "") exitWith {{ [] }};

private _normalise = {{
    params ["_text"];
    private _out = "";
    {{
        if ((_x >= 48 && _x <= 57) || (_x >= 97 && _x <= 122)) then {{
            _out = _out + toString [_x];
        }};
    }} forEach (toArray (toLower _text));
    _out
}};

private _key = [_className] call _normalise;
if (_key == "") exitWith {{ [] }};

// Identity text only: the classname and the display name, read from
// whichever config root declares the class. Vehicle armament is spread
// across CfgAmmo, CfgMagazines and CfgWeapons, and a vanilla class stores
// a $STR key in displayName, so the localised text is read too. None of
// this carries a figure.
private _rawName = "";
{{
    private _entry = configFile >> _x >> _className;
    if (isClass _entry) exitWith {{
        _rawName = getText (_entry >> "displayName");
        if (_rawName == "") then {{ _rawName = getText (_entry >> "displayNameShort"); }};
    }};
}} forEach ["CfgAmmo", "CfgMagazines", "CfgWeapons"];
private _localName = if ((_rawName select [0,1]) == "$") then {{ localize _rawName }} else {{ _rawName }};
private _identity = _className + " " + _rawName + " " + _localName;
private _query = [_identity] call _normalise;
private _tokens = [];
{{
    private _token = _x call _normalise;
    if (_token != "") then {{ _tokens pushBack _token; }};
}} forEach (_identity splitString " _-.");

// Kind screen. A class that names equipment rather than a munition
// never resolves, whatever it declares. The terms are the folded kinds in
// tools/validation/munition_kind.py, which the coverage tool shares.
private _screened = false;
{{
    if (_query find _x >= 0) exitWith {{ _screened = true; }};
}} forEach {screen};

if (_screened) exitWith {{ [] }};

private _table = [
{rows}
];

// Family rows. A family entry names a family and no mark, so it is
// identity-only and lives in its own table: no layer above can reach it,
// and the last layer alone reads it. The columns are the ones above.
private _families = [
{families}
];

private _result = {{
    params ["_row", "_confidence", "_layer"];
    [_row select 0, _row select 1, _confidence, _layer, _row select 5, _row select 6]
}};

private _candidates = [];

// Layer 1: exact class.
{{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (((_classes splitString "|") find _key) >= 0) then {{
        _candidates pushBack _x;
    }};
}} forEach _table;
if ((count _candidates) == 1) exitWith {{ [_candidates select 0, 1, "exact_class"] call _result }};
if ((count _candidates) > 1) exitWith {{ [] }};

// Layer 2: alias. A query token equals a curated alias.
_candidates = [];
{{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {{
        if (_x in _tokens) then {{ _hit = true; }};
    }} forEach (_aliases splitString "|");
    if (_hit) then {{ _candidates pushBack _row; }};
}} forEach _table;
if ((count _candidates) == 1) exitWith {{ [_candidates select 0, 2, "alias"] call _result }};
if ((count _candidates) > 1) exitWith {{ [] }};

// Layer 3: keyword. The query holds a derived designation.
_candidates = [];
{{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {{
        if ((count _x) >= {scan} && {{_query find _x >= 0}}) then {{ _hit = true; }};
    }} forEach ((_aliases + "|" + _keywords) splitString "|");
    if (_hit) then {{ _candidates pushBack _row; }};
}} forEach _table;
if ((count _candidates) == 1) exitWith {{ [_candidates select 0, 3, "keyword"] call _result }};
if ((count _candidates) > 1) exitWith {{ [] }};

// Layer 4: closest. The total of every designation of the entry that the
// query holds, with a type number worth double.
private _bestRow = [];
private _bestScore = 0;
private _runnerUp = 0;
private _bestCount = 0;
private _bestName = 0;
private _tie = false;
{{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _score = 0;
    private _count = 0;
    private _longest = 0;
    {{
        _count = _count + 1;
        if ((count _x) >= {scan} && {{_query find _x >= 0}}) then {{
            private _hasDigit = false;
            {{
                if (_x >= 48 && _x <= 57) exitWith {{ _hasDigit = true; }};
            }} forEach (toArray _x);
            _score = _score + (count _x) * ([1, 2] select _hasDigit);
        }};
        if ((count _x) > _longest) then {{ _longest = count _x; }};
    }} forEach ((_aliases + "|" + _keywords) splitString "|");
    if (_score >= {scan}) then {{
        if (_score > _bestScore) then {{
            _runnerUp = _bestScore;
            _bestScore = _score;
            _bestRow = _row;
            _bestCount = _count;
            _bestName = _longest;
            _tie = false;
        }} else {{
            if (_score == _bestScore) then {{
                // Equal evidence. The entry advertising FEWER designations
                // is the less qualified one, and failing that the entry
                // whose own longest designation is SHORTER carries the less
                // qualified name. When a query names the family but not the
                // mark, the family is the right answer.
                if (_count < _bestCount) then {{
                    _bestRow = _row;
                    _bestCount = _count;
                    _bestName = _longest;
                    _tie = false;
                }} else {{
                    if (_count == _bestCount) then {{
                        if (_longest < _bestName) then {{
                            _bestRow = _row;
                            _bestName = _longest;
                            _tie = false;
                        }} else {{
                            if (_longest == _bestName) then {{ _tie = true; }};
                        }};
                    }};
                }};
            }};
            if (_score < _bestScore && _score > _runnerUp) then {{
                _runnerUp = _score;
            }};
        }};
    }};
}} forEach _table;
if ((_bestRow isNotEqualTo []) && {{!_tie}} && _bestScore > _runnerUp) exitWith {{
    [_bestRow, 4, "closest"] call _result
}};

// Layer 5: family. The class text names a family and no mark. A family row
// is identity-only, so it carries no class, no alias and no value, and it
// is read here alone. The scan is the keyword rule, over the declared
// family designations. Exactly one candidate answers: two families in one
// query name no single family, and none names nothing.
_candidates = [];
{{
    _x params ["_catalogue", "_type", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {{
        if ((count _x) >= {scan} && {{_query find _x >= 0}}) then {{ _hit = true; }};
    }} forEach (_keywords splitString "|");
    if (_hit) then {{ _candidates pushBack _row; }};
}} forEach _families;
if ((count _candidates) == 1) exitWith {{ [_candidates select 0, 7, "family"] call _result }};
[]
"""

DATA_TEMPLATE = """#include "..\\..\\script_component.hpp"
/*
Munition runtime lookup.

Function: aee_blast_fnc_getMunitionData.

This file is GENERATED. The generator tools/validation/gen_munition_data.py
writes it from the munition catalogue under data/munition/. Do not edit it
by hand. Edit the corpus and regenerate it.

A thin consumer of aee_blast_fnc_getMunitionMatch: it returns the value row
of a unique match, or an empty array. It reads no config value and returns
no default.

The row is
[totalMassKg, warheadMassKg, chargeMassKg, calibreMm, lengthMm, filling].
A zero or an empty string means the corpus holds no published figure for
that field, which is a statement about the sources, never an estimate.

Arguments:
  0: className (STRING, a CfgAmmo, CfgMagazines or CfgWeapons classname,
     default "")
*/
params [["_className", "", [""]]];
if (_className == "") exitWith {{ [] }};

private _match = [_className] call FUNC(getMunitionMatch);
if (_match isEqualTo []) exitWith {{ [] }};
_match select 5
"""


def family_errors(entries: list[dict]) -> list[str]:
    """The shape a munition family entry must carry, as every corpus checks it."""
    errors: list[str] = []
    for entry in entries:
        if not is_family(entry):
            continue
        cid = str(entry.get("catalogue_id", "<none>"))
        family = entry.get("family")
        if not isinstance(family, bool):
            errors.append(f"catalogue {cid}: family must be true or false")
            continue
        errors.extend(vehicle_catalogue.family_shape_errors(cid, entry))
    return errors


def build() -> tuple[str, str]:
    entries = load()
    marks = [entry for entry in entries if not is_family(entry)]
    families = [entry for entry in entries if is_family(entry)]
    family_words = frozenset(
        _fold(word)
        for entry in families
        for word in (entry.get("keywords") or [])
        if _fold(word)
    )
    body = "\n".join(f"{row}," for row in rows(marks, family_words))
    body = body.rstrip(",")
    family_body = "\n".join(f"{row}," for row in family_rows(families))
    family_body = family_body.rstrip(",")
    screen = "[" + ", ".join(f'"{t}"' for t in SCREEN_TERMS) + "]"
    match = MATCH_TEMPLATE.format(
        rows=body, families=family_body, scan=SCAN_MIN, screen=screen
    )
    return match, DATA_TEMPLATE.format()


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    errors = family_errors(load())
    if errors:
        print("\n".join(errors))
        return 1
    match, data = build()
    n = len(load())
    if "--check" in args:
        stale = []
        for path, text in ((MATCH_OUT, match), (DATA_OUT, data)):
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        if stale:
            print(
                "munition projection: stale ("
                + ", ".join(stale)
                + "), run python3 tools/validation/gen_munition_data.py"
            )
            return 1
        families = sum(1 for entry in load() if is_family(entry))
        print(f"munition projection: {n - families} rows and {families} family rows (fresh)")
        return 0
    MATCH_OUT.write_text(match, encoding="utf-8")
    DATA_OUT.write_text(data, encoding="utf-8")
    families = sum(1 for entry in load() if is_family(entry))
    print(
        f"munition projection: {n - families} rows and {families} family rows -> "
        "fnc_getMunitionMatch.sqf and fnc_getMunitionData.sqf"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
