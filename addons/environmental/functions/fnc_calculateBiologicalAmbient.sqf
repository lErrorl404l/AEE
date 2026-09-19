#include "..\script_component.hpp"

/*
Ambient biological sound intensity (0.0–1.0) for environmental audio.

Models insect, bird, and cricket sound levels based on Köppen biome,
air temperature, diurnal cycle (sunOrMoon), and northern-hemisphere
season (month).

Stored in GVAR(biologicalAmbientIntensity).
*/

params [];

private _temp  = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
private _month  = date select 1;

if (isNil "_temp") exitWith { 0 };

// ─── Biome baseline ────────────────────────────────────────────────────
private _baseline = switch (_biome) do {
    // Tropical — always loud
    case "Af": { 0.8 };
    case "Am": { 0.8 };
    case "Aw": { 0.8 };
    // Arid — sparse insect/bird life
    case "BWh": { 0.1 };
    case "BWk": { 0.1 };
    case "BSh": { 0.1 };
    case "BSk": { 0.1 };
    // Mediterranean
    case "Csa": { 0.5 };
    case "Csb": { 0.5 };
    // Humid subtropical
    case "Cfa": { 0.6 };
    case "Cwa": { 0.6 };
    case "Cwb": { 0.6 };
    // Oceanic
    case "Cfb": { 0.4 };
    // Continental
    case "Dfa": { 0.3 };
    case "Dfb": { 0.3 };
    case "Dfc": { 0.3 };
    // Polar / tundra
    case "ET":  { 0.0 };
    case "EF":  { 0.0 };
    default     { 0.3 };
};

// ─── Temperature factor — cold reduces, extreme heat reduces ───────────
private _tempFactor = if (_temp < 10) then {
    (_temp / 10) max 0
} else {
    [1, 0.5] select (_temp > 35)
};

// ─── Night factor — crickets still chirp, birds sleep ─────────────────
private _nightFactor = [1, 0.6] select (sunOrMoon == -1);

// ─── Season factor (northern-hemisphere) ──────────────────────────────
private _seasonFactor = switch (true) do {
    case (_month <= 2): { 0.3 };   // winter
    case (_month <= 5): { 0.7 };   // spring
    case (_month <= 8): { 1.0 };   // summer
    default             { 0.5 };   // autumn
};

private _intensity = _baseline * _tempFactor * _nightFactor * _seasonFactor;
_intensity = _intensity max 0 min 1;

missionNamespace setVariable [QGVAR(biologicalAmbientIntensity), _intensity];

_intensity
