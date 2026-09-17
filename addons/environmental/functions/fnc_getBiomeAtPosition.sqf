#include "..\script_component.hpp"

// ─── Per-position biome detection ─────────────────────────────────────
// Returns Koppen code for a given position using surface type, latitude,
// and elevation. Two-axis model: formation (surface) + climate (lat/elev).
//
// High-confidence surfaces return immediately. Low-confidence surfaces
// use latitude bands and elevation lapse rate to disambiguate.
//
// Reference: Peel 2007 (doi:10.5194/hess-11-1633-2007)
//
// Arguments: [_posASL]
//   0: Position ASL [x, y, z]
// Return: Koppen code string

params [
    ["_posASL", [], [[]]]
];

// Headless servers have no current unit, so updateEnvironment passes [].
// Fall back to the map-detected biome (fnc_getBiome result) instead of
// failing on the empty position.
if (count _posASL < 3) exitWith {
    missionNamespace getVariable [QEGVAR(core,biome), "Cfb"]
};

private _pos2D = [_posASL select 0, _posASL select 1];
private _elevation = _posASL select 2;

// ─── Surface type lookup ──────────────────────────────────────────────
// Two-tier system:
//   Tier 1: High-confidence surfaces → immediate return
//   Tier 2: Low-confidence surfaces → latitude + elevation disambiguation
private _surface = toLower (surfaceType _pos2D);

// Tier 1: High-confidence surface → biome mapping
// These surfaces have a strong, unambiguous biome signal.
private _DIRECT_MAP = createHashMapFromArray [
    ["#GdtDesert",   "BWh"],  // Hot Desert, arid sparse vegetation
    ["#GdtSand",     "BWh"],  // Sand, desert substrate
    ["#GdtDunes",    "BWh"],  // Dunes, desert landform
    ["#GdtJungle",   "Af"],   // Jungle, tropical rainforest
    ["#GdtRainForest","Af"],  // Rain Forest, tropical rainforest
    ["#GdtTundra",   "ET"],   // Tundra, treeless polar/subpolar
    ["#GdtIce",      "EF"],   // Ice, permanent ice cap
    ["#GdtGlacier",  "EF"],   // Glacier, permanent ice
    ["#GdtVineyard", "Csa"],  // Vineyard, Mediterranean agriculture
    ["#GdtPrairie",  "BSk"]   // Prairie, semi-arid grassland
];

if (_surface in _DIRECT_MAP) exitWith {
    _DIRECT_MAP get _surface
};

// ─── Latitude bands (Köppen primary thermal zones) ───────────────────
// Latitude magnitude from the shared source (issue #154 pattern 3).
// Peel 2007: A = all months >18°C, B = arid, C = 1–3 months <10°C,
// D = 1–3 months <0°C (or <−3°C Kottek), E = all months <10°C.
private _lat = ([] call EFUNC(core,getWorldLatitude)) select 1;
if (_lat == 0) then { _lat = 40; }; // fallback: temperate default

// Latitude band → primary Koppen zone
private _latBand = switch (true) do {
    case (_lat < 10):    { "A" };    // Equatorial
    case (_lat < 23.5):  { "A" };    // Tropical (Tropic of Cancer/Capricorn)
    case (_lat < 35):    { "B" };    // Subtropical arid
    case (_lat < 50):    { "C" };    // Temperate
    case (_lat < 66.5):  { "D" };    // Continental
    default              { "E" };    // Polar
};

// ─── Tier 2: Low-confidence surfaces → disambiguate with lat + elev ──
// These surfaces occur across multiple biomes. Use latitude band and
// elevation lapse rate to pick the most likely candidate.

// Elevation lapse rate: 6.5°C per 1000m (ICAO standard atmosphere)
// At high elevation, even tropical surfaces become temperate/continental.
private _elevEffect = _elevation / 1000 * 6.5; // temperature depression

// Surface + latitude band → candidate list [biome, weight]
private _CANDIDATE_MAP = createHashMapFromArray [
    // Forest types: depend on latitude and elevation
    ["#GdtForest", switch (_latBand) do {
        case "A": { [["Af",2], ["Am",1]] };
        case "B": { [["BSh",2], ["BSk",1]] };
        case "C": { [["Cfb",3], ["Cfa",1]] };
        case "D": { [["Dfb",3], ["Dfc",1]] };
        case "E": { [["Dfc",2], ["ET",1]] };
    }],
    ["#GdtConiferous", switch (_latBand) do {
        case "A": { [["Am",2], ["Cfb",1]] };
        case "B": { [["BSk",2], ["Cfb",1]] };
        case "C": { [["Cfb",2], ["Dfb",2]] };
        case "D": { [["Dfb",3], ["Dfc",2]] };
        case "E": { [["Dfc",3], ["ET",2]] };
    }],

    // Grass types: depend on latitude (precipitation proxy)
    ["#GdtGrass", switch (_latBand) do {
        case "A": { [["Aw",3], ["Am",1]] };
        case "B": { [["BSh",3], ["BSk",2]] };
        case "C": { [["Cfb",3], ["Cfa",1]] };
        case "D": { [["Dfb",2], ["Cfb",1]] };
        case "E": { [["ET",2], ["Dfc",1]] };
    }],
    ["#GdtGrassLand", switch (_latBand) do {
        case "A": { [["Aw",3], ["Am",1]] };
        case "B": { [["BSh",3], ["BSk",2]] };
        case "C": { [["Cfb",3], ["Cfa",1]] };
        case "D": { [["Dfb",2], ["Cfb",1]] };
        case "E": { [["ET",2], ["Dfc",1]] };
    }],

    // Wetland: depends on latitude (temperature determines type)
    ["#GdtSwamp", switch (_latBand) do {
        case "A": { [["Af",3], ["Am",2]] };
        case "B": { [["BSh",2], ["Cfa",1]] };
        case "C": { [["Cfa",2], ["Cfb",2]] };
        case "D": { [["Dfb",2], ["Dfc",1]] };
        case "E": { [["Dfc",2], ["ET",1]] };
    }],
    ["#GdtMarsh", switch (_latBand) do {
        case "A": { [["Af",3], ["Am",2]] };
        case "B": { [["BSh",2], ["Cfa",1]] };
        case "C": { [["Cfa",2], ["Cfb",2]] };
        case "D": { [["Dfb",2], ["Dfc",1]] };
        case "E": { [["Dfc",2], ["ET",1]] };
    }],

    // Rocky/mountain: elevation dominates
    ["#GdtRock", switch (true) do {
        case (_elevEffect > 15):  { [["ET",3], ["EF",1]] };   // High alpine
        case (_elevEffect > 8):   { [["Dfc",3], ["ET",2]] };  // Subalpine
        case (_latBand == "E"):   { [["ET",3], ["Dfc",2]] };  // Polar
        default                   { [["Dfb",2], ["Cfb",1]] }; // Mid-elevation
    }],
    ["#GdtMountain", switch (true) do {
        case (_elevEffect > 20):  { [["ET",3], ["EF",1]] };   // Above treeline
        case (_elevEffect > 10):  { [["Dfc",3], ["ET",2]] };  // Subalpine
        case (_latBand == "E"):   { [["ET",3], ["Dfc",2]] };  // Polar
        default                   { [["Dfb",2], ["Dfc",1]] }; // Mid-elevation
    }],

    // Agricultural: anthropogenic, use latitude for base climate
    ["#GdtField", switch (_latBand) do {
        case "A": { [["Aw",2], ["Am",1]] };
        case "B": { [["BSh",2], ["BSk",1]] };
        case "C": { [["Cfb",3], ["Cfa",2]] };
        case "D": { [["Dfb",3], ["Dfb",1]] };
        case "E": { [["Dfc",2], ["ET",1]] };
    }],
    ["#GdtCrop", switch (_latBand) do {
        case "A": { [["Aw",2], ["Am",1]] };
        case "B": { [["BSh",2], ["BSk",1]] };
        case "C": { [["Cfb",3], ["Cfa",2]] };
        case "D": { [["Dfb",3], ["Dfb",1]] };
        case "E": { [["Dfc",2], ["ET",1]] };
    }],
    ["#GdtOrchard", switch (_latBand) do {
        case "A": { [["Am",2], ["Af",1]] };
        case "B": { [["BSk",2], ["BSh",1]] };
        case "C": { [["Cfb",3], ["Cfa",2]] };
        case "D": { [["Dfb",2], ["Cfb",1]] };
        case "E": { [["Dfc",2], ["ET",1]] };
    }],

    // Snow: cold biomes
    ["#GdtSnow", switch (true) do {
        case (_latBand == "E"):   { [["ET",3], ["EF",2]] };
        case (_latBand == "D"):   { [["Dfc",3], ["ET",2]] };
        case (_elevEffect > 15):  { [["ET",3], ["Dfc",2]] };
        default                   { [["Dfc",2], ["ET",1]] };
    }]
];

// Look up candidates for this surface type
private _candidates = _CANDIDATE_MAP getOrDefault [_surface, []];

// If no candidates found, use latitude-based fallback
if (_candidates isEqualTo []) exitWith {
    switch (_latBand) do {
        case "A": { "Af" };
        case "B": { "BWh" };
        case "C": { "Cfb" };
        case "D": { "Dfb" };
        case "E": { "ET" };
        default   { "Cfb" };
    };
};

// ─── Pick winner from candidates ──────────────────────────────────────
// Simple weighted selection. First candidate with highest weight wins.
private _best = _candidates select 0;
{
    if ((_x select 1) > (_best select 1)) then {
        _best = _x;
    };
} forEach _candidates;

_best select 0
