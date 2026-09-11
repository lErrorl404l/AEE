#include "..\script_component.hpp"

// ─── Biome name table (shared by override and final lookup) ──────────
private _BIOME_NAMES = createHashMapFromArray [
    ["Af", "Tropical Rainforest"], ["Am", "Monsoon Tropical"],
    ["Aw", "Tropical Savanna"],    ["BSh", "Hot Semi-Arid"],
    ["BSk", "Cold Semi-Arid"],     ["BWk", "Cold Desert"],
    ["BWh", "Hot Desert"],         ["Csa", "Hot Mediterranean"],
    ["Csb", "Warm Mediterranean"], ["Cfa", "Humid Subtropical"],
    ["Cfb", "Oceanic"],            ["Cwa", "Monsoon Subtropical"],
    ["Dfa", "Hot Continental"],    ["Dfb", "Humid Continental"],
    ["Dfc", "Subarctic"],          ["ET", "Tundra"],
    ["EF", "Ice Cap"]
];

// ─── Module override (EDEN/Zeus) ────────────────────────────────────
// Check for module-placed biome override before running auto-detection
private _moduleOverride = missionNamespace getVariable [QEGVAR(core,moduleBiomeOverride), ""];
if (_moduleOverride != "") exitWith {
    private _name = _BIOME_NAMES getOrDefault [_moduleOverride, _moduleOverride];
    missionNamespace setVariable [QEGVAR(core,biome), _moduleOverride];
    missionNamespace setVariable [QEGVAR(core,biomeName), _name];
};

// ─── Surface type → biome votes ──────────────────────────────────────
// Each entry: [biomeCode, weight] where biome gets one vote per sample
// Higher weight = stronger signal for that biome from this surface type
private _SURFACE_VOTES = createHashMapFromArray [
    ["#GdtForest",       [["Cfb",3], ["Dfb",2], ["Dfc",1]]],
    ["#GdtConiferous",   [["Dfb",3], ["Dfc",2]]],
    ["#GdtGrass",        [["Cfb",2], ["BSk",2], ["Dfb",1]]],
    ["#GdtGrassLand",    [["Cfb",2], ["BSk",2], ["Dfb",1]]],
    ["#GdtPrairie",      [["BSk",3], ["Dfb",1]]],
    ["#GdtJungle",       [["Af",3],  ["Am",2]]],
    ["#GdtRainForest",   [["Af",3],  ["Am",2]]],
    ["#GdtDesert",       [["BWh",3], ["BWk",2], ["BSh",1]]],
    ["#GdtSand",         [["BWh",3], ["BWk",2]]],
    ["#GdtDunes",        [["BWh",3], ["BSh",1]]],
    ["#GdtTundra",       [["ET",3],  ["Dfc",2]]],
    ["#GdtSnow",         [["Dfc",3], ["ET",2]]],
    ["#GdtIce",          [["EF",3],  ["ET",2]]],
    ["#GdtGlacier",      [["EF",3],  ["ET",1]]],
    ["#GdtSwamp",        [["Af",2],  ["Cfb",1]]],
    ["#GdtMarsh",        [["Af",2],  ["Cfb",1]]],
    ["#GdtVineyard",     [["Csa",3], ["Cfa",1]]],
    ["#GdtOrchard",      [["Cfb",2], ["Cfa",1]]],
    ["#GdtField",        [["Cfb",2], ["Dfb",1]]],
    ["#GdtCrop",         [["Cfb",2], ["Dfb",1]]],
    ["#GdtRock",         [["Dfb",1], ["Dfc",1]]],
    ["#GdtMountain",     [["Dfc",2], ["ET",1]]]
];

// ─── Override check ──────────────────────────────────────────────────
private _biomeOverride = missionNamespace getVariable [QEGVAR(core,biome), nil];
if (!isNil "_biomeOverride" && (_biomeOverride != "AUTO")) exitWith {
    missionNamespace setVariable [QEGVAR(core,biome), _biomeOverride];
    private _name = _BIOME_NAMES getOrDefault [_biomeOverride, _biomeOverride];
    missionNamespace setVariable [QEGVAR(core,biomeName), _name];
};

// ─── Collect signals ─────────────────────────────────────────────────
private _world = worldName;
private _biome = "";
private _biomeName = "";

// --- Step 1: Exact map name match (weight 10 — immediate return) ----
private _MAP_BIOMES = createHashMapFromArray [
    ["Altis",     ["Csa", "Hot Mediterranean"]],  ["Stratis",   ["Csa", "Hot Mediterranean"]],
    ["Tanoa",     ["Af",  "Tropical Rainforest"]], ["Lingor",    ["Af",  "Tropical Rainforest"]],
    ["Enoch",     ["Dfb", "Humid Continental"]],  ["Livonia",   ["Dfb", "Humid Continental"]],
    ["Chernarus", ["Dfb", "Humid Continental"]],  ["chernarus_summer", ["Dfb", "Humid Continental"]],
    ["Takistan",  ["BSk", "Cold Semi-Arid"]],     ["Malden",    ["Csa", "Hot Mediterranean"]],
    ["Sahrani",   ["Aw",  "Tropical Savanna"]],   ["Kujari",    ["BSh", "Hot Semi-Arid"]],
    ["Weferlingen", ["Cfb", "Oceanic"]],           ["CamLaoNam", ["Am",  "Monsoon Tropical"]],
    ["Xcam_taolao",["Am",  "Monsoon Tropical"]],  ["Isladuala", ["Af",  "Tropical Rainforest"]],
    ["Caribou",   ["Dfc", "Subarctic"]],           ["tem_anizay",["BWh", "Hot Desert"]]
];
if (_world in _MAP_BIOMES) exitWith {
    private _entry = _MAP_BIOMES get _world;
    missionNamespace setVariable [QEGVAR(core,biome), _entry select 0];
    missionNamespace setVariable [QEGVAR(core,biomeName), _entry select 1];
};

// --- Step 2: CfgWorlds description keyword match (weight 5 — immediate return) ---
private _cfg = configFile >> "CfgWorlds" >> _world;
private _desc = toLower (getText (_cfg >> "description"));
if (_desc != "") then {
    if ("tropical" in _desc)       then { _biome = "Af";  _biomeName = "Tropical Rainforest"; };
    if ("desert" in _desc)         then { _biome = "BWh"; _biomeName = "Hot Desert"; };
    if ("arid" in _desc)           then { _biome = "BSh"; _biomeName = "Hot Semi-Arid"; };
    if ("temperate" in _desc)      then { _biome = "Cfb"; _biomeName = "Oceanic"; };
    if ("mediterranean" in _desc)  then { _biome = "Csa"; _biomeName = "Hot Mediterranean"; };
    if ("continental" in _desc)    then { _biome = "Dfb"; _biomeName = "Humid Continental"; };
    if ("arctic" in _desc)         then { _biome = "ET";  _biomeName = "Tundra"; };
    if ("snow" in _desc)           then { _biome = "Dfc"; _biomeName = "Subarctic"; };
};
if (_biome != "") exitWith {
    missionNamespace setVariable [QEGVAR(core,biome), _biome];
    missionNamespace setVariable [QEGVAR(core,biomeName), _biomeName];
};

// --- Step 3: Weighted consensus voting (surface + latitude) ---------
// Only reached if steps 1 and 2 found nothing
private _scores = createHashMapFromArray []; // biome code -> total weight

// 3a: Surface type scan — 8 samples in a star pattern
private _ws = worldSize;
for "_i" from 0 to 7 do {
    private _angle = _i * 45;
    private _dist = _ws * (0.25 + random 0.25); // 25%-50% from center
    private _pos = [
        (_ws / 2) + (sin _angle * _dist),
        (_ws / 2) + (cos _angle * _dist)
    ];
    // Bounds check
    if (_pos#0 >= 0 && _pos#0 <= _ws && _pos#1 >= 0 && _pos#1 <= _ws) then {
        private _type = toLower (surfaceType _pos);
        private _votes = _SURFACE_VOTES getOrDefault [_type, []];
        { _scores set [_x#0, (_scores getOrDefault [_x#0, 0]) + (_x#1 * 7)]; } forEach _votes;
    };
};

// 3b: Latitude vote (weight 3 per vote)
private _lat = abs getNumber (_cfg >> "latitude");
if (_lat == 0) then { _lat = 40; };
private _latVotes = switch (true) do {
    case (_lat < 10):    { [["Af",3],  ["Am",2],  ["Aw",1]] };
    case (_lat < 23.5):  { [["Aw",3],  ["BSh",2], ["Am",1]] };
    case (_lat < 30):    { [["BWh",3], ["BSh",2], ["Csa",1]] };
    case (_lat < 35):    { [["Csa",3], ["BSh",2], ["BWh",1]] };
    case (_lat < 45):    { [["Cfa",3], ["Csa",2], ["Cfb",1]] };
    case (_lat < 50):    { [["Cfb",3], ["Dfb",2], ["Cfa",1]] };
    case (_lat < 55):    { [["Dfb",3], ["Cfb",2], ["Dfc",1]] };
    case (_lat < 66.5):  { [["Dfb",3], ["Dfc",2], ["ET",1]]  };
    default              { [["ET",3],  ["Dfc",2], ["EF",1]]  };
};
{ _scores set [_x#0, (_scores getOrDefault [_x#0, 0]) + (_x#1 * 3)]; } forEach _latVotes;

// 3c: Pick winner
private _maxScore = 0;
{
    if (_y > _maxScore) then { _biome = _x; _maxScore = _y; };
} forEach _scores;

// --- Step 4: Hard fallback ---
if (_biome == "") then { _biome = "Cfb"; _biomeName = "Oceanic"; };

// --- Store results ---
missionNamespace setVariable [QEGVAR(core,biome), _biome];
missionNamespace setVariable [QGVAR(biomeName),
    _BIOME_NAMES getOrDefault [_biome, _biome]
];
