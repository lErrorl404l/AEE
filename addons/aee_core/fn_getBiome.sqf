#include "script_component.hpp"

// ─── Override check ────────────────────────────────────────────────────
// If GVAR(biome) was pre-set (e.g. by CBA setting or mission script)
// to anything other than "AUTO", skip detection and use that value.
private _biomeOverride = GVAR(biome);
if (!isNil "_biomeOverride" && {_biomeOverride != "AUTO"}) exitWith {
    missionNamespace setVariable [QGVAR(biome), _biomeOverride, true];
    // Look up a human-readable name for the override code
    private _biomeNames = createHashMapFromArray [
        ["Af", "Tropical Rainforest"], ["Am", "Monsoon Tropical"],
        ["Aw", "Tropical Savanna"],    ["BSh", "Hot Semi-Arid"],
        ["BSk", "Cold Semi-Arid"],     ["BWk", "Cold Desert"],
        ["BWh", "Hot Desert"],         ["Csa", "Hot Mediterranean"],
        ["Csb", "Warm Mediterranean"], ["Cfa", "Humid Subtropical"],
        ["Cfb", "Oceanic"],            ["Cwa", "Monsoon Subtropical"],
        ["Dfa", "Hot Continental"],    ["Dfb", "Humid Continental"],
        ["Dfc", "Subarctic"],          ["ET", "Tundra"]
    ];
    missionNamespace setVariable [QGVAR(biomeName),
        _biomeNames getOrDefault [_biomeOverride, _biomeOverride], true
    ];
};

private _world = worldName;
private _biome = "";
private _biomeName = "";

// --- Step 1: Hardcoded map lookup ---
private _mapBiomes = createHashMapFromArray [
    ["Altis",     ["Csa", "Hot Mediterranean"]],
    ["Stratis",   ["Csa", "Hot Mediterranean"]],
    ["Tanoa",     ["Af",  "Tropical Rainforest"]],
    ["Lingor",    ["Af",  "Tropical Rainforest"]],
    ["Enoch",     ["Dfb", "Humid Continental"]],
    ["Livonia",   ["Dfb", "Humid Continental"]],
    ["Chernarus", ["Dfb", "Humid Continental"]],
    ["chernarus_summer", ["Dfb", "Humid Continental"]],
    ["Takistan",  ["BSk", "Cold Semi-Arid"]],
    ["Malden",    ["Csa", "Hot Mediterranean"]],
    ["Sahrani",   ["Aw",  "Tropical Savanna"]],
    ["Kujari",    ["BSh", "Hot Semi-Arid"]],
    ["Weferlingen", ["Cfb", "Oceanic"]],
    ["CamLaoNam", ["Am",  "Monsoon Tropical"]],
    ["Xcam_taolao", ["Am", "Monsoon Tropical"]],
    ["Isladuala", ["Af",  "Tropical Rainforest"]],
    ["Caribou",   ["Dfc", "Subarctic"]],
    ["tem_anizay", ["BWh", "Hot Desert"]]
];

if (_world in _mapBiomes) then {
    private _entry = _mapBiomes get _world;
    _biome = _entry select 0;
    _biomeName = _entry select 1;
};

// --- Step 2: CfgWorlds description matching ---
if (_biome == "") then {
    private _cfg = configFile >> "CfgWorlds" >> _world;
    private _desc = toLower (getText (_cfg >> "description"));

    if (_desc find "tropical" > -1) then { _biome = "Af"; _biomeName = "Tropical Rainforest"; };
    if (_desc find "desert" > -1) then { _biome = "BWh"; _biomeName = "Hot Desert"; };
    if (_desc find "arid" > -1) then { _biome = "BSh"; _biomeName = "Hot Semi-Arid"; };
    if (_desc find "temperate" > -1) then { _biome = "Cfb"; _biomeName = "Oceanic"; };
    if (_desc find "mediterranean" > -1) then { _biome = "Csa"; _biomeName = "Hot Mediterranean"; };
    if (_desc find "continental" > -1) then { _biome = "Dfb"; _biomeName = "Humid Continental"; };
    if (_desc find "arctic" > -1) then { _biome = "ET"; _biomeName = "Tundra"; };
    if (_desc find "snow" > -1) then { _biome = "Dfc"; _biomeName = "Subarctic"; };
};

// --- Step 3: Latitude heuristic fallback ---
if (_biome == "") then {
    private _lat = getNumber (configFile >> "CfgWorlds" >> _world >> "latitude");
    if (_lat == 0) then { _lat = 40; };

    if (_lat < 10) then { _biome = "Af"; _biomeName = "Tropical Rainforest"; };
    if (_lat >= 10 && _lat < 23.5) then { _biome = "Aw"; _biomeName = "Tropical Savanna"; };
    if (_lat >= 23.5 && _lat < 35) then { _biome = "BSh"; _biomeName = "Hot Semi-Arid"; };
    if (_lat >= 35 && _lat < 45) then { _biome = "Csa"; _biomeName = "Hot Mediterranean"; };
    if (_lat >= 45 && _lat < 55) then { _biome = "Cfb"; _biomeName = "Oceanic"; };
    if (_lat >= 55 && _lat < 66.5) then { _biome = "Dfb"; _biomeName = "Humid Continental"; };
    if (_lat >= 66.5) then { _biome = "Dfc"; _biomeName = "Subarctic"; };
};

// --- Final fallback ---
if (_biome == "") then {
    _biome = "Cfa";
    _biomeName = "Humid Subtropical";
};

// --- Store results ---
missionNamespace setVariable [QGVAR(biome), _biome, true];
missionNamespace setVariable [QGVAR(biomeName), _biomeName, true];
