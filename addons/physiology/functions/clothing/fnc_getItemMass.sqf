#include "..\..\script_component.hpp"
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
    ["foretrex", "gps", 0.088, 1],
    ["wraith4k", "optic", 0.612, 1],
    ["wraithhd", "optic", 1.029, 1],
    ["javelin", "thermal", 7.0, 1],
    ["sandman", "suppressor", 0.502, 1],
    ["ak301m", "mount", 0.082, 1],
    ["hs507c", "optic", 0.044, 1],
    ["leap02", "mount", 0.063, 1],
    ["leap03", "mount", 0.045, 2],
    ["leap10", "mount", 0.04, 2],
    ["leap14", "mount", 0.045, 2],
    ["protac", "light", 0.189, 4],
    ["virpro", "light", 0.24, 2],
    ["atacr", "optic", 0.595, 1],
    ["drsth", "mount", 0.065, 1],
    ["drsth", "optic", 0.51, 1],
    ["envgb", "thermal", 0.907, 2],
    ["gpnvg", "nv", 0.8, 1],
    ["hm3xt", "optic", 0.329, 1],
    ["m600v", "light", 0.136, 1],
    ["mark6", "optic", 0.669, 1],
    ["nitro", "binocular", 0.695, 1],
    ["peq15", "laser", 0.213, 1],
    ["pvs14", "nv", 0.35, 1],
    ["pvs15", "nv", 0.7, 1],
    ["pvs31", "nv", 0.45, 2],
    ["razor", "optic", 0.61, 1],
    ["socom", "suppressor", 0.538, 2],
    ["spear", "rangefinder", 0.425, 1],
    ["aems", "optic", 0.162, 3],
    ["avs9", "nv", 0.55, 1],
    ["dbal", "laser", 0.22, 2],
    ["hm3x", "optic", 0.278, 1],
    ["m110", "suppressor", 0.907, 1],
    ["mawl", "laser", 0.306, 2],
    ["ngal", "laser", 0.142, 1],
    ["peq2", "laser", 0.21, 1],
    ["pvs7", "nv", 0.68, 1],
    ["tlr1", "light", 0.122, 1],
    ["tlr7", "light", 0.073, 2],
    ["x300", "light", 0.116, 1],
    ["akr", "mount", 0.067, 1],
    ["g24", "nv", 0.162, 1],
    ["nt4", "suppressor", 0.624, 1]
];

// The table is ordered longest family first, so the more specific keyword
// wins (an "lv-119" row outranks a "119" row).
private _match = 0;
{
    _x params ["_family", "_category", "_mass"];
    if ((_allowed isEqualTo [] || {_category in _allowed})
        && {_hay find _family >= 0}) exitWith {
        _match = _mass;
    };
} forEach _TABLE;

_match
