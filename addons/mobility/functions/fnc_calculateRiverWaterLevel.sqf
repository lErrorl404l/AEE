#include "..\script_component.hpp"

/*
Cumulative water level change from precipitation, modelled as a Nash
cascade of three serial linear reservoirs with biome-dependent inflow.

  • r1 accumulates rainfall, r2 and r3 pass it downstream
  • Outflow from r3 drives the water level (lagged, peaked response)
  • Tropical biomes amplify, arid biomes dampen
  • Flood risk thresholds for mission logic (river crossings, flooding)

Stored in GVAR(currentWaterLevel) — float 0+ (0 = dry baseline)
Stored in GVAR(riverReservoirs)   — [r1, r2, r3] cascade state
Stored in GVAR(currentFloodRisk)  — string "None"|"Elevated"|"Flood"|"Severe"
*/

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

// ─── Nash cascade — three serial linear reservoirs ─────────────────────────
private _k = missionNamespace getVariable [QGVAR(riverResponseRate), 0.1];   // storage coefficient; 1/k = reservoir time constant
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
_k = _k * (_interval / 5);
private _reservoirs = missionNamespace getVariable [QGVAR(riverReservoirs), [0, 0, 0]];
private _r1 = _reservoirs select 0;
private _r2 = _reservoirs select 1;
private _r3 = _reservoirs select 2;

private _inflow = rain * _biomeFactor;

_r1 = _r1 + _inflow - (_r1 * _k);
_r2 = _r2 + (_r1 * _k) - (_r2 * _k);
_r3 = _r3 + (_r2 * _k) - (_r3 * _k);
private _outflow = _r3 * _k;

missionNamespace setVariable [QGVAR(riverReservoirs), [_r1, _r2, _r3]];

// ─── Water level proportional to outflow ───────────────────────────────────
private _waterLevel = _outflow max 0;

private _floodRisk = switch (true) do {
    case (_waterLevel > 0.5): { "Severe" };
    case (_waterLevel > 0.3): { "Flood" };
    case (_waterLevel > 0.15): { "Elevated" };
    default                    { "None" };
};

missionNamespace setVariable [QGVAR(currentWaterLevel), _waterLevel];
missionNamespace setVariable [QEGVAR(core,currentFloodRisk), _floodRisk];
