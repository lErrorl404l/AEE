#!/usr/bin/env python3
"""Generate the device matcher and lookup from the device corpus.

The device corpus holds one entry per real night vision, thermal or optic
device. An entry carries a value, a unit, a source, a locator, a state and
a grade per field. This generator reads the shared catalogue loader output
and writes two SQF files:

  addons/nightvision/functions/fnc_getDeviceMatch.sqf  the identity ladder
  addons/nightvision/functions/fnc_getDeviceData.sqf   the value row lookup

The match file holds the table and the ladder. The data file is a thin
consumer that returns the value row. CBA PREP compiles one function per
file, so the two entry points live in two generated files.

The row is family-aware. It carries the device id, the family, the mapped
class names, the aliases, the keywords, the record source and the value
row. A tube row holds the four image-intensifier fields. A thermal row
holds the six detector fields. An optic row holds the six sight fields.

The matcher reads the generated table and the class displayName only. It
reads no source registry and no config value as a figure. A row is emitted
for every entry whose identity is complete. A missing value is a labelled
zero or an empty string, graded absent, never a reason to refuse the
record. An unknown class, an ambiguous match and an identity-incomplete
entry make the matcher return an empty array. There is no default.

Run:  python3 tools/validation/gen_device_data.py
      python3 tools/validation/gen_device_data.py --data-dir PATH
      python3 tools/validation/gen_device_data.py --check
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation import device_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "device"
MATCH_OUT = ROOT / "addons" / "nightvision" / "functions" / "fnc_getDeviceMatch.sqf"
DATA_OUT = ROOT / "addons" / "nightvision" / "functions" / "fnc_getDeviceData.sqf"

# The row columns per the matcher metadata contract.
COL_DEVICE = 0
COL_FAMILY = 1
COL_CLASSES = 2
COL_ALIASES = 3
COL_KEYWORDS = 4
COL_SOURCE = 5
COL_VALUES = 6

# The shortest alias or keyword the closest layer accepts.
SCAN_MIN = 4

MATCH_TEMPLATE = """#include "..\\script_component.hpp"
/*
Device identity matcher (night vision, thermal and optic).

Function: aee_nightvision_fnc_getDeviceMatch.

This file is GENERATED. The generator tools/validation/gen_device_data.py
writes it from the validated device catalogue under data/device/. Do not
edit it by hand. Edit the corpus and regenerate it.

The matcher resolves a device class to a real device entry. It runs an
ordered ladder. The first layer that yields exactly one candidate wins. A
weaker layer runs only when every stronger layer yields none. A tie at any
layer returns an empty array.

  exact_class   the normalised class equals a mapped class name.        1
  alias         a classname token equals a catalogue alias.             2
  keyword       the query holds a keyword of 4 or more characters.      3
  closest       the longest alias or keyword substring of the query,
                at least 4 characters, with a strictly lower
                runner-up score. A tie returns [].                    4

The vehicle matcher runs a fifth inheritance layer. A device row names no
supported game class token, so that layer has no meaning here and is
absent. The order and the tie rule of the remaining layers are the same.

The table is filtered by family before the ladder runs, so one class cannot
tie across two families. The ENVG-B is both a night vision device and a
thermal device, and a caller states which one it wants.

A row has seven columns:

  0 device_id         string, the stable catalogue key
  1 family            string, "nvg", "thermal" or "optic"
  2 class_names       string, "|" separated normalised class names
  3 aliases           string, "|" separated normalised catalogue aliases
  4 keywords          string, "|" separated normalised catalogue keywords
  5 source_record_id  string, the source id of the first held value
  6 value_row         array of values, by family

value_row, nvg      [output_colour, resolution_lpmm, snr, halo_mm]
value_row, thermal  [netd_c, resolution_x, resolution_y, refresh_hz,
                     cooled, weight_kg]
value_row, optic    [magnification, objective_mm, fov_deg, weight_kg,
                     exit_pupil_mm, active]

A missing value is a labelled zero for a number or an empty string for a
word, never a refusal of the record. The grade of every field is in the
corpus and in the coverage artefact.

Returns [device_id, family, confidence, matched_by, source_record_id,
valueRow], or []. The class displayName is identity text only. The matcher
reads no config value as a figure and no source registry.

Arguments:
  0: className (STRING, the device classname, default "")
  1: family (STRING, the optional family filter, default "")
*/
params [["_className", "", [""]], ["_family", "", [""]]];
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

// Identity text only: the class name, the raw display name and its
// localised stringtable text. A class stores a $STR key in displayName,
// so all three are needed. None carries a figure.
private _rawName = "";
{
    private _cfg = configFile >> _x >> _className;
    if (isClass _cfg) exitWith {
        _rawName = getText (_cfg >> "displayName");
    };
} forEach ["CfgWeapons", "CfgVehicles"];
private _localName = if ((_rawName select [0,1]) == "$") then { localize _rawName } else { _rawName };
private _identity = _className + " " + _rawName + " " + _localName;
private _query = [_identity] call _normalise;
private _tokens = [];
{
    private _token = _x call _normalise;
    if (_token != "") then { _tokens pushBack _token; };
} forEach (_identity splitString " _-.");

private _tableAll = [
__ROWS__
];

// Filter by family so a class two families share cannot tie.
private _table = if (_family == "") then { _tableAll } else {
    _tableAll select {(_x select 1) == _family}
};

// [device_id, family, confidence, matched_by, source_record_id, value_row]
private _result = {
    params ["_row", "_confidence", "_layer"];
    [_row select 0, _row select 1, _confidence, _layer,
     _row select 5, _row select 6]
};

private _candidates = [];

// Layer 1: exact class. The normalised class equals a mapped class name.
{
    _x params ["_device", "_devFamily", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (((_classes splitString "|") find _key) >= 0) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 1, "exact_class"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 2: alias. A query token equals a catalogue alias.
_candidates = [];
{
    _x params ["_device", "_devFamily", "_classes", "_aliases", "_keywords", "_source", "_values"];
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
    _x params ["_device", "_devFamily", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if ((count _x) >= __SCAN__ && {_query find _x >= 0}) then { _hit = true; };
    } forEach (_keywords splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 3, "keyword"] call _result };
if ((count _candidates) > 1) exitWith { [] };

// Layer 4: closest. The longest alias or keyword substring of the query,
// at least four characters, with a strictly lower runner-up score.
private _bestRow = [];
private _bestScore = 0;
private _runnerUp = 0;
private _tie = false;
{
    _x params ["_device", "_devFamily", "_classes", "_aliases", "_keywords", "_source", "_values"];
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
    [_bestRow, 4, "closest"] call _result
};
[]
"""

DATA_TEMPLATE = """#include "..\\script_component.hpp"
/*
Device runtime lookup (night vision, thermal and optic).

Function: aee_nightvision_fnc_getDeviceData.

This file is GENERATED. The generator tools/validation/gen_device_data.py
writes it from the validated device catalogue under data/device/. Do not
edit it by hand. Edit the corpus and regenerate it.

The lookup is a thin consumer of aee_nightvision_fnc_getDeviceMatch. It
returns the value row of a unique match, or an empty array. A caller that
knows the device family passes it, so a class that two families share
resolves to the row the caller wants.

The value row is the runtime set of the family. A tube row holds the four
image-intensifier fields. A thermal row holds the six detector fields. An
optic row holds the six sight fields. The lookup reads no config value and
no source registry. It returns no default.

Arguments:
  0: className (STRING, the device classname, default "")
  1: family (STRING, the optional family filter, default "")
*/
params [["_className", "", [""]], ["_family", "", [""]]];
if (_className == "") exitWith { [] };

private _match = [_className, _family] call FUNC(getDeviceMatch);
if (_match isEqualTo []) exitWith { [] };

_match select 5
"""


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def resolve_row(record: object) -> list[catalogue.ResolvedField] | None:
    """Return the graded runtime fields of a record, or None when no row emits.

    A row emits for every entry whose identity is complete: a device id, a
    family the projection supports and a values object. A missing value
    never refuses the row. It resolves to a labelled absent zero or empty
    string, so a held entry always projects.
    """
    entry = _mapping(record)
    if entry is None:
        return None
    if _text(entry.get("device_id")) is None:
        return None
    family = entry.get("family")
    if not isinstance(family, str):
        return None
    required = catalogue.REQUIRED_RUNTIME_BY_FAMILY.get(family)
    if not required:
        return None
    values = _mapping(entry.get("values"))
    if values is None:
        values = {}
    return [catalogue.resolve_field(values, field) for field in required]


def build_row(
    record: object, mapped_classes: Iterable[str] = ()
) -> list[object] | None:
    """Return one runtime row, or None when the record has no identity."""
    fields = resolve_row(record)
    if fields is None:
        return None
    entry = _mapping(record)
    assert entry is not None

    device_id = _text(entry.get("device_id")) or ""
    family = _text(entry.get("family")) or ""
    classes_blob = "|".join(
        key
        for key in (catalogue.normalise(str(item)) for item in mapped_classes)
        if key
    )
    aliases = entry.get("aliases")
    keywords = entry.get("keywords")
    aliases_blob = "|".join(
        key
        for key in (
            catalogue.normalise(str(item))
            for item in (aliases if isinstance(aliases, list) else [])
        )
        if key
    )
    keywords_blob = "|".join(
        key
        for key in (
            catalogue.normalise(str(item))
            for item in (keywords if isinstance(keywords, list) else [])
        )
        if key
    )
    source_record_id = next(
        (field.source for field in fields if field.grade != "absent" and field.source),
        "",
    )
    return [
        device_id,
        family,
        classes_blob,
        aliases_blob,
        keywords_blob,
        source_record_id,
        [field.value for field in fields],
    ]


def class_index(load: catalogue.DeviceLoad) -> dict[str, list[str]]:
    """Map each device id to its mapped class names."""
    return {entry.device_id: list(entry.class_names) for entry in load.entries}


def build_rows(
    records: Iterable[object],
    mappings: dict[str, list[str]] | None = None,
) -> list[list[object]]:
    """Build every row and sort it. The order is device id."""
    table = mappings if mappings is not None else {}
    rows: list[list[object]] = []
    for record in records:
        entry = _mapping(record)
        if entry is None:
            continue
        did = entry.get("device_id")
        classes = table.get(did, ()) if isinstance(did, str) else ()
        row = build_row(entry, classes)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda row: str(row[COL_DEVICE]))
    return rows


def load_rows(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Read the catalogue layer and build every runtime row."""
    load = catalogue.load(data_dir)
    index = class_index(load)
    return build_rows((entry.to_mapping() for entry in load.entries), index)


def _sqf(value: object) -> str:
    """Render one SQF literal. A string is quoted and escaped."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return '"' + value.replace('"', '""') + '"'
    return str(value)


def format_row(row: Sequence[object]) -> str:
    """Render one row in the fixed seven-column shape."""
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
    return {
        catalogue.normalise(token)
        for token in folded.split()
        if catalogue.normalise(token)
    }


def match_row(
    rows: Sequence[Sequence[object]],
    class_name: str,
    display_name: str = "",
    family: str = "",
) -> list[object] | None:
    """Reference mirror of the generated four-layer ladder.

    The generated SQF file is the runtime authority. This mirror lets the
    Python harness prove that the emitted table resolves an identity to a
    value row. It reads identity text only and returns the same six-element
    result array, or None.
    """
    key = catalogue.normalise(class_name)
    if key == "":
        return None
    query = catalogue.normalise(class_name + " " + display_name)
    tokens = _query_tokens(class_name + " " + display_name)
    scoped = [row for row in rows if family == "" or row[COL_FAMILY] == family]

    def result(row: Sequence[object], confidence: int, layer: str) -> list[object]:
        return [
            row[COL_DEVICE],
            row[COL_FAMILY],
            confidence,
            layer,
            row[COL_SOURCE],
            row[COL_VALUES],
        ]

    exact = [row for row in scoped if key in str(row[COL_CLASSES]).split("|")]
    if len(exact) == 1:
        return result(exact[0], 1, "exact_class")
    if len(exact) > 1:
        return None

    alias = [row for row in scoped if set(str(row[COL_ALIASES]).split("|")) & tokens]
    if len(alias) == 1:
        return result(alias[0], 2, "alias")
    if len(alias) > 1:
        return None

    keyword = [
        row
        for row in scoped
        if any(
            len(word) >= SCAN_MIN and word in query
            for word in str(row[COL_KEYWORDS]).split("|")
        )
    ]
    if len(keyword) == 1:
        return result(keyword[0], 3, "keyword")
    if len(keyword) > 1:
        return None

    best: Sequence[object] | None = None
    best_score = 0
    runner_up = 0
    tie = False
    for row in scoped:
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
        return result(best, 4, "closest")
    return None


def render_match(rows: Sequence[Sequence[object]]) -> str:
    """Render the matcher file for the given rows."""
    body = ",\n".join(format_row(row) for row in rows)
    return MATCH_TEMPLATE.replace("__ROWS__", body).replace("__SCAN__", str(SCAN_MIN))


def render_data() -> str:
    """Render the thin lookup file."""
    return DATA_TEMPLATE


def write_outputs(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Write every generated file and return the matcher rows."""
    rows = load_rows(data_dir)
    MATCH_OUT.write_text(render_match(rows), encoding="utf-8")
    DATA_OUT.write_text(render_data(), encoding="utf-8")
    return rows


def check_outputs(
    data_dir: Path,
    match_out: Path = MATCH_OUT,
    data_out: Path = DATA_OUT,
) -> int:
    """Return 0 when every generated file matches a fresh render.

    Check mode writes nothing. A missing or stale file returns 1, so a stale
    generated matcher or lookup fails the gate.
    """
    rows = load_rows(data_dir)
    expected = {
        match_out: render_match(rows),
        data_out: render_data(),
    }
    stale = False
    for path, text in expected.items():
        if not path.is_file():
            print(f"device projection: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"device projection: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(
        f"device projection: {len(rows)} rows -> {match_out.name} and "
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
        f"device rows: {len(rows)} from {len(load.entries)} catalogue entries, "
        f"wrote {MATCH_OUT.name} and {DATA_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
