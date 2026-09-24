#!/usr/bin/env python3
"""Generate the runtime vehicle matcher and lookup from the catalogue.

The vehicle catalogue holds one entry per real vehicle variant. An entry
carries a value, a unit, a source, a locator, a state and a grade per field.
This generator reads the shared catalogue loader output and writes two SQF
files:

  addons/mobility/functions/fnc_getVehicleMatch.sqf   the identity ladder
  addons/mobility/functions/fnc_getVehicleData.sqf    the value row lookup

The match file holds the table and the five-layer ladder. The data file is
a thin consumer that returns the value row. CBA PREP compiles one function
per file, so the two entry points live in two generated files.

The row is type-aware. It carries the catalogue id, the variant id, the
vehicle type, the class token, the mapped game classes, the aliases, the
keywords, the record source and the value row. A wheeled value row holds
the two tyre fields. A tracked value row holds the two track fields. The
value row is the seven NRMM inputs of the vehicle type.

The matcher reads the generated table and the class displayName only. It
reads no source registry and no config value as a figure. A row is emitted
for every entry whose identity is complete. A missing value is a labelled
zero or an empty string, graded absent, never a reason to refuse the record.
An unknown class, an ambiguous match and an identity-incomplete entry make
the matcher return an empty array. There is no default.

Run:  python3 tools/validation/gen_vehicle_data.py
      python3 tools/validation/gen_vehicle_data.py --data-dir PATH
      python3 tools/validation/gen_vehicle_data.py --check
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

# A package import (tests) and a direct script run both resolve the sibling
# modules. The repository root goes on the path first.
_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "vehicle"
MATCH_OUT = ROOT / "addons" / "mobility" / "functions" / "fnc_getVehicleMatch.sqf"
DATA_OUT = ROOT / "addons" / "mobility" / "functions" / "fnc_getVehicleData.sqf"

# The five keys a complete value object carries beside its value.
VALUE_META_KEYS = ("unit", "source", "locator", "state", "grade")

# The row columns per the matcher metadata contract.
COL_CATALOGUE = 0
COL_VARIANT = 1
COL_TYPE = 2
COL_CLASS_TOKEN = 3
COL_CLASSES = 4
COL_ALIASES = 5
COL_KEYWORDS = 6
COL_SOURCE = 7
COL_VALUES = 8

# The shortest alias or keyword the closest layer accepts.
SCAN_MIN = 4

MATCH_TEMPLATE = """#include "..\\script_component.hpp"
/*
Vehicle identity matcher (issue #117).

Function: aee_mobility_fnc_getVehicleMatch.

This file is GENERATED. The generator tools/validation/gen_vehicle_data.py
writes it from the validated vehicle catalogue under data/vehicle/. Do not
edit it by hand. Edit the corpus and regenerate it.

The matcher resolves a game class to a real vehicle entry. It runs an
ordered ladder. The first layer that yields exactly one candidate wins. A
weaker layer runs only when every stronger layer yields none. A tie at any
layer returns an empty array.

  exact_class   the normalised class equals a mapped game class.      1
  alias         a classname or displayName token equals an alias.     2
  keyword       the query holds a keyword of 4 or more characters.    3
  inheritance   the class isKindOf the entry class token, and exactly
                one entry carries that token.                         4
  closest       the longest alias or keyword substring of the query,
                at least 4 characters, with a strictly lower
                runner-up score. A tie returns [].                    5

A row has nine columns:

  0 catalogue_id      string, the stable catalogue key
  1 variant_id        string, the variant key
  2 vehicle_type      string, "wheeled" or "tracked"
  3 class_token       string, the supported token or empty
  4 mapped_classes    string, "|" separated normalised game classes
  5 aliases           string, "|" separated normalised catalogue aliases
  6 keywords          string, "|" separated normalised catalogue keywords
  7 source_record_id  string, the source id of the operating weight value
  8 value_row         array of seven values, by vehicle type

value_row, wheeled  [operating_weight_kg, tyre_width_mm, tyre_diameter_mm,
                     ground_clearance_mm, net_power_kw, transmission_type,
                     grousers_state]
value_row, tracked  [operating_weight_kg, track_shoe_width_mm,
                     track_pitch_mm, ground_clearance_mm, net_power_kw,
                     transmission_type, grousers_state]

Column units: operating weight kg, widths and pitches mm, clearance mm,
net power kW, transmission_type enum (manual or automatic), grousers_state
enum (none, grousers or chains).

Returns [catalogue_id, variant_id, vehicle_type, confidence, matched_by,
source_record_id, valueRow], or []. The class displayName is identity text
only. The matcher reads no config value as a figure and no source registry.

Arguments:
  0: className (STRING, the CfgVehicles classname, default "")
*/
params [["_className", "", [""]]];
if (_className == "") exitWith { [] };

private _normalise = {
    params ["_text"];
    private _out = "";
    {
        if ((_x >= 48 && _x <= 57) || (_x >= 97 && _x <= 122)) then {
            _out = _out + toString [_x];
        };
    } forEach (toArray (toLower _text));
    _out
};

private _key = [_className] call _normalise;
if (_key == "") exitWith { [] };

// Identity text only. The displayName broadens the query for the alias and
// keyword layers. It never carries a figure.
private _name = getText (configFile >> "CfgVehicles" >> _className >> "displayName");
private _query = [_className + " " + _name] call _normalise;
private _tokens = [];
{
    private _token = _x call _normalise;
    if (_token != "") then { _tokens pushBack _token; };
} forEach ((_className + " " + _name) splitString " _-.");

private _table = [
__ROWS__
];

// [catalogue_id, variant_id, vehicle_type, confidence, matched_by,
//  source_record_id, value_row]
private _result = {
    params ["_row", "_confidence", "_layer"];
    [_row select 0, _row select 1, _row select 2, _confidence, _layer,
     _row select 7, _row select 8]
};

private _candidates = [];

// Layer 1: exact class. The normalised class equals a mapped game class.
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (((_classes splitString "|") find _key) >= 0) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 1, "exact_class"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 2: alias. A query token equals a catalogue alias.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if (_x in _tokens) then { _hit = true; };
    } forEach (_aliases splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 2, "alias"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 3: keyword. The query holds a keyword of at least four characters.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if ((count _x) >= __SCAN__ && {_query find _x >= 0}) then { _hit = true; };
    } forEach (_keywords splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 3, "keyword"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 4: inheritance. The class isKindOf the entry class token.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (_token != "" && {_className isKindOf _token}) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 4, "inheritance"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 5: closest. The longest alias or keyword substring of the query,
// at least four characters, with a strictly lower runner-up score.
private _bestRow = [];
private _bestScore = 0;
private _runnerUp = 0;
private _tie = false;
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _score = 0;
    {
        if ((count _x) >= __SCAN__ && {count _x > _score} && {_query find _x >= 0}) then {
            _score = count _x;
        };
    } forEach ((_aliases + "|" + _keywords) splitString "|");
    if (_score >= __SCAN__) then {
        if (_score > _bestScore) then {
            _runnerUp = _bestScore;
            _bestScore = _score;
            _bestRow = _row;
            _tie = false;
        } else {
            if (_score == _bestScore) then { _tie = true; };
            if (_score > _runnerUp) then { _runnerUp = _score; };
        };
    };
} forEach _table;
if ((_bestRow isNotEqualTo []) && {!_tie} && _bestScore > _runnerUp) exitWith {
    [_bestRow, 5, "closest"] call _result
};
[]
"""

DATA_TEMPLATE = """#include "..\\script_component.hpp"
/*
Vehicle runtime lookup (issue #117).

Function: aee_mobility_fnc_getVehicleData.

This file is GENERATED. The generator tools/validation/gen_vehicle_data.py
writes it from the validated vehicle catalogue under data/vehicle/. Do not
edit it by hand. Edit the corpus and regenerate it.

The lookup is a thin consumer of aee_mobility_fnc_getVehicleMatch. It
returns the value row of a unique match, or an empty array. A variant
selector keeps a row only when its variant id matches.

The value row is the seven NRMM inputs of the vehicle type. A wheeled row
holds the two tyre fields. A tracked row holds the two track fields. The
lookup reads no config value and no source registry. It returns no default.

Arguments:
  0: className (STRING, the CfgVehicles classname, default "")
  1: variantId (STRING, the optional variant selector, default "")
*/
params [["_className", "", [""]], ["_variantId", "", [""]]];
if (_className == "") exitWith { [] };

private _match = [_className] call FUNC(getVehicleMatch);
if (_match isEqualTo []) exitWith { [] };
if (_variantId == "") exitWith { _match select 6 };

private _normalise = {
    params ["_text"];
    private _out = "";
    {
        if ((_x >= 48 && _x <= 57) || (_x >= 97 && _x <= 122)) then {
            _out = _out + toString [_x];
        };
    } forEach (toArray (toLower _text));
    _out
};
private _variantKey = [_variantId] call _normalise;
if ((_match select 1) != _variantKey) exitWith { [] };
_match select 6
"""


def normalise(text: str) -> str:
    """Fold a class, alias or keyword to its lookup key."""
    return "".join(char for char in text.lower() if char.isascii() and char.isalnum())


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _normalised_list(value: object) -> tuple[str, ...]:
    """Return the deduplicated normalised keys of an alias or keyword array."""
    if not isinstance(value, list):
        return ()
    keys: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        key = normalise(item)
        if key and key not in keys:
            keys.append(key)
    return tuple(keys)


def _text(value: object) -> str | None:
    """Return a non-empty string, or None."""
    if isinstance(value, str) and value.strip():
        return value
    return None


def resolve_row(record: object) -> list[catalogue.ResolvedField] | None:
    """Return the graded runtime fields of a record, or None when no row emits.

    A row emits for every entry whose identity is complete: a catalogue id, a
    variant id and a supported vehicle type. A missing value never refuses the
    row. It resolves to a labelled absent zero, so a held entry always projects.
    """
    entry = _mapping(record)
    if entry is None:
        return None
    if _text(entry.get("catalogue_id")) is None:
        return None
    if _text(entry.get("variant_id")) is None:
        return None
    vehicle_type = entry.get("vehicle_type")
    if not isinstance(vehicle_type, str):
        return None
    required = catalogue.REQUIRED_RUNTIME_BY_TYPE.get(vehicle_type)
    if not required:
        return None
    values = _mapping(entry.get("values"))
    if values is None:
        values = {}
    return [catalogue.resolve_field(values, field) for field in required]


def build_row(
    record: object, mapped_classes: Iterable[str] = ()
) -> list[object] | None:
    """Return one runtime row, or None when the record has no identity.

    ``mapped_classes`` names the AEE game classes the class map links to the
    entry. It fills column 4 as a normalised blob. Every value column is graded
    in ``resolve_row``: a held value, a named derivation or a labelled zero.
    """
    fields = resolve_row(record)
    if fields is None:
        return None
    entry = _mapping(record)
    assert entry is not None

    catalogue_id = _text(entry.get("catalogue_id")) or ""
    variant_id = _text(entry.get("variant_id")) or ""
    vehicle_type = _text(entry.get("vehicle_type")) or ""
    class_token = entry.get("class_token")
    classes_blob = "|".join(
        key for key in (normalise(str(item)) for item in mapped_classes) if key
    )
    aliases_blob = "|".join(_normalised_list(entry.get("aliases")))
    keywords_blob = "|".join(_normalised_list(entry.get("keywords")))
    source_record_id = next(
        (field.source for field in fields if field.grade != "absent" and field.source),
        "",
    )

    return [
        catalogue_id,
        variant_id,
        vehicle_type,
        class_token if isinstance(class_token, str) else "",
        classes_blob,
        aliases_blob,
        keywords_blob,
        source_record_id,
        [field.value for field in fields],
    ]


def class_index(load: catalogue.CatalogueLoad) -> dict[str, list[str]]:
    """Map each catalogue id to its sorted mapped game classes."""
    owners: dict[str, set[str]] = {}
    for mapping in load.mappings:
        owners.setdefault(mapping.catalogue_id, set()).add(mapping.game_class)
    return {key: sorted(value) for key, value in owners.items()}


def build_rows(
    records: Iterable[object],
    mappings: dict[str, list[str]] | None = None,
) -> list[list[object]]:
    """Build every row and sort it. The order is catalogue then variant."""
    table = mappings if mappings is not None else {}
    rows: list[list[object]] = []
    for record in records:
        entry = _mapping(record)
        if entry is None:
            continue
        cid = entry.get("catalogue_id")
        classes = table.get(cid, ()) if isinstance(cid, str) else ()
        row = build_row(entry, classes)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda row: (str(row[COL_CATALOGUE]), str(row[COL_VARIANT])))
    return rows


def load_rows(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Read the catalogue layer and build every runtime row."""
    load = catalogue.load(data_dir)
    return build_rows((entry.to_mapping() for entry in load.entries), class_index(load))


def _sqf(value: object) -> str:
    """Render one SQF literal. A string is quoted and escaped."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace('"', '""') + '"'
    return str(value)


def format_row(row: Sequence[object]) -> str:
    """Render one row in the fixed nine-column shape."""
    head = ", ".join(_sqf(row[index]) for index in range(COL_VALUES))
    value_row = row[COL_VALUES]
    assert isinstance(value_row, (list, tuple))
    values = ", ".join(_sqf(item) for item in value_row)
    return f"    [{head}, [{values}]]"


def _query_tokens(text: str) -> set[str]:
    """Split identity text into normalised match keys, as the SQF does."""
    folded = text.lower()
    for char in ("_", "-", "."):
        folded = folded.replace(char, " ")
    return {normalise(token) for token in folded.split() if normalise(token)}


def match_row(
    rows: Sequence[Sequence[object]], class_name: str, display_name: str = ""
) -> list[object] | None:
    """Reference mirror of the generated five-layer ladder.

    The generated SQF file is the runtime authority. This mirror exists so the
    Python harness can prove that the emitted table resolves an identity to a
    value row. It reads identity text only and returns the same seven-element
    result array, or None. The inheritance layer approximates ``isKindOf`` by
    an exact token match, because the harness cannot query the engine class
    tree.
    """
    key = normalise(class_name)
    if key == "":
        return None
    query = normalise(class_name + " " + display_name)
    tokens = _query_tokens(class_name + " " + display_name)

    def result(row: Sequence[object], confidence: int, layer: str) -> list[object]:
        return [
            row[COL_CATALOGUE],
            row[COL_VARIANT],
            row[COL_TYPE],
            confidence,
            layer,
            row[COL_SOURCE],
            row[COL_VALUES],
        ]

    exact = [row for row in rows if key in str(row[COL_CLASSES]).split("|")]
    if len(exact) == 1:
        return result(exact[0], 1, "exact_class")
    if len(exact) > 1:
        return None

    alias = [row for row in rows if set(str(row[COL_ALIASES]).split("|")) & tokens]
    if len(alias) == 1:
        return result(alias[0], 2, "alias")
    if len(alias) > 1:
        return None

    keyword = [
        row
        for row in rows
        if any(
            len(word) >= SCAN_MIN and word in query
            for word in str(row[COL_KEYWORDS]).split("|")
        )
    ]
    if len(keyword) == 1:
        return result(keyword[0], 3, "keyword")
    if len(keyword) > 1:
        return None

    inherit = [
        row
        for row in rows
        if str(row[COL_CLASS_TOKEN]) and normalise(str(row[COL_CLASS_TOKEN])) == key
    ]
    if len(inherit) == 1:
        return result(inherit[0], 4, "inheritance")
    if len(inherit) > 1:
        return None

    best: Sequence[object] | None = None
    best_score = 0
    runner_up = 0
    tie = False
    for row in rows:
        score = 0
        for word in (str(row[COL_ALIASES]) + "|" + str(row[COL_KEYWORDS])).split("|"):
            if len(word) >= SCAN_MIN and len(word) > score and word in query:
                score = len(word)
        if score >= SCAN_MIN:
            if score > best_score:
                runner_up = best_score
                best_score = score
                best = row
                tie = False
            else:
                if score == best_score:
                    tie = True
                if score > runner_up:
                    runner_up = score
    if best is not None and not tie and best_score > runner_up:
        return result(best, 5, "closest")
    return None


def render_match(rows: Sequence[Sequence[object]]) -> str:
    """Render the matcher file for the given rows."""
    body = ",\n".join(format_row(row) for row in rows)
    return MATCH_TEMPLATE.replace("__ROWS__", body).replace("__SCAN__", str(SCAN_MIN))


def render_data() -> str:
    """Render the thin lookup file."""
    return DATA_TEMPLATE


def write_outputs(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Write both generated files and return the rows."""
    rows = load_rows(data_dir)
    MATCH_OUT.write_text(render_match(rows), encoding="utf-8")
    DATA_OUT.write_text(render_data(), encoding="utf-8")
    return rows


def check_outputs(
    data_dir: Path,
    match_out: Path = MATCH_OUT,
    data_out: Path = DATA_OUT,
) -> int:
    """Return 0 when both generated files match a fresh render.

    Check mode writes nothing. A missing or stale file returns 1, so a stale
    generated matcher fails the gate.
    """
    rows = load_rows(data_dir)
    expected = {match_out: render_match(rows), data_out: render_data()}
    stale = False
    for path, text in expected.items():
        if not path.is_file():
            print(f"vehicle projection: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"vehicle projection: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(
        f"vehicle projection: {len(rows)} rows -> {match_out.name} and "
        f"{data_out.name} (fresh)"
    )
    return 0


def main(argv: Sequence[str]) -> int:
    data_dir = DEFAULT_DATA
    if "--data-dir" in argv:
        index = argv.index("--data-dir")
        if index + 1 < len(argv):
            data_dir = Path(argv[index + 1])
    if "--check" in argv:
        return check_outputs(data_dir)
    rows = write_outputs(data_dir)
    load = catalogue.load(data_dir)
    print(
        f"vehicle rows: {len(rows)} from {len(load.entries)} catalogue entries, "
        f"wrote {MATCH_OUT.name} and {DATA_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
