#include "..\..\script_component.hpp"

// ─── Biome name table (shared by override and final lookup) ──────────
// The full 30-code Koppen set: 5 main groups, second letter s/w/f
// precipitation, third letter a/b/c/d temperature (AR 70-38 uses this
// Koppen (1931) structure for its military operating environments).
private _BIOME_NAMES = createHashMapFromArray [
    ["Af", "Tropical Rainforest"], ["Am", "Monsoon Tropical"],
    ["Aw", "Tropical Savanna"],    ["BSh", "Hot Semi-Arid"],
    ["BSk", "Cold Semi-Arid"],     ["BWk", "Cold Desert"],
    ["BWh", "Hot Desert"],         ["Csa", "Hot Mediterranean"],
    ["Csb", "Warm Mediterranean"], ["Csc", "Cool Mediterranean"],
    ["Cfa", "Humid Subtropical"],  ["Cfb", "Oceanic"],
    ["Cfc", "Subpolar Oceanic"],   ["Cwa", "Monsoon Subtropical"],
    ["Cwb", "Subtropical Highland"], ["Cwc", "Cool Subtropical Highland"],
    ["Dsa", "Dry-Summer Continental"], ["Dsb", "Cool Dry-Summer Continental"],
    ["Dsc", "Subarctic Dry-Summer"], ["Dsd", "Severe Subarctic Dry-Summer"],
    ["Dwa", "Monsoon Continental"], ["Dwb", "Cool Monsoon Continental"],
    ["Dwc", "Subarctic Monsoon"],  ["Dwd", "Severe Subarctic Monsoon"],
    ["Dfa", "Hot Continental"],    ["Dfb", "Humid Continental"],
    ["Dfc", "Subarctic"],          ["Dfd", "Severe Subarctic"],
    ["ET", "Tundra"],              ["EF", "Ice Cap"]
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
// The getVariable default must NOT be nil: `private _x = nil` does not
// bind the local in SQF, so the next line's `_cached` reads as undefined
// and errors every tick.  Use a string sentinel.
private _cached = missionNamespace getVariable [QGVAR(biomeCached), ""];
if (_cached isNotEqualTo "") then { _cached } else {

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
private _lat = ([] call EFUNC(core,getWorldLocation)) select 1;  // magnitude
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
    private _code = _x;
    _scores set [_code, (_scores getOrDefault [_code, 0]) + ((_vegScores get _code) * 8)];
} forEach (keys _vegScores);
{
    private _code = _x;
    _scores set [_code, (_scores getOrDefault [_code, 0]) + ((_surfaceScores get _code) * 4)];
} forEach (keys _surfaceScores);
{
    private _code = _x;
    _scores set [_code, (_scores getOrDefault [_code, 0]) + ((_structScores get _code) * 3)];
} forEach (keys _structScores);

// Elevation refinement: high terrain genuinely shifts the climate
// (lapse rate ~6.5 C/km, Koppen altitude rule).  A 1500 m+ mean elevation
// forces the subarctic/tundra verdicts hard enough to override a
// temperate climate anchor — mountains are colder than their latitude
// suggests.  Weight 15 beats the climate anchor's 10.
if (_meanElev > 1500) then {
    _scores set ["Dfc", (_scores getOrDefault ["Dfc", 0]) + 15];
    _scores set ["ET",  (_scores getOrDefault ["ET",  0]) + 8];
};

// ─── Pick winner with confidence gate ─────────────────────────────
// TERCOM/DSMAC position-fixing doctrine (innovation gate): the terrain
// refinement is accepted only when UNAMBIGUOUS - the winner must clear
// the runner-up by the peak-to-sidelobe ratio.  An ambiguous match
// (two signals nearly tied) is rejected, never forced: the climate
// anchor holds.  Ratio 1.4: a full-coverage indicator species (24 vs
// anchor 10) passes at 2.4; a moderate signal (12 vs 10) abstains at
// 1.2; the elevation override (15 vs 10) passes at 1.5.
private _marginRatio = 1.4;
private _bestCode = "";
private _bestScore = 0;
private _secondScore = 0;
{
    private _s = _scores get _x;
    if (_s > _bestScore) then {
        _secondScore = _bestScore;
        _bestScore = _s;
        _bestCode = _x;
    } else {
        if (_s > _secondScore) then { _secondScore = _s; };
    };
} forEach (keys _scores);

// Ambiguous match: the winner did not clear the runner-up by the
// ratio, so the terrain evidence does not justify moving off the
// climate anchor.  Abstain (keep the anchor) rather than force a
// weak match - the doctrine's "reject, never override" rule.
if (_bestCode != _climateBiome && {_bestScore < (_secondScore * _marginRatio)}) then {
    _bestCode = _climateBiome;
};

if (_bestCode == "") then { _bestCode = "Cfb"; };
private _bestName = _BIOME_NAMES getOrDefault [_bestCode, _bestCode];

missionNamespace setVariable [QEGVAR(core,biome), _bestCode];
missionNamespace setVariable [QEGVAR(core,biomeName), _bestName];

if (missionNamespace getVariable [QEGVAR(core,diagnostic), false]) then {
    diag_log text format [
        "[AEE] Biome dynamic: %1 (%2) lat=%3 water=%4 elev=%5 | climate=%6 veg=%7",
        _bestCode, _bestName, _lat, _waterFrac, _meanElev,
        _climateBiome, count _vegScores
    ];
};

missionNamespace setVariable [QGVAR(biomeCached), _bestCode];
_bestCode
};
