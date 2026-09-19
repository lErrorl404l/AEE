#include "..\..\script_component.hpp"

/*
One-time terrain signal scan (issue #123 — fully dynamic biome).

Reads the map's FACTS, not its names.  No map-name table, no class-name
keyword matching against unknown content.  Every signal is something the
engine actually exposes about the world:

  1. Vegetation category  - isKindOf [obj, "Tree"/"Bush"]: config
                            INHERITANCE, so any custom class that extends
                            the engine base classes is caught regardless
                            of its name.
  2. Vegetation species   - the object's MODEL PATH (config model entry):
                            the .p3d filename is the ground truth of what
                            the asset is.  A model file named t_palm IS a
                            palm whatever the wrapping class is called.
  3. Structure category   - isKindOf Building/House/Ruins: urban vs
                            wilderness, alpine rock / ruin signals.
  4. Ground texture       - surfaceType grid: the map's OWN CfgSurfaces
                            entries (custom maps define these in config,
                            so the ground signal is always factual).
  5. Water fraction       - surfaceIsWater grid: maritime/continental
                            discrimination (ocean moderates climate).
  6. Elevation stats      - getTerrainHeightASL: lapse-rate refinement.

The species/structural votes use model-path keywords.  Model files are
stable facts: map authors reuse or import the engine's asset files, whose
names encode the species (t_palm, t_pinus, cactus, ...).  Where no model
keyword matches, the object contributes nothing — the latitude + surface
signals still classify.

Runs ONCE at mission start; cached in QGVAR(terrainSignals).

Output shape (stored):
  [surfaceVotes, vegVotes, structureVotes, waterFrac, meanElevM, maxElevM]
  each votes map: biome code -> weight
*/

// Species indicator: model-path keywords -> Koppen votes.  These match
// the MODEL FILE, not the class: t_palm.p3d is a palm whatever the class
// wrapper.  Weight = signal strength (indicator species are the
// strongest evidence a biome is present).
private _VEG_RULES = [
    ["palm",       [["Af",3], ["Am",2]]],
    ["mangrove",   [["Af",3], ["Am",2]]],
    ["jungle",     [["Af",3], ["Am",2]]],
    ["cactus",     [["BWh",3], ["BSh",2]]],
    ["cacti",      [["BWh",3], ["BSh",2]]],
    ["acacia",     [["BSh",3], ["BSk",2]]],
    ["olea",       [["Csa",3], ["Cfa",1]]],
    ["olive",      [["Csa",3], ["Cfa",1]]],
    ["vitis",      [["Csa",3], ["Cfa",1]]],
    ["pinus",      [["Dfb",2], ["Dfc",3]]],
    ["picea",      [["Dfb",2], ["Dfc",3]]],
    ["spruce",     [["Dfb",2], ["Dfc",3]]],
    ["abies",      [["Dfb",2], ["Dfc",3]]],
    ["larix",      [["Dfc",3], ["ET",1]]],
    ["pine",       [["Dfb",2], ["Dfc",3]]],
    ["betula",     [["Dfb",2], ["Cfb",2]]],
    ["fagus",      [["Cfb",3], ["Dfb",2]]],
    ["quercus",    [["Cfa",3], ["Cfb",2]]],
    ["populus",    [["Cfa",2], ["Dfb",2]]],
    ["salix",      [["Dfc",2], ["Cfb",2]]],
    ["reed",       [["Cfb",2], ["Dfb",2]]],
    ["cattail",    [["Cfb",2], ["Dfb",2]]]
];

// Structure model-path keywords -> votes.  Ruins/dry-stone -> arid,
// alpine rock -> subarctic/tundra.  Only counts when a structure class
// matches (isKindOf Building/House/Ruins below).
private _STRUCT_RULES = [
    ["ruin",     [["BSh",2], ["BSk",2]]],
    ["drystone", [["BSh",2], ["BSk",2]]],
    ["dirt",     [["BWh",2], ["BSh",2]]],
    ["sand",     [["BWh",2], ["BSh",2]]],
    ["stone",    [["ET",2], ["Dfc",2]]],
    ["rock",     [["ET",2], ["Dfc",2]]]
];

// Surface -> Koppen votes (ground texture evidence).  Keys are the
// LOWERCASED surface type the map's CfgSurfaces produces.
private _SURFACE_VOTES = [
    ["#gdtdesert",       [["BWh",3], ["BWk",2], ["BSh",1]]],
    ["#gdtconiferous",   [["Dfb",3], ["Dfc",2]]],
    ["#gdtdunes",        [["BWh",3], ["BSh",1]]],
    ["#gdtforest",       [["Cfb",3], ["Dfb",2], ["Dfc",1]]],
    ["#gdtgrass",        [["Cfb",2], ["BSk",2], ["Dfb",1]]],
    ["#gdtgrassland",    [["Cfb",2], ["BSk",2], ["Dfb",1]]],
    ["#gdtice",          [["EF",3],  ["ET",2]]],
    ["#gdtjungle",       [["Af",3],  ["Am",2]]],
    ["#gdtprairie",      [["BSk",3], ["Dfb",1]]],
    ["#gdtrainforest",   [["Af",3],  ["Am",2]]],
    ["#gdtsand",         [["BWh",3], ["BWk",2]]],
    ["#gdtsnow",         [["Dfc",3], ["ET",2]]],
    ["#gdttundra",       [["ET",3],  ["Dfc",2]]],
    ["#gdtglacier",      [["EF",3],  ["ET",1]]],
    ["#gdtswamp",        [["Af",2],  ["Cfb",1]]],
    ["#gdtmarsh",        [["Af",2],  ["Cfb",1]]],
    ["#gdtvineyard",     [["Csa",3], ["Cfa",1]]],
    ["#gdtorchard",      [["Cfb",2], ["Cfa",1]]],
    ["#gdtfield",        [["Cfb",2], ["Dfb",1]]],
    ["#gdtcrop",         [["Cfb",2], ["Dfb",1]]],
    ["#gdtrock",         [["Dfb",1], ["Dfc",1]]],
    ["#gdtmountain",     [["Dfc",2], ["ET",1]]]
];

// ─── Scan ─────────────────────────────────────────────────────────────────
private _surfaceScores = createHashMap;
private _vegScores = createHashMap;
private _structScores = createHashMap;
private _vegCount = 0;
private _structCount = 0;
private _waterCount = 0;
private _sampleCount = 0;
private _elevSum = 0;
private _elevMax = 0;
private _ws = worldSize;

// 1. Ground surface + water + elevation: 64-point grid.
private _surfaceLookup = createHashMapFromArray _SURFACE_VOTES;
for "_x" from 1 to 8 do {
    for "_y" from 1 to 8 do {
        private _pos = [(_ws / 8) * (_x - 0.5), (_ws / 8) * (_y - 0.5), 0];
        if (surfaceIsWater _pos) then {
            _waterCount = _waterCount + 1;
        } else {
            private _type = toLower (surfaceType _pos);
            private _votes = _surfaceLookup getOrDefault [_type, []];
            {
                _surfaceScores set [_x#0, (_surfaceScores getOrDefault [_x#0, 0]) + (_x#1)];
            } forEach _votes;
        };
        private _elev = getTerrainHeightASL _pos;
        _elevSum = _elevSum + _elev;
        if (_elev > _elevMax) then { _elevMax = _elev; };
        _sampleCount = _sampleCount + 1;
    };
};

// 2. Vegetation + structures: classify every object by config INHERITANCE
//    (category) and MODEL PATH (species).  allMissionObjects "" reads
//    literally every object on the map; isKindOf filters by the engine
//    class hierarchy so custom classes are caught too.
{
    private _obj = _x;
    if ((_obj isKindOf "Tree") || (_obj isKindOf "Bush")) then {
        private _model = toLower (getText (configOf _obj >> "model"));
        {
            _x params ["_keyword", "_votes"];
            if (_model find _keyword >= 0) then {
                {
                    _vegScores set [_x#0, (_vegScores getOrDefault [_x#0, 0]) + (_x#1)];
                } forEach _votes;
                _vegCount = _vegCount + 1;
            };
        } forEach _VEG_RULES;
    };
    if ((_obj isKindOf "Building") || (_obj isKindOf "House") || (_obj isKindOf "Ruins")) then {
        private _model = toLower (getText (configOf _obj >> "model"));
        {
            _x params ["_keyword", "_votes"];
            if (_model find _keyword >= 0) then {
                {
                    _structScores set [_x#0, (_structScores getOrDefault [_x#0, 0]) + (_x#1)];
                } forEach _votes;
                _structCount = _structCount + 1;
            };
        } forEach _STRUCT_RULES;
    };
} forEach (allMissionObjects "");

// 3. Water fraction.
private _waterFrac = _waterCount / (_sampleCount max 1);

// 4. Elevation stats.
private _meanElev = _elevSum / (_sampleCount max 1);

// 5. Coverage-normalise the evidence channels.  Each stored score is the
//    AVERAGE vote weight per sample, i.e. weight x coverage fraction:
//    a surface covering half the map with vote weight 2 stores 1.0, a
//    full-coverage palm (weight 3) stores 3.0.  The fusion then applies
//    the documented channel weights (veg 8, surface 4, struct 3) against
//    the climate anchor (10): incidental signals stay below the anchor,
//    full-coverage indicator species (24) are the ADR's documented
//    override.  The scan MUST NOT pre-scale (the old *10/*20 combined
//    with the fusion *8/*4/*3 made terrain 40-160x the anchor and broke
//    the climate-primary contract, issue #184).
{
    _surfaceScores set [_x, _y / (_sampleCount max 1)];
} forEach _surfaceScores;
{
    _vegScores set [_x, _y / (_vegCount max 1)];
} forEach _vegScores;
{
    _structScores set [_x, _y / (_structCount max 1)];
} forEach _structScores;

private _signals = [_surfaceScores, _vegScores, _structScores, _waterFrac, _meanElev, _elevMax];
missionNamespace setVariable [QGVAR(terrainSignals), _signals];
missionNamespace setVariable [QGVAR(terrainScanDone), true];

_signals
