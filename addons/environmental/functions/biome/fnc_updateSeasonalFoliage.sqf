#include "..\..\script_component.hpp"

/*
Vegetation / foliage density (0–1) driven by Köppen biome and calendar month.

  1.0 = full canopy (tropical rainforest, temperate summer)
  0.0 = bare (desert, tundra, temperate winter)

Stored in GVAR(currentFoliageDensity) for use by concealment
modifiers, sound-propagation, and visual-seasonal systems.
*/

private _biome = missionNamespace getVariable [QEGVAR(core,biome), "Cfb"];
if (isNil "_biome" || _biome == "") then { _biome = "Cfb"; };

private _monthIdx = ((date select 1) - 1) max 0 min 11; // 0‑based

private _foliage = switch (_biome) do {
    // Tropical — evergreen year-round
    case "Af": { 1.0 };
    case "Am": { 1.0 };
    // Savanna — wet/dry season
    case "Aw": { [0.6,0.6,0.6,0.7,0.8,0.9,1.0,1.0,0.9,0.8,0.7,0.6] select _monthIdx };
    // Arid — always sparse
    case "BWh": { 0.05 };
    case "BWk": { 0.05 };
    case "BSh": { [0.1,0.1,0.15,0.15,0.2,0.2,0.2,0.2,0.15,0.15,0.1,0.1] select _monthIdx };
    case "BSk": { [0.1,0.1,0.15,0.15,0.2,0.2,0.2,0.2,0.15,0.15,0.1,0.1] select _monthIdx };
    // Mediterranean — dry summer, green winter
    case "Csa": { [0.4,0.4,0.5,0.6,0.7,0.8,0.8,0.8,0.7,0.6,0.5,0.4] select _monthIdx };
    case "Csb": { [0.4,0.4,0.5,0.6,0.7,0.8,0.8,0.8,0.7,0.6,0.5,0.4] select _monthIdx };
    // Subtropical — deciduous cycle
    case "Cfa": { [0.2,0.2,0.3,0.5,0.8,1.0,1.0,1.0,0.9,0.6,0.4,0.2] select _monthIdx };
    case "Cfb": { [0.2,0.2,0.3,0.5,0.8,1.0,1.0,1.0,0.9,0.6,0.4,0.2] select _monthIdx };
    case "Cwa": { [0.3,0.3,0.4,0.6,0.8,1.0,1.0,1.0,0.9,0.7,0.5,0.4] select _monthIdx };
    // Continental — strong four-season
    case "Dfa": { [0.0,0.0,0.0,0.2,0.7,1.0,1.0,1.0,0.8,0.4,0.1,0.0] select _monthIdx };
    case "Dfb": { [0.0,0.0,0.0,0.2,0.7,1.0,1.0,1.0,0.8,0.4,0.1,0.0] select _monthIdx };
    case "Dfc": { [0.0,0.0,0.0,0.1,0.5,0.9,1.0,0.9,0.6,0.2,0.0,0.0] select _monthIdx };
    // Polar / alpine
    case "ET":  { 0.0 };
    case "EF":  { 0.0 };
    default     { 0.8 };
};

missionNamespace setVariable [QGVAR(currentFoliageDensity), _foliage];
