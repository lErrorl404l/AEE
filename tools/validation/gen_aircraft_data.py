#!/usr/bin/env python3
"""Generate the runtime aircraft matcher and lookup from the catalogue.

The aircraft catalogue holds one entry per real aircraft variant. An entry
carries a value, a unit, a source, a locator, a state and a grade per field.
This generator reads the shared catalogue loader output through the aircraft
profile and writes two SQF files:

  addons/flight/functions/fnc_getAircraftMatch.sqf   the identity ladder
  addons/flight/functions/fnc_getAircraftData.sqf    the value row lookup

The match file holds the table and the five-layer ladder. The data file is
a thin consumer that returns the value row. CBA PREP compiles one function
per file, so the two entry points live in two generated files.

The row is type-aware. It carries the catalogue id, the variant id, the
vehicle type, the class token, the mapped game classes, the aliases, the
keywords, the record source and the value row. The value row holds the four
flight-model inputs in fixed order: operating weight, rated power, drag area
and rotor disc area. An absent field is a labelled zero.

The matcher reads the generated table and the class displayName only. It
reads no source registry and no config value as a figure. A row is emitted
for every entry whose identity is complete. A missing value is a labelled
zero or an empty string, graded absent, never a reason to refuse the record.
An unknown class, an ambiguous match and an identity-incomplete entry make
the matcher return an empty array. There is no default.

Run:  python3 tools/validation/gen_aircraft_data.py
      python3 tools/validation/gen_aircraft_data.py --data-dir PATH
      python3 tools/validation/gen_aircraft_data.py --check
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

# A package import (tests) and a direct script run both resolve the sibling
# modules. The repository root goes on the path first.
_REPO = Path(__file__).parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.validation.identity_designations import (
    CATEGORY_WORDS as _CATEGORY_WORDS,
)
from tools.validation.identity_designations import designations as _designations
from tools.validation.identity_designations import fold as _designation_fold
from tools.validation import vehicle_catalogue as catalogue  # noqa: E402

ROOT = _REPO
DEFAULT_DATA = ROOT / "data" / "aircraft"
MATCH_OUT = ROOT / "addons" / "flight" / "functions" / "fnc_getAircraftMatch.sqf"
DATA_OUT = ROOT / "addons" / "flight" / "functions" / "fnc_getAircraftData.sqf"

# The aircraft profile selects the type enum, the runtime sets and the named
# derivations. The type enum is fixed_wing and rotary_wing.
PROFILE = catalogue.AIRCRAFT_PROFILE

# The value row, in fixed projection order. The two optional fields resolve to
# a labelled absent zero when the corpus holds no value and no derivation.
VALUE_FIELDS = (
    "operating_weight_kg",
    "rated_power_w",
    "drag_area_m2",
    "rotor_disc_area_m2",
)

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
# A non-numeric designation advertised by more entries than this names a
# category or a maker, not one thing.
SHARED_WORD_MAX = 3
SCAN_MIN = 3

MATCH_TEMPLATE = """#include "..\\script_component.hpp"
/*
Aircraft identity matcher (issue #117).

Function: aee_flight_fnc_getAircraftMatch.

This file is GENERATED. The generator tools/validation/gen_aircraft_data.py
writes it from the validated aircraft catalogue under data/aircraft/. Do not
edit it by hand. Edit the corpus and regenerate it.

The matcher resolves a game class to a real aircraft entry. It runs an
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
  family        the class text names a family and no mark: exactly one
                row of the family table carries a designation of 3 or
                more characters in the query. A family row is
                identity-only and answers only when it is the only
                one, so it never takes an answer from a mark.           7
  type          nothing above names the aircraft, so the ENGINE kind is
                the answer: "helicopter", "fixed-wing aircraft",
                "unmanned aerial vehicle" or "aircraft". A type entry
                names a kind, never a model, and carries no figure.     8

A row has nine columns:

  0 catalogue_id      string, the stable catalogue key
  1 variant_id        string, the variant key
  2 vehicle_type      string, "fixed_wing" or "rotary_wing"
  3 class_token       string, the supported token or empty
  4 mapped_classes    string, "|" separated normalised game classes
  5 aliases           string, "|" separated normalised catalogue aliases
  6 keywords          string, "|" separated normalised catalogue keywords
  7 source_record_id  string, the source id of the operating weight value
  8 value_row         array of four values, in fixed order

value_row  [operating_weight_kg, rated_power_w, drag_area_m2,
            rotor_disc_area_m2]

The value row carries the four flight-model inputs. A field no held value
and no derivation reaches is a labelled absent zero. The matcher reads no
config value as a figure and no source registry.

Column units: operating weight kg, rated power W, drag area m^2, rotor disc
area m^2.

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

// Identity text only: the class name, the raw display name and its
// localised stringtable text. A vanilla class stores a $STR key in
// displayName, so all three are needed. None carries a figure.
private _rawName = getText (configFile >> "CfgVehicles" >> _className >> "displayName");
private _localName = if ((_rawName select [0,1]) == "$") then { localize _rawName } else { _rawName };
private _identity = _className + " " + _rawName + " " + _localName;
private _query = [_identity] call _normalise;
private _tokens = [];
{
    private _token = _x call _normalise;
    if (_token != "") then { _tokens pushBack _token; };
} forEach (_identity splitString " _-.");

private _table = [
__ROWS__
];

// Family rows. A family entry names a family and no mark, so it is
// identity-only and lives in its own table: no layer above can reach it,
// and the last layer alone reads it. The columns are the ones above.
private _families = [
__FAMILIES__
];

// [catalogue_id, variant_id, vehicle_type, confidence, matched_by,
//  source_record_id, value_row]
private _result = {
    params ["_row", "_confidence", "_layer"];
    [_row select 0, _row select 1, _row select 2, _confidence, _layer,
     _row select 7, _row select 8]
};

private _typeAnswer = {
    // The type rung. It answers the KIND of the class when no identity layer
    // can, and it is also what a tie falls to: two candidate marks name no
    // single mark, but the engine still states the kind. It names a kind,
    // never a model, and carries no figure.
    //
    // Nothing above named the aircraft, so the ENGINE kind is the answer: the config's own taxonomy says whether this is a
    // helicopter, a fixed-wing aircraft or an unmanned aerial vehicle. A type
    // entry names a kind, never a model, and carries no figure.
    params ["_className"];
    private _kind = "";
    if (_className isKindOf "Helicopter") then { _kind = "helicopter" };
    if ((_kind == "") && {_className isKindOf "Plane"}) then { _kind = "fixed-wing aircraft" };
    if ((_kind == "") && {_className isKindOf "UAV"}) then { _kind = "unmanned aerial vehicle" };
    if (_kind == "") then { _kind = "aircraft" };
    [_kind, "", "", 8, "type", "", []]
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
if ((count _candidates) > 1) exitWith { [_className] call _typeAnswer };

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
if ((count _candidates) > 1) exitWith { [_className] call _typeAnswer };

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
if ((count _candidates) > 1) exitWith { [_className] call _typeAnswer };

// Layer 4: inheritance. The class isKindOf the entry class token.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    if (_token != "" && {_className isKindOf _token}) then {
        _candidates pushBack _x;
    };
} forEach _table;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 4, "inheritance"] call _result };
if ((count _candidates) > 1) exitWith { [_className] call _typeAnswer };

// Layer 5: closest. The longest alias or keyword substring of the query,
// at least four characters, with a strictly lower runner-up score.
private _bestRow = [];
private _bestScore = 0;
private _runnerUp = 0;
private _bestCount = 0;
private _bestName = 0;
private _tie = false;
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    // Score by the TOTAL of every distinct designation of this entry that
    // the query holds, not by the longest one alone. A reporting name is
    // shared across the marks of a type ("Frogfoot" names every Su-25), so
    // the longest single match would let any mark answer for the type;
    // summing makes the entry whose type number AND name both appear win.
    private _score = 0;
    private _count = 0;
    private _longest = 0;
    {
        _count = _count + 1;
        if ((count _x) >= __SCAN__ && {_query find _x >= 0}) then {
            // A designation carrying a TYPE NUMBER identifies the thing;
            // a plain word only describes it ("gunship" fits every gunship).
            // So a type number is worth double, and a described match can
            // no longer outvote the designation that names the aircraft.
            private _hasDigit = false;
            {
                if (_x >= 48 && _x <= 57) exitWith { _hasDigit = true; };
            } forEach (toArray _x);
            _score = _score + (count _x) * ([1, 2] select _hasDigit);
        };
        if ((count _x) > _longest) then { _longest = count _x; };
    } forEach ((_aliases + "|" + _keywords) splitString "|");
    if (_score >= __SCAN__) then {
        if (_score > _bestScore) then {
            _runnerUp = _bestScore;
            _bestScore = _score;
            _bestRow = _row;
            _bestCount = _count;
            _bestName = _longest;
            _tie = false;
        } else {
            if (_score == _bestScore) then {
                // Equal evidence. Two rules separate sibling marks, in
                // order: the entry advertising FEWER designations is the
                // less qualified one, and failing that the entry whose own
                // longest designation is SHORTER carries the less qualified
                // name ("AW101 Merlin" before "AW101 HM2 Merlin"). When a
                // query names the type but not the mark, the base mark is
                // the right answer. A true draw still stays a draw.
                if (_count < _bestCount) then {
                    _bestRow = _row;
                    _bestCount = _count;
                    _bestName = _longest;
                    _tie = false;
                } else {
                    if (_count == _bestCount) then {
                        if (_longest < _bestName) then {
                            _bestRow = _row;
                            _bestName = _longest;
                            _tie = false;
                        } else {
                            if (_longest == _bestName) then { _tie = true; };
                        };
                    };
                };
            };
            if (_score < _bestScore && _score > _runnerUp) then {
                _runnerUp = _score;
            };
        };
    };
} forEach _table;
if ((_bestRow isNotEqualTo []) && {!_tie} && _bestScore > _runnerUp) exitWith {
    [_bestRow, 5, "closest"] call _result
};

// Layer 7: family. The class text names a family and no mark. A family row
// is identity-only, so it carries no class, no alias and no value, and it
// is read here alone. The scan is the keyword rule, over the declared
// family designations. Exactly one candidate answers: two families in one
// query name no single family, and none names nothing.
_candidates = [];
{
    _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
    private _row = _x;
    private _hit = false;
    {
        if ((count _x) >= __SCAN__ && {_query find _x >= 0}) then { _hit = true; };
    } forEach (_keywords splitString "|");
    if (_hit) then { _candidates pushBack _row; };
} forEach _families;
if ((count _candidates) == 1) exitWith { [_candidates select 0, 7, "family"] call _result };

[_className] call _typeAnswer
"""

DATA_TEMPLATE = """#include "..\\script_component.hpp"
/*
Aircraft runtime lookup (issue #117).

Function: aee_flight_fnc_getAircraftData.

This file is GENERATED. The generator tools/validation/gen_aircraft_data.py
writes it from the validated aircraft catalogue under data/aircraft/. Do not
edit it by hand. Edit the corpus and regenerate it.

The lookup is a thin consumer of aee_flight_fnc_getAircraftMatch. It
returns the value row of a unique match, or an empty array. A variant
selector keeps a row only when its variant id matches.

The value row holds the four flight-model inputs in fixed order: operating
weight kg, rated power W, drag area m^2 and rotor disc area m^2. The lookup
reads no config value and no source registry. It returns no default.

Arguments:
  0: className (STRING, the CfgVehicles classname, default "")
  1: variantId (STRING, the optional variant selector, default "")
*/
params [["_className", "", [""]], ["_variantId", "", [""]]];
if (_className == "") exitWith { [] };

private _match = [_className] call FUNC(getAircraftMatch);
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
    variant id and a supported aircraft type. A missing value never refuses the
    row. It resolves to a labelled absent zero, so a held entry always projects.
    The value row holds the four fixed fields, in order.
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
    if vehicle_type not in PROFILE.vehicle_types:
        return None
    values = _mapping(entry.get("values"))
    if values is None:
        values = {}
    return [catalogue.resolve_field(values, field, PROFILE) for field in VALUE_FIELDS]


def designations(entry: dict) -> tuple[str, ...]:
    """The designations this aircraft is published under.

    The rule is the one every AEE matcher shares
    (tools/validation/identity_designations.py): only the PUBLISHED
    identity is used, so an aircraft is recognised from its own text and
    no per-mod class list is needed.
    """
    return tuple(
        _designations(
            entry.get("canonical_name"),
            entry.get("model"),
            *(entry.get("aliases") or []),
        )
    )


def build_row(
    record: object,
    mapped_classes: Iterable[str] = (),
    reserved_identities: frozenset[str] = frozenset(),
    shared_words: frozenset[str] = frozenset(),
    family_words: frozenset[str] = frozenset(),
) -> list[object] | None:
    """Return one runtime row, or None when the record has no identity.

    ``mapped_classes`` names the AEE game classes the class map and the class
    bindings link to the entry. It fills column 4 as a normalised blob. Every
    value column is graded in ``resolve_row``: a held value, a named derivation
    or a labelled zero.

    ``family_words`` holds the designations a FAMILY entry owns. A mark must
    never claim one: "uh60" names the UH-60 family, so as a keyword of the
    UH-60M mark it would tie every query that names the family and no mark
    could answer. The family entry owns it, and the family rung alone reads
    it.
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
    # The alias layer stays CURATED: it is matched by equality, so one
    # curated alias must name one entry.
    alias_keys = list(_normalised_list(entry.get("aliases")))
    aliases_blob = "|".join(alias_keys)
    # The keyword layer is matched by SUBSTRING, so it carries the derived
    # identity designations. Category words are left out: "helicopter" or
    # "transport" would match most of the catalogue and tie every query.
    own_identity = _designation_fold(entry.get("canonical_name") or "")
    keyword_keys: list[str] = []
    for key in _normalised_list(entry.get("keywords")):
        if key in alias_keys or key in _CATEGORY_WORDS or key in family_words:
            continue
        # A curated keyword is held for documentation and many of them are
        # categories ("mrap", "attack", "mainbattletank") or makers. Those
        # must not reach the matcher: they tie a query against a whole
        # class instead of naming one thing.
        if key in shared_words and not any(ch.isdigit() for ch in key):
            continue
        keyword_keys.append(key)
    for key in designations(entry):
        if key in alias_keys or key in keyword_keys or key in family_words:
            continue
        # A base model owns its own name; a sub-mark may not claim it.
        if key != own_identity and key in reserved_identities:
            continue
        if key in shared_words and not any(ch.isdigit() for ch in key):
            continue
        keyword_keys.append(key)
    keywords_blob = "|".join(keyword_keys)
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
    """Map each catalogue id to the base-game classes research has bound.

    These bindings are NOT a per-mod class list. Every one names a class of
    the base game whose own text does not name the real aircraft - a
    transport helicopter class called only "Heli_Transport_01" names no
    aircraft - so no derivation could ever recover its identity and the
    researched binding is the only evidence there is.

    Everything else is identified generically from its own text by the
    derived designations, so a modded or unknown class needs no entry here
    and none is kept for one.
    """
    owners: dict[str, set[str]] = {}
    for mapping in load.mappings:
        owners.setdefault(mapping.catalogue_id, set()).add(mapping.game_class)
    for binding in load.bindings:
        owners.setdefault(binding.catalogue_id, set()).add(binding.game_class)
    return {key: sorted(value) for key, value in owners.items()}


def build_rows(
    records: Iterable[object],
    mappings: dict[str, list[str]] | None = None,
) -> list[list[object]]:
    """Build every row and sort it. The order is catalogue then variant.

    A family entry emits no row here. It names a family and no mark, so it
    belongs to its own table, which no rung above the family rung reads.
    """
    table = mappings if mappings is not None else {}
    all_records = list(records)
    records = [record for record in all_records if not _is_family(record)]
    identities: set[str] = set()
    for record in records:
        entry = _mapping(record)
        if entry is None:
            continue
        key = _designation_fold(entry.get("canonical_name") or "")
        if len(key) >= 3:
            identities.add(key)
    reserved = frozenset(identities)
    # Count how many entries each candidate designation would come from.
    # A word shared by more than a handful is a category or a maker.
    tally: dict[str, int] = {}
    for record in records:
        entry = _mapping(record)
        if entry is None:
            continue
        words = set(designations(entry)) | set(_normalised_list(entry.get("keywords")))
        for key in words:
            tally[key] = tally.get(key, 0) + 1
    shared = frozenset(k for k, n in tally.items() if n > SHARED_WORD_MAX)
    # The designations a family entry owns belong to the family rung alone.
    # Counting them over the mark entries too would let a mark claim one and
    # tie every query that names the family.
    family_words = frozenset(
        key
        for record in all_records
        if _is_family(record)
        for key in _normalised_list((_mapping(record) or {}).get("keywords"))
    )
    rows: list[list[object]] = []
    for record in records:
        entry = _mapping(record)
        if entry is None:
            continue
        cid = entry.get("catalogue_id")
        classes = table.get(cid, ()) if isinstance(cid, str) else ()
        row = build_row(entry, classes, reserved, shared, family_words)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda row: (str(row[COL_CATALOGUE]), str(row[COL_VARIANT])))
    return rows


def load_rows(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Read the catalogue layer through the aircraft profile and build rows."""
    load = catalogue.load(data_dir, profile=PROFILE)
    index = class_index(load)
    return build_rows((entry.to_mapping() for entry in load.entries), index)


def _is_family(record: object) -> bool:
    """True when the record names a family and no mark."""
    entry = _mapping(record)
    return entry is not None and entry.get("family") is True


def build_family_row(record: object) -> list[object] | None:
    """Return the family row of a family entry, or None when no row emits.

    The row keeps the nine-column shape, so the result formatter is the one
    the mark table uses. Its class, alias and source columns stay empty: a
    family names no mark, and the designation it is reached by is its own
    keyword list, never a derivation from a name.
    """
    if not _is_family(record):
        return None
    fields = resolve_row(record)
    if fields is None:
        return None
    entry = _mapping(record)
    assert entry is not None
    return [
        _text(entry.get("catalogue_id")) or "",
        _text(entry.get("variant_id")) or "",
        _text(entry.get("vehicle_type")) or "",
        "",
        "",
        "",
        "|".join(_normalised_list(entry.get("keywords"))),
        "",
        [field.value for field in fields],
    ]


def build_family_rows(records: Iterable[object]) -> list[list[object]]:
    """Build every family row and sort it. The order is catalogue, variant."""
    rows = [
        row
        for row in (build_family_row(record) for record in records)
        if row is not None
    ]
    rows.sort(key=lambda row: (str(row[COL_CATALOGUE]), str(row[COL_VARIANT])))
    return rows


def load_family_rows(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Read the catalogue layer through the aircraft profile, family rows."""
    load = catalogue.load(data_dir, profile=PROFILE)
    return build_family_rows(entry.to_mapping() for entry in load.entries)


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


def render_match(
    rows: Sequence[Sequence[object]],
    families: Sequence[Sequence[object]] = (),
) -> str:
    """Render the matcher file for the given rows and family rows."""
    body = ",\n".join(format_row(row) for row in rows)
    family_body = ",\n".join(format_row(row) for row in families)
    return (
        MATCH_TEMPLATE.replace("__ROWS__", body)
        .replace("__FAMILIES__", family_body)
        .replace("__SCAN__", str(SCAN_MIN))
    )


def render_data() -> str:
    """Render the thin lookup file."""
    return DATA_TEMPLATE


def write_outputs(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Write every generated file and return the matcher rows."""
    rows = load_rows(data_dir)
    MATCH_OUT.write_text(
        render_match(rows, load_family_rows(data_dir)), encoding="utf-8"
    )
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
        match_out: render_match(rows, load_family_rows(data_dir)),
        data_out: render_data(),
    }
    stale = False
    for path, text in expected.items():
        if not path.is_file():
            print(f"aircraft projection: {path} is missing; run the generator")
            stale = True
            continue
        if path.read_text(encoding="utf-8") != text:
            print(f"aircraft projection: {path} is stale; run the generator")
            stale = True
    if stale:
        return 1
    print(
        f"aircraft projection: {len(rows)} rows -> {match_out.name} "
        f"and {data_out.name} (fresh)"
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
    load = catalogue.load(data_dir, profile=PROFILE)
    print(
        f"aircraft rows: {len(rows)} from {len(load.entries)} catalogue entries, "
        f"wrote {MATCH_OUT.name} and {DATA_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
