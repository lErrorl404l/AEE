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
    ["survival blanket", "medical", 0.052, 1],
    ["litter carrier", "medical", 0.454, 1],
    ["decompression", "", 0.028, 1],
    ["combat gauze", "medical", 0.023, 1],
    ["elastic wrap", "medical", 0.059, 1],
    ["field shield", "medical", 0.014, 1],
    ["laryngoscope", "medical", 0.283, 1],
    ["rolled gauze", "medical", 0.034, 1],
    ["combatgauze", "", 0.023, 1],
    ["frostjacket", "garment", 0.79, 1],
    ["polarshield", "misc", 0.071, 1],
    ["cummerbund", "webbing", 0.235, 2],
    ["medicalbag", "", 0.948, 3],
    ["quiklitter", "medical", 0.683, 2],
    ["rainjacket", "garment", 0.485, 1],
    ["sam splint", "medical", 0.128, 1],
    ["super tool", "tool", 0.272, 3],
    ["triangular", "", 0.045, 1],
    ["wave alpha", "tool", 0.234, 1],
    ["windjacket", "garment", 0.215, 1],
    ["camocloak", "uniform", 0.55, 1],
    ["chestseal", "", 0.041, 1],
    ["eyeshield", "", 0.006, 2],
    ["sam sling", "medical", 0.397, 1],
    ["samsplint", "", 0.09, 6],
    ["skeletool", "tool", 0.142, 2],
    ["slickster", "vest", 0.402, 1],
    ["stahlhelm", "helmet", 1.19, 2],
    ["urbanruck", "rucksack", 1.021, 1],
    ["cat case", "medical", 0.085, 1],
    ["firstaid", "", 0.322, 3],
    ["foretrex", "gps", 0.088, 1],
    ["free k2x", "tool", 0.139, 1],
    ["free k4x", "tool", 0.156, 1],
    ["kolpak20", "helmet", 2.2, 1],
    ["modframe", "rucksack", 2.041, 1],
    ["quikclot", "medical", 0.023, 2],
    ["redacted", "webbing", 0.227, 1],
    ["sidekick", "tool", 0.198, 1],
    ["traction", "", 0.68, 1],
    ["wraith4k", "optic", 0.612, 1],
    ["wraithhd", "optic", 1.029, 1],
    ["burntec", "", 0.55, 3],
    ["burntec", "medical", 1.361, 1],
    ["ceramic", "vest", 2.5, 3],
    ["free t2", "tool", 0.094, 1],
    ["israeli", "", 0.099, 1],
    ["iv pole", "medical", 0.369, 2],
    ["jaakari", "rucksack", 2.38, 1],
    ["javelin", "thermal", 7.0, 1],
    ["medikit", "", 3.118, 5],
    ["minikeg", "rucksack", 1.3, 1],
    ["nalgene", "hydration", 0.12, 4],
    ["salomon", "footwear", 0.305, 1],
    ["sandman", "suppressor", 0.502, 1],
    ["subzero", "vest", 0.57, 1],
    ["suction", "", 0.207, 1],
    ["wingman", "tool", 0.198, 1],
    ["aidbag", "", 1.987, 1],
    ["ak301m", "mount", 0.082, 1],
    ["bb2590", "power", 1.4, 1],
    ["brodie", "helmet", 1.1, 1],
    ["bt2590", "power", 1.4, 1],
    ["chesty", "vest", 0.294, 2],
    ["collar", "", 0.147, 1],
    ["cr2032", "power", 0.003, 1],
    ["gloves", "", 0.456, 1],
    ["hs507c", "optic", 0.044, 1],
    ["leap02", "mount", 0.063, 1],
    ["leap03", "mount", 0.045, 2],
    ["leap10", "mount", 0.04, 2],
    ["leap14", "mount", 0.045, 2],
    ["litter", "", 0.851, 1],
    ["prc117", "radio", 4.325, 2],
    ["prc152", "radio", 1.15, 2],
    ["prc158", "radio", 4.9, 2],
    ["prc160", "radio", 4.1, 1],
    ["prc163", "radio", 1.25, 1],
    ["prc165", "radio", 0.566, 1],
    ["prc167", "radio", 5.85, 1],
    ["prc171", "radio", 0.45, 1],
    ["protac", "light", 0.189, 4],
    ["raptor", "tool", 0.164, 1],
    ["reaper", "vest", 0.38, 1],
    ["reeves", "medical", 8.6, 1],
    ["rf7800", "radio", 3.74, 2],
    ["shears", "", 0.057, 1],
    ["signal", "tool", 0.213, 1],
    ["virpro", "light", 0.24, 2],
    ["alice", "rucksack", 1.4, 1],
    ["altyn", "helmet", 3.5, 1],
    ["atacr", "optic", 0.595, 1],
    ["celox", "", 0.031, 2],
    ["celox", "medical", 0.045, 1],
    ["chito", "", 0.02, 1],
    ["cr123", "power", 0.017, 1],
    ["dl123", "power", 0.017, 1],
    ["drsth", "mount", 0.065, 1],
    ["drsth", "optic", 0.51, 1],
    ["ecwcs", "garment", 0.365, 12],
    ["envgb", "thermal", 0.907, 2],
    ["esapi", "vest", 2.5, 5],
    ["gpnvg", "nv", 0.8, 1],
    ["hatka", "rucksack", 0.48, 1],
    ["hm3xt", "optic", 0.329, 1],
    ["hyfin", "medical", 0.057, 2],
    ["ivset", "", 0.037, 1],
    ["kzero", "vest", 0.97, 1],
    ["m600v", "light", 0.136, 1],
    ["mark6", "optic", 0.669, 1],
    ["micra", "tool", 0.051, 1],
    ["molle", "rucksack", 2.7, 2],
    ["nitro", "binocular", 0.695, 1],
    ["olaes", "", 0.095, 2],
    ["pasgt", "helmet", 1.66, 2],
    ["pasgt", "vest", 4.05, 2],
    ["peq15", "laser", 0.213, 1],
    ["pvs14", "nv", 0.35, 1],
    ["pvs15", "nv", 0.7, 1],
    ["pvs31", "nv", 0.45, 2],
    ["raven", "medical", 6.8, 1],
    ["razor", "optic", 0.61, 1],
    ["rebar", "tool", 0.19, 1],
    ["scrim", "uniform", 0.11, 1],
    ["socom", "suppressor", 0.538, 2],
    ["spear", "rangefinder", 0.425, 1],
    ["ssh40", "helmet", 1.3, 1],
    ["ssh68", "helmet", 1.61, 4],
    ["surge", "tool", 0.354, 1],
    ["talon", "medical", 6.8, 1],
    ["6b13", "vest", 5.0, 1],
    ["6b17", "vest", 5.0, 1],
    ["6b18", "vest", 4.6, 1],
    ["6b23", "vest", 7.55, 4],
    ["6b45", "vest", 8.0, 1],
    ["6b47", "helmet", 1.0, 1],
    ["aajt", "", 0.709, 1],
    ["aems", "optic", 0.162, 3],
    ["amap", "rucksack", 0.96, 1],
    ["avs9", "nv", 0.55, 1],
    ["bond", "tool", 0.176, 1],
    ["burn", "", 0.028, 1],
    ["cric", "", 0.126, 2],
    ["dbal", "laser", 0.22, 2],
    ["fast", "helmet", 0.667, 3],
    ["fcpc", "vest", 0.44, 2],
    ["haix", "footwear", 0.68, 6],
    ["hm3x", "optic", 0.278, 1],
    ["hpmk", "", 1.588, 1],
    ["ifak", "", 0.794, 4],
    ["ihps", "helmet", 1.36, 1],
    ["ilbe", "rucksack", 3.6, 1],
    ["iotv", "vest", 14.0, 3],
    ["jett", "", 0.68, 1],
    ["m110", "suppressor", 0.907, 1],
    ["mawl", "laser", 0.306, 2],
    ["mbav", "vest", 7.3, 1],
    ["mich", "helmet", 1.495, 2],
    ["narp", "medical", 6.0, 1],
    ["ngal", "laser", 0.142, 1],
    ["peq2", "laser", 0.21, 1],
    ["pvs7", "nv", 0.68, 1],
    ["sapi", "vest", 1.82, 5],
    ["sked", "", 7.711, 1],
    ["spcs", "vest", 10.0, 1],
    ["tlr1", "light", 0.122, 1],
    ["tlr7", "light", 0.073, 2],
    ["walk", "", 13.579, 1],
    ["wave", "tool", 0.241, 1],
    ["x300", "light", 0.116, 1],
    ["522", "power", 0.045, 1],
    ["6b2", "vest", 4.2, 1],
    ["6b3", "vest", 10.2, 2],
    ["6b5", "vest", 6.5, 6],
    ["6b6", "helmet", 1.5, 1],
    ["ach", "helmet", 1.429, 4],
    ["akr", "mount", 0.067, 1],
    ["bvm", "", 0.493, 3],
    ["cat", "medical", 0.076, 1],
    ["cpe", "vest", 0.37, 1],
    ["e91", "power", 0.023, 1],
    ["e92", "power", 0.011, 1],
    ["ech", "helmet", 1.5, 1],
    ["etd", "medical", 0.057, 2],
    ["g24", "nv", 0.162, 1],
    ["k19", "vest", 1.1, 1],
    ["l91", "power", 0.015, 1],
    ["l92", "power", 0.008, 1],
    ["lwh", "helmet", 1.45, 1],
    ["m92", "helmet", 1.5, 1],
    ["msv", "vest", 11.0, 1],
    ["mut", "tool", 0.318, 2],
    ["npa", "", 0.014, 1],
    ["npa", "medical", 0.009, 1],
    ["nt4", "suppressor", 0.624, 1],
    ["otv", "vest", 5.6, 2],
    ["rba", "vest", 7.3, 3],
    ["rev", "tool", 0.167, 1],
    ["ted", "medical", 0.7, 1],
    ["tfp", "food", 0.344, 2]
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
