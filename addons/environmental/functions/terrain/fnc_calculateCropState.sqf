#include "..\..\script_component.hpp"

/*
Agricultural crop height / density (0–1) for concealment modifiers,
separate from natural foliage (GVAR(currentFoliageDensity)).

Driven by Köppen biome and calendar month:
  • Tropical — always dense year-round
  • Temperate — planted spring, peak summer, harvested autumn
  • Continental — shorter growing season
  • Mediterranean — winter-growing cycle
  • Arid / other — negligible

Stored in GVAR(currentCropDensity) — float 0–1
*/

private _biome = EGVAR(core,biome);
if (isNil "_biome" || _biome == "") then { _biome = "Cfb"; };

private _monthIdx = ((date select 1) - 1) max 0 min 11;

private _cropDensity = switch (_biome) do {
    // Tropical — always dense
    case "Af": { [0.8,0.8,0.8,0.8,0.8,0.8,0.9,0.9,0.9,0.9,0.8,0.8] select _monthIdx };
    case "Am": { [0.8,0.8,0.8,0.8,0.8,0.8,0.9,0.9,0.9,0.9,0.8,0.8] select _monthIdx };
    case "Aw": { [0.8,0.8,0.8,0.8,0.8,0.8,0.9,0.9,0.9,0.9,0.8,0.8] select _monthIdx };
    // Temperate — spring planting, summer peak
    case "Cfa": { [0.1,0.1,0.2,0.4,0.7,1.0,1.0,0.9,0.7,0.3,0.1,0.1] select _monthIdx };
    case "Cfb": { [0.1,0.1,0.2,0.4,0.7,1.0,1.0,0.9,0.7,0.3,0.1,0.1] select _monthIdx };
    case "Cwa": { [0.1,0.1,0.2,0.4,0.7,1.0,1.0,0.9,0.7,0.3,0.1,0.1] select _monthIdx };
    // Continental — shorter season
    case "Dfa": { [0.0,0.0,0.0,0.2,0.5,0.8,1.0,0.9,0.6,0.2,0.0,0.0] select _monthIdx };
    case "Dfb": { [0.0,0.0,0.0,0.2,0.5,0.8,1.0,0.9,0.6,0.2,0.0,0.0] select _monthIdx };
    case "Dfc": { [0.0,0.0,0.0,0.2,0.5,0.8,1.0,0.9,0.6,0.2,0.0,0.0] select _monthIdx };
    // Mediterranean — winter growing
    case "Csa": { [0.6,0.7,0.8,0.6,0.3,0.1,0.1,0.1,0.2,0.4,0.6,0.6] select _monthIdx };
    case "Csb": { [0.6,0.7,0.8,0.6,0.3,0.1,0.1,0.1,0.2,0.4,0.6,0.6] select _monthIdx };
    // Arid — negligible
    case "BWh": { 0.05 };
    case "BWk": { 0.05 };
    case "BSh": { 0.1 };
    case "BSk": { 0.1 };
    // Polar / tundra
    case "ET":  { 0.0 };
    case "EF":  { 0.0 };
    default     { 0.3 };
};

missionNamespace setVariable [QEGVAR(core,currentCropDensity), _cropDensity];
