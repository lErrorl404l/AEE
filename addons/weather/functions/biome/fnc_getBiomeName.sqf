#include "..\..\script_component.hpp"

// ─── Biome code → human name ─────────────────────────────────────────
// Returns the human-readable name for a Koppen code.
// Used by updateBiomePosition and diagnostic display.
//
// Arguments: [_code]
//   0: Koppen code string (e.g. "Cfb")
// Return: Human-readable name string

params ["_code"];

private _NAMES = createHashMapFromArray [
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

_NAMES getOrDefault [_code, _code]
