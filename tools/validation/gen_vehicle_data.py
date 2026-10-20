#!/usr/bin/env python3
"""Generate the runtime vehicle matcher and lookup from the catalogue.

The vehicle catalogue holds one entry per real vehicle variant. An entry
carries a value, a unit, a source, a locator, a state and a grade per field.
This generator reads the shared catalogue loader output and writes two SQF
files:

  addons/vehicles/functions/fnc_getVehicleMatch.sqf   the identity ladder
  addons/vehicles/functions/fnc_getVehicleData.sqf    the value row lookup

The match file holds the table and the six-layer ladder. The data file is
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

import json
import re
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
DEFAULT_DATA = ROOT / "data" / "vehicle"
MATCH_OUT = ROOT / "addons" / "vehicles" / "functions" / "fnc_getVehicleMatch.sqf"
DATA_OUT = ROOT / "addons" / "vehicles" / "functions" / "fnc_getVehicleData.sqf"
BANDS_OUT = ROOT / "addons" / "vehicles" / "functions" / "fnc_getVehicleBands.sqf"
BINDINGS_FILE = "stringtable_bindings.json"

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
# A non-numeric designation advertised by more entries than this names a
# category or a maker, not one thing.
SHARED_WORD_MAX = 3
SCAN_MIN = 3

MATCH_TEMPLATE = """#include "..\\script_component.hpp"
/*
Vehicle identity matcher (issue #117).

Function: aee_vehicles_fnc_getVehicleMatch.

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
  inherited     the class text names no entry, so the ENGINE ancestry
                answers: the nearest config ancestor the table maps by
                classname, when the class text names a designation
                that entry claims. This layer states ancestry, not
                identity: a class whose text describes a different
                thing than its ancestor returns [], whatever the
                chain says.                                             6
  family        the class text names a family and no mark: exactly one
                row of the family table carries a designation of 3 or
                more characters in the query. A family row is
                identity-only and answers only when it is the only
                one, so it never takes an answer from a mark.           7

A row has nine columns:

  0 catalogue_id      string, the stable catalogue key
  1 variant_id        string, the variant key
  2 vehicle_type      string, "wheeled", "tracked", "air" or "sea"
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
value_row, air      [operating_weight_kg, length_mm, width_mm, height_mm]
value_row, sea      [operating_weight_kg, length_mm, width_mm, height_mm]

The ground row carries the NRMM inputs. The air and sea row carries the
identity geometry only, because the ground couplings are land-specific.

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

// Layer 6: inherited. The class text names no entry, so the ENGINE ancestry
// answers. Walk the config parent chain to the nearest ancestor the table
// names by MAPPED CLASS, and answer that ancestor's entry when the class's
// own text names a designation the entry claims.
//
// Two limits keep the claim honest. The ancestor is matched by classname and
// never by text: any mod may rewrite an ancestor's displayName, so only the
// classname is stable evidence. And the class's own text has to name the
// entry, so a class that describes a different article than its ancestor
// returns [] instead of the neighbour's identity.
private _inheritedRow = [];
private _decided = false;
private _ancestor = inheritsFrom (configFile >> "CfgVehicles" >> _className);
while {isClass _ancestor && {!_decided}} do {
    private _ancestorKey = [configName _ancestor] call _normalise;
    private _ancestorHits = [];
    {
        _x params ["_catalogue", "_variant", "_type", "_token", "_classes", "_aliases", "_keywords", "_source", "_values"];
        if (((_classes splitString "|") find _ancestorKey) >= 0) then {
            _ancestorHits pushBack _x;
        };
    } forEach _table;
    if (_ancestorHits isNotEqualTo []) then {
        // The nearest named ancestor decides, and it is not walked past.
        _decided = true;
        if ((count _ancestorHits) == 1) then {
            private _entry = _ancestorHits select 0;
            private _claims = 0;
            {
                if ((count _x) >= __SCAN__ && {(((_entry select 0) + "|" + (_entry select 5) + "|" + (_entry select 6)) find _x) >= 0}) then {
                    _claims = _claims + 1;
                };
            } forEach _tokens;
            if (_claims > 0) then { _inheritedRow = _entry; };
        };
    } else {
        _ancestor = inheritsFrom _ancestor;
    };
};
if (_inheritedRow isNotEqualTo []) exitWith { [_inheritedRow, 6, "inherited"] call _result };

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
[]
"""

DATA_TEMPLATE = """#include "..\\script_component.hpp"
/*
Vehicle runtime lookup (issue #117).

Function: aee_vehicles_fnc_getVehicleData.

This file is GENERATED. The generator tools/validation/gen_vehicle_data.py
writes it from the validated vehicle catalogue under data/vehicle/. Do not
edit it by hand. Edit the corpus and regenerate it.

The lookup is a thin consumer of aee_vehicles_fnc_getVehicleMatch. It
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

BAND_TEMPLATE = """#include "..\\script_component.hpp"
/*
Vehicle identity band table (issue #117).

Function: aee_vehicles_fnc_getVehicleBands.

This file is GENERATED. The generator tools/validation/gen_vehicle_data.py
writes it from the validated vehicle catalogue under data/vehicle/. Do not
edit it by hand. Edit the corpus and regenerate it.

The band table is the property fallback of the vehicle classifier
aee_vehicles_fnc_classifyVehicle. A class whose name routes resolve to no
catalogue entry is matched by its live properties: the vehicle type first,
then the nearest held mass, then the nearest held extent. A tie selects no
row, so the classifier never guesses between two catalogue entries.

A row has seven columns:

  0 catalogue_id      string, the stable catalogue key
  1 vehicle_type      string, "wheeled", "tracked", "air" or "sea"
  2 is_tracked        number, 1 for a tracked entry, else 0
  3 mass_kg           number, the resolved operating weight in kg, 0 absent
  4 length_mm         number, the held overall length in mm, 0 absent
  5 width_mm          number, the held overall width in mm, 0 absent
  6 height_mm         number, the held overall height in mm, 0 absent

The mass is the catalogue resolution of operating_weight_kg: a held value or
a named derivation. The three extents are held values only. A zero means the
corpus holds no value. A corpus value only: the engine mass and the engine
bounding box are never written here.

Returns the band table, one row per catalogue entry, sorted by catalogue id.

Arguments: none.
Public: No
*/

private _table = [
__ROWS__
];

_table
"""


def normalise(text: str) -> str:
    """Fold a class, alias or keyword to its lookup key."""
    return "".join(char for char in text.lower() if char.isascii() and char.isalnum())


def _mapping(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def designations(entry: dict) -> tuple[str, ...]:
    """The designations this vehicle is published under.

    The rule is shared with every other AEE matcher
    (tools/validation/identity_designations.py), so a vehicle, an aircraft,
    a weapon and a device are all recognised from their own text by the
    same derivation and no domain carries a per-mod class list.

    Only the PUBLISHED identity is passed: the canonical name, the model
    and the curated aliases. The catalogue and variant keys are repository
    bookkeeping, not identity, so they stay out of the matcher.
    """
    return tuple(
        _designations(
            entry.get("canonical_name"),
            entry.get("model"),
            *(entry.get("aliases") or []),
        )
    )


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
    record: object,
    mapped_classes: Iterable[str] = (),
    reserved_identities: frozenset[str] = frozenset(),
    shared_words: frozenset[str] = frozenset(),
) -> list[object] | None:
    """Return one runtime row, or None when the record has no identity.

    ``mapped_classes`` names the AEE game classes the class map links to the
    entry. It fills column 4 as a normalised blob. Every value column is graded
    in ``resolve_row``: a held value, a named derivation or a labelled zero.

    ``shared_words`` holds the designations that carry NO type number and
    that many entries advertise. A word like "mrap", "mainbattletank",
    "attack" or a maker's own name is a CATEGORY: it says what kind of
    thing this is, never which one, so as a designation it ties every
    query against its whole class. A designation carrying a type number is
    never dropped, however many marks share it, because that is exactly
    what a family designation looks like.

    ``reserved_identities`` holds the folded canonical name of every OTHER
    entry. A derived designation equal to one of them is dropped: a sub-mark
    must not advertise the base model's own name, or a query naming the base
    model ties against every sub-mark and the matcher answers nothing.
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
    # identity designations: that is what lets the matcher identify a
    # vanilla or modded class from its own text with no per-mod class list.
    # The category words the corpus keeps for documentation are left out
    # on purpose - "tracked" or "transport" would match half the catalogue
    # and tie every query.
    keyword_keys: list[str] = []
    for key in _normalised_list(entry.get("keywords")):
        if key in alias_keys or key in _CATEGORY_WORDS:
            continue
        # A curated keyword is held for documentation and many of them are
        # categories ("mrap", "attack", "mainbattletank") or makers. Those
        # must not reach the matcher: they tie a query against a whole
        # class instead of naming one thing.
        if key in shared_words and not any(ch.isdigit() for ch in key):
            continue
        keyword_keys.append(key)
    own_identity = _designation_fold(entry.get("canonical_name") or "")
    for key in designations(entry):
        if key in alias_keys or key in keyword_keys:
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


def load_binding_classes(data_dir: Path = DEFAULT_DATA) -> dict[str, list[str]]:
    """Map each catalogue id to the base-game classes research has bound.

    Only a binding read out of the BASE GAME's own config is kept, which
    its locator shows by sitting under the game's "a3" addon root. Those
    are the classes whose own text names no real vehicle - a fictional
    in-game name cannot be derived back to the thing it was modelled on -
    so the researched binding is the only evidence there is.

    Every other binding describes content outside the base game. Those are
    dropped: the matcher identifies such a class generically, from the
    designations the real vehicle is published under, so it needs no list
    and must not carry one.
    """
    path = data_dir / BINDINGS_FILE
    if not path.is_file():
        return {}
    try:
        loaded: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    payload = loaded if isinstance(loaded, dict) else {}
    records = payload.get("bindings")
    if not isinstance(records, list):
        return {}
    owners: dict[str, set[str]] = {}
    for raw in records:
        if not isinstance(raw, dict):
            continue
        catalogue_id = raw.get("catalogue_id")
        game_class = raw.get("game_class")
        # Keep only a binding whose evidence is the BASE GAME's own data:
        # a config read out of the game's Addons tree AND a display name
        # read out of the game's own stringtable namespace. A binding
        # evidenced by any other package describes content that is not the
        # base game, and the matcher identifies that generically, from the
        # designations the real vehicle is published under.
        locator = raw.get("config_locator")
        name_key = raw.get("display_name_key")
        if not isinstance(locator, str) or not locator.strip().startswith("Addons/"):
            continue
        if not isinstance(name_key, str) or not name_key.strip().upper().startswith(
            "$STR_A3_"
        ):
            continue
        if isinstance(catalogue_id, str) and isinstance(game_class, str):
            owners.setdefault(catalogue_id, set()).add(game_class)
    return {key: sorted(value) for key, value in owners.items()}


def class_index(
    load: catalogue.CatalogueLoad,
    extra: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """Map each catalogue id to its sorted mapped game classes.

    ``extra`` unions the stringtable bindings into the class map, so a vanilla
    class that only its display name names still reaches the exact_class layer.
    """
    owners: dict[str, set[str]] = {}
    for mapping in load.mappings:
        owners.setdefault(mapping.catalogue_id, set()).add(mapping.game_class)
    for catalogue_id, classes in (extra or {}).items():
        owners.setdefault(catalogue_id, set()).update(classes)
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
    records = [record for record in records if not _is_family(record)]
    # Every entry's own folded canonical name. A derived designation equal
    # to another entry's name is that entry's identity, not this one's.
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
    rows: list[list[object]] = []
    for record in records:
        entry = _mapping(record)
        if entry is None:
            continue
        cid = entry.get("catalogue_id")
        classes = table.get(cid, ()) if isinstance(cid, str) else ()
        row = build_row(entry, classes, reserved, shared)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda row: (str(row[COL_CATALOGUE]), str(row[COL_VARIANT])))
    return rows


def load_rows(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Read the catalogue layer and build every runtime row."""
    load = catalogue.load(data_dir)
    index = class_index(load, load_binding_classes(data_dir))
    return build_rows((entry.to_mapping() for entry in load.entries), index)


def _is_family(record: object) -> bool:
    """True when the record names a family and no mark."""
    entry = _mapping(record)
    return entry is not None and entry.get("family") is True


def build_family_row(record: object) -> list[object] | None:
    """Return the family row of a family entry, or None when no row emits.

    The row keeps the nine-column shape, so the result formatter is the one
    the mark table uses. Its class, alias and source columns stay empty: a
    family names no mark, and it is reached by its designation alone. The
    designation is the entry's own keyword list and is never derived, so a
    family cannot pick up a mark's term from its name.
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
    """Read the catalogue layer and build the family table."""
    load = catalogue.load(data_dir)
    return build_family_rows(entry.to_mapping() for entry in load.entries)


def _number(value: object) -> int | float:
    """Return a JSON number, or 0 for anything else. A bool is not a number."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return value
    return 0


def _held_number(values: dict[str, object], field: str) -> int | float:
    """Return the held value of one field as a number, or 0 when absent."""
    held = catalogue.held_value(values, field)
    if held is None:
        return 0
    return _number(held.get("value"))


def build_band_row(record: object) -> list[object] | None:
    """Return one classification-band row, or None when the entry has no id.

    The row is the property fallback of the classifier: the catalogue id, the
    vehicle type, the tracked flag, the resolved operating weight and the three
    held extents. The mass resolves through the shared catalogue ladder, so a
    derived operating weight is carried. A missing extent is a labelled zero,
    because the corpus holds no derivation for it.
    """
    entry = _mapping(record)
    if entry is None:
        return None
    catalogue_id = _text(entry.get("catalogue_id"))
    vehicle_type = entry.get("vehicle_type")
    if catalogue_id is None or not isinstance(vehicle_type, str):
        return None
    values = _mapping(entry.get("values")) or {}
    mass = _number(catalogue.resolve_field(values, "operating_weight_kg").value)
    return [
        catalogue_id,
        vehicle_type,
        1 if vehicle_type == "tracked" else 0,
        mass,
        _held_number(values, "length_mm"),
        _held_number(values, "width_mm"),
        _held_number(values, "height_mm"),
    ]


def build_band_rows(records: Iterable[object]) -> list[list[object]]:
    """Build every band row and sort it by catalogue id."""
    rows: list[list[object]] = []
    for record in records:
        row = build_band_row(record)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda row: str(row[0]))
    return rows


def load_band_rows(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Read the catalogue layer and build every band row."""
    load = catalogue.load(data_dir)
    return build_band_rows(entry.to_mapping() for entry in load.entries)


def format_band_row(row: Sequence[object]) -> str:
    """Render one band row in the fixed seven-column shape."""
    return "    [" + ", ".join(_sqf(item) for item in row) + "]"


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


def _named_ancestor(
    rows: Sequence[Sequence[object]], class_name: str
) -> Sequence[object] | None:
    """The one entry that maps an ancestor classname, or None.

    The mapped-class test only. A mod may rewrite any ancestor's displayName,
    so an ancestor named by its text is not stable evidence; its classname is.
    """
    key = normalise(class_name)
    picked = [row for row in rows if key in str(row[COL_CLASSES]).split("|")]
    return picked[0] if len(picked) == 1 else None


def _claims(row: Sequence[object], tokens: set[str]) -> bool:
    """True when a query token names something the entry is identified by.

    The retexture test: a class that carries the ancestor's family word, or a
    maker or model the ancestor's entry is published under, is the same article
    in new paint. A class that carries neither is a different article, and the
    inherited layer must refuse it even where the config chain is short.
    """
    blob = "|".join(
        (str(row[COL_CATALOGUE]), str(row[COL_ALIASES]), str(row[COL_KEYWORDS]))
    )
    return any(len(token) >= SCAN_MIN and token in blob for token in tokens)


def match_row(
    rows: Sequence[Sequence[object]],
    class_name: str,
    display_name: str = "",
    ancestors: Sequence[str] = (),
    families: Sequence[Sequence[object]] = (),
) -> list[object] | None:
    """Reference mirror of the generated seven-layer ladder.

    The generated SQF file is the runtime authority. This mirror exists so the
    Python harness can prove that the emitted table resolves an identity to a
    value row. It reads identity text only and returns the same seven-element
    result array, or None. The inheritance layer approximates ``isKindOf`` by
    an exact token match, because the harness cannot query the engine class
    tree. The inherited layer needs that tree, so the caller passes the
    ancestor classnames, nearest first.

    ``families`` is the family table. The family layer runs last, and only a
    single family row matching a designation of at least ``SCAN_MIN``
    characters answers. Two families in one query answer nothing.
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

    for ancestor_name in ancestors:
        found = _named_ancestor(rows, ancestor_name)
        if found is None:
            continue
        # The nearest named ancestor decides. When the class text does not
        # name its entry, the neighbour is a different thing, not a donor.
        if _claims(found, tokens):
            return result(found, 6, "inherited")
        return None

    family = [
        row
        for row in families
        if any(
            len(word) >= SCAN_MIN and word in query
            for word in str(row[COL_KEYWORDS]).split("|")
        )
    ]
    if len(family) == 1:
        return result(family[0], 7, "family")
    return None


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


def render_bands(rows: Sequence[Sequence[object]]) -> str:
    """Render the classification-band file for the given rows."""
    body = ",\n".join(format_band_row(row) for row in rows)
    return BAND_TEMPLATE.replace("__ROWS__", body)


def write_outputs(data_dir: Path = DEFAULT_DATA) -> list[list[object]]:
    """Write every generated file and return the matcher rows."""
    rows = load_rows(data_dir)
    MATCH_OUT.write_text(
        render_match(rows, load_family_rows(data_dir)), encoding="utf-8"
    )
    DATA_OUT.write_text(render_data(), encoding="utf-8")
    BANDS_OUT.write_text(render_bands(load_band_rows(data_dir)), encoding="utf-8")
    return rows


def check_outputs(
    data_dir: Path,
    match_out: Path = MATCH_OUT,
    data_out: Path = DATA_OUT,
    bands_out: Path = BANDS_OUT,
) -> int:
    """Return 0 when every generated file matches a fresh render.

    Check mode writes nothing. A missing or stale file returns 1, so a stale
    generated matcher or band table fails the gate.
    """
    rows = load_rows(data_dir)
    expected = {
        match_out: render_match(rows, load_family_rows(data_dir)),
        data_out: render_data(),
        bands_out: render_bands(load_band_rows(data_dir)),
    }
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
        f"vehicle projection: {len(rows)} rows -> {match_out.name}, "
        f"{data_out.name} and {bands_out.name} (fresh)"
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
        f"wrote {MATCH_OUT.name}, {DATA_OUT.name} and {BANDS_OUT.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
