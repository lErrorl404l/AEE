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
    ["frostjacket", "garment", 0.79, 1],
    ["cummerbund", "webbing", 0.235, 2],
    ["rainjacket", "garment", 0.485, 1],
    ["windjacket", "garment", 0.215, 1],
    ["camocloak", "uniform", 0.55, 1],
    ["slickster", "vest", 0.402, 1],
    ["stahlhelm", "helmet", 1.19, 2],
    ["urbanruck", "rucksack", 1.021, 1],
    ["foretrex", "gps", 0.088, 1],
    ["kolpak20", "helmet", 2.2, 1],
    ["modframe", "rucksack", 2.041, 1],
    ["redacted", "webbing", 0.227, 1],
    ["wraith4k", "optic", 0.612, 1],
    ["wraithhd", "optic", 1.029, 1],
    ["ceramic", "vest", 2.5, 3],
    ["jaakari", "rucksack", 2.38, 1],
    ["javelin", "thermal", 7.0, 1],
    ["minikeg", "rucksack", 1.3, 1],
    ["salomon", "footwear", 0.305, 1],
    ["sandman", "suppressor", 0.502, 1],
    ["subzero", "vest", 0.57, 1],
    ["ak301m", "mount", 0.082, 1],
    ["brodie", "helmet", 1.1, 1],
    ["chesty", "vest", 0.294, 2],
    ["hs507c", "optic", 0.044, 1],
    ["leap02", "mount", 0.063, 1],
    ["leap03", "mount", 0.045, 2],
    ["leap10", "mount", 0.04, 2],
    ["leap14", "mount", 0.045, 2],
    ["protac", "light", 0.189, 4],
    ["reaper", "vest", 0.38, 1],
    ["virpro", "light", 0.24, 2],
    ["alice", "rucksack", 1.4, 1],
    ["altyn", "helmet", 3.5, 1],
    ["atacr", "optic", 0.595, 1],
    ["drsth", "mount", 0.065, 1],
    ["drsth", "optic", 0.51, 1],
    ["ecwcs", "garment", 0.365, 12],
    ["envgb", "thermal", 0.907, 2],
    ["esapi", "vest", 2.5, 5],
    ["gpnvg", "nv", 0.8, 1],
    ["hatka", "rucksack", 0.48, 1],
    ["hm3xt", "optic", 0.329, 1],
    ["kzero", "vest", 0.97, 1],
    ["m600v", "light", 0.136, 1],
    ["mark6", "optic", 0.669, 1],
    ["molle", "rucksack", 2.7, 2],
    ["nitro", "binocular", 0.695, 1],
    ["pasgt", "helmet", 1.66, 2],
    ["pasgt", "vest", 4.05, 2],
    ["peq15", "laser", 0.213, 1],
    ["pvs14", "nv", 0.35, 1],
    ["pvs15", "nv", 0.7, 1],
    ["pvs31", "nv", 0.45, 2],
    ["razor", "optic", 0.61, 1],
    ["scrim", "uniform", 0.11, 1],
    ["socom", "suppressor", 0.538, 2],
    ["spear", "rangefinder", 0.425, 1],
    ["ssh40", "helmet", 1.3, 1],
    ["ssh68", "helmet", 1.61, 4],
    ["6b13", "vest", 5.0, 1],
    ["6b17", "vest", 5.0, 1],
    ["6b18", "vest", 4.6, 1],
    ["6b23", "vest", 7.55, 4],
    ["6b45", "vest", 8.0, 1],
    ["6b47", "helmet", 1.0, 1],
    ["aems", "optic", 0.162, 3],
    ["amap", "rucksack", 0.96, 1],
    ["avs9", "nv", 0.55, 1],
    ["dbal", "laser", 0.22, 2],
    ["fast", "helmet", 0.667, 3],
    ["fcpc", "vest", 0.44, 2],
    ["haix", "footwear", 0.68, 6],
    ["hm3x", "optic", 0.278, 1],
    ["ihps", "helmet", 1.36, 1],
    ["ilbe", "rucksack", 3.6, 1],
    ["iotv", "vest", 14.0, 3],
    ["m110", "suppressor", 0.907, 1],
    ["mawl", "laser", 0.306, 2],
    ["mbav", "vest", 7.3, 1],
    ["mich", "helmet", 1.495, 2],
    ["ngal", "laser", 0.142, 1],
    ["peq2", "laser", 0.21, 1],
    ["pvs7", "nv", 0.68, 1],
    ["sapi", "vest", 1.82, 5],
    ["spcs", "vest", 10.0, 1],
    ["tlr1", "light", 0.122, 1],
    ["tlr7", "light", 0.073, 2],
    ["x300", "light", 0.116, 1],
    ["6b2", "vest", 4.2, 1],
    ["6b3", "vest", 10.2, 2],
    ["6b5", "vest", 6.5, 6],
    ["6b6", "helmet", 1.5, 1],
    ["ach", "helmet", 1.429, 4],
    ["akr", "mount", 0.067, 1],
    ["cpe", "vest", 0.37, 1],
    ["ech", "helmet", 1.5, 1],
    ["g24", "nv", 0.162, 1],
    ["k19", "vest", 1.1, 1],
    ["lwh", "helmet", 1.45, 1],
    ["m92", "helmet", 1.5, 1],
    ["msv", "vest", 11.0, 1],
    ["nt4", "suppressor", 0.624, 1],
    ["otv", "vest", 5.6, 2],
    ["rba", "vest", 7.3, 3]
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
