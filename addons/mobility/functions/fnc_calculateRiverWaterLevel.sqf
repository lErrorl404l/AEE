#include "..\script_component.hpp"

/*
Cumulative water level change from precipitation, modelled as a leaky
integrator with biome-dependent sensitivity.

  • Decays 0.5 % / tick  (~23 min half-life at 5 s ticks)
  • Tropical biomes amplify, arid biomes dampen
  • Flood risk thresholds for mission logic (river crossings, flooding)

Stored in GVAR(currentWaterLevel) — float 0+ (0 = dry baseline)
Stored in GVAR(currentFloodRisk)  — string "None"|"Elevated"|"Flood"|"Severe"
*/

private _previous = missionNamespace getVariable [QGVAR(currentWaterLevel), 0];

private _biome = EGVAR(core,biome);
if (isNil "_biome" || _biome == "") then { _biome = "Cfb"; };

private _biomeFactor = switch (true) do {
    // Tropical — heavy rain multiplier
    case (_biome in ["Af","Am","Aw"]):                      { 1.5 };
    // Temperate / continental
    case (_biome in ["Cfa","Cfb","Cwa","Csa","Csb"]):      { 1.0 };
    case (_biome in ["Dfa","Dfb","Dfc"]):                   { 1.0 };
    // Arid — minimal runoff
    case (_biome in ["BWh","BWk","BSh","BSk"]):             { 0.3 };
    default                                                 { 1.0 };
};

private _waterLevel = (_previous * 0.995) + (rain * 0.005 * _biomeFactor);
_waterLevel = _waterLevel max 0;

private _floodRisk = switch (true) do {
    case (_waterLevel > 0.5): { "Severe" };
    case (_waterLevel > 0.3): { "Flood" };
    case (_waterLevel > 0.15): { "Elevated" };
    default                    { "None" };
};

missionNamespace setVariable [QGVAR(currentWaterLevel), _waterLevel];
missionNamespace setVariable [QEGVAR(core,currentFloodRisk), _floodRisk];
