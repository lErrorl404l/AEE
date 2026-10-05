#include "..\..\script_component.hpp"

/*
Classify a world into a lighting class from FACTS.  No map name is consulted.

The biome-group mapping is SOURCED: it follows the Koppen scheme that
fnc_classifyBiome implements (Peel et al. 2007).  The thresholds in this
kernel are UNSOURCED aesthetic proxies chosen for the eye, not published
constants.

Arguments:
  0: latitude    signed degrees, positive north (number)
  1: biomeGroup  0 tropical, 1 arid, 2 temperate, 3 continental, 4 polar,
                 5 unknown (number)
  2: waterFrac   fraction of the terrain sample that is water, 0..1 (number)
  3: meanElev    mean terrain elevation, metres (number)
  4: dry         1 for a dry-summer or desert climate (Cs*, BW*, BS*), else 0

Return: class string.
*/

params [
    ["_latitude", 40, [0]],
    ["_biomeGroup", 2, [0]],
    ["_waterFrac", 0, [0]],
    ["_meanElev", 0, [0]],
    ["_dry", 0, [0]]
];

if (_biomeGroup == 5) exitWith { "TEMPERATE" };

// Lapse rate 6.5 C/km: high terrain is colder than its latitude suggests.
if (_meanElev > 1500) exitWith { "MONTANE" };

if (_biomeGroup == 4) exitWith { "POLAR" };
if (_biomeGroup == 1) exitWith { "ARID" };
if (_biomeGroup == 3) exitWith { "SUBARCTIC" };

// A water-dominated world moderates its climate.  This outranks the
// temperate and tropical classes, but not the montane override above.
if (_waterFrac > 0.5) exitWith { "MARITIME" };

if (_biomeGroup == 0) exitWith {
    ["TROPICAL", "TROPICAL_HUMID"] select (_waterFrac > 0.15)
};

if (_dry > 0.5) exitWith { "MEDITERRANEAN" };
if ((abs _latitude) >= 45) exitWith { "TEMPERATE_COOL" };

"TEMPERATE"
