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

// ─── One-time cache ─────────────────────────────────────────────────
// The map biome is a static property of the world: latitude, water
// fraction, terrain signals and the fused verdict never change mid-
// mission (only the module override can force a biome).  The first call
// runs the full latitude-climate + terrain-scan + fusion; every later
// call returns the cached verdict in microseconds.  This keeps repeated
// calls (and the PHASE10 perf gate) cheap.
private _cached = missionNamespace getVariable [QGVAR(biomeCached), nil];
if (_cached isNotEqualTo nil) then { _cached } else {

// ─── Dynamic biome detection (issue #123) ────────────────────────────
// Fully data-driven: the biome is CLASSIFIED from the map's own facts,
// never looked up by map name or description keyword.  Four independent
// evidence channels are fused:
//
//   A. Latitude climate: the map's latitude (config) + water fraction
//      drive a 12-month climatology (fnc_getLatitudeClimate); the real
//      Koppen rules (fnc_classifyBiome) classify it.  This is the
//      climate-consistent verdict (Af..EF).
//   B. Terrain signal scan (fnc_scanTerrainSignals): surface textures,
//      indicator vegetation (model-path species), structures, elevation
//      from the map's own CfgSurfaces/objects — facts, no names.
//
// Fusion: the climate verdict from A is the primary class; the terrain
// signals from B adjust it — a climate that says "desert" is confirmed
// or refuted by actual cactus/sand evidence, and a map with palms at a
// temperate latitude is re-voted tropical by the strongest signal
// (indicator species).  The latitude climate keeps every vote inside a
// physically consistent band.
private _lat = ([] call EFUNC(core,getWorldLatitude)) select 1;  // magnitude
if (_lat == 0) then { _lat = 40; };

// Run the one-time terrain scan if it has not happened yet (it may have
// been triggered earlier by another consumer).
if (isNil {missionNamespace getVariable [QGVAR(terrainScanDone), nil]}) then {
    [] call FUNC(scanTerrainSignals);
};
private _signals = missionNamespace getVariable [QGVAR(terrainSignals), [createHashMap, createHashMap, createHashMap, 0, 0, 0]];
_signals params ["_surfaceScores", "_vegScores", "_structScores", "_waterFrac", "_meanElev", "_elevMax"];
if (isNil "_surfaceScores") then { _surfaceScores = createHashMap; };
if (isNil "_vegScores") then { _vegScores = createHashMap; };
if (isNil "_structScores") then { _structScores = createHashMap; };

// ─── Channel A: climate verdict (Koppen from latitude climatology) ──
private _normals = [_lat, _waterFrac] call FUNC(getLatitudeClimate);
private _tDay = _normals select 2;
private _tNight = _normals select 3;
private _precip = _normals select 5;
// Publish the latitude-driven normals so the 4 climate consumers
// (temperature, pressure, humidity, fog) use the map's actual climate
// instead of the static per-biome table — the "facts, not names" fix.
missionNamespace setVariable [QGVAR(climateNormals), _normals];
private _meanTemps = [];
for "_m" from 0 to 11 do {
    _meanTemps pushBack (((_tDay select _m) + (_tNight select _m)) / 2);
};
private _climateBiome = [_meanTemps, _precip, 0] call FUNC(classifyBiome);
if (_climateBiome == "") then { _climateBiome = "Cfb"; };

// ─── Channel B: terrain evidence fusion ─────────────────────────────
// The climate verdict is PRIMARY; terrain signals REFINE it within the
// climate's plausible thermal band, they do not override it.  A conifer
// signal can move Dfb -> Dfc (boreal), but cannot flip a temperate
// climate to tropical (that would need the climate itself to be
// tropical).  Weighted: climate 10, vegetation 8 (strongest signal),
// surface 4, structure 3 - deliberately less than the climate so the
// physical band stays the anchor.
private _scores = createHashMap;
_scores set [_climateBiome, 10];
{
    _scores set [_x#0, (_scores getOrDefault [_x#0, 0]) + (_x#1 * 8)];
} forEach _vegScores;
{
    _scores set [_x#0, (_scores getOrDefault [_x#0, 0]) + (_x#1 * 4)];
} forEach _surfaceScores;
{
    _scores set [_x#0, (_scores getOrDefault [_x#0, 0]) + (_x#1 * 3)];
} forEach _structScores;

// Elevation refinement: high terrain genuinely shifts the climate
// (lapse rate ~6.5 C/km, Koppen altitude rule).  A 1500 m+ mean elevation
// forces the subarctic/tundra verdicts hard enough to override a
// temperate climate anchor — mountains are colder than their latitude
// suggests.  Weight 15 beats the climate anchor's 10.
if (_meanElev > 1500) then {
    _scores set ["Dfc", (_scores getOrDefault ["Dfc", 0]) + 15];
    _scores set ["ET",  (_scores getOrDefault ["ET",  0]) + 8];
};

// ─── Pick winner ────────────────────────────────────────────────────
private _bestCode = "";
private _bestScore = 0;
{
    if (_y > _bestScore) then { _bestCode = _x; _bestScore = _y; };
} forEach _scores;

if (_bestCode == "") then { _bestCode = "Cfb"; };
private _bestName = _BIOME_NAMES getOrDefault [_bestCode, _bestCode];

missionNamespace setVariable [QEGVAR(core,biome), _bestCode];
missionNamespace setVariable [QEGVAR(core,biomeName), _bestName];

if (EGVAR(core,diagnostic)) then {
    diag_log text format [
        "[AEE] Biome dynamic: %1 (%2) lat=%3 water=%4 elev=%5 | climate=%6 veg=%7",
        _bestCode, _bestName, _lat, _waterFrac, _meanElev,
        _climateBiome, count _vegScores
    ];
};

missionNamespace setVariable [QGVAR(biomeCached), _bestCode];
_bestCode
};
