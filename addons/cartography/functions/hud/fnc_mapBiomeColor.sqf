#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapBiomeColor
 *
 * Pure kernel.  Maps a Koppen climate code to the RGBA tint the map biome
 * overlay draws for that climate group, plus its short group label.
 *
 * The CODE is the mod's own computed biome (EGVAR(core,biome), produced by
 * EFUNC(weather,getBiomeAtPosition) / FUNC(weather,getBiomeName)); this kernel
 * reads no world, no marker and no config.  The colour is a PRESENTATION
 * choice, keyed to the Koppen primary group letter (A tropical, B arid,
 * C temperate, D continental, E polar) - the letter scheme of Peel 2007
 * (doi:10.5194/hess-11-1633-2007), the same source the biome kernel cites.
 * The exact RGBA values are AEE's own and are UNSOURCED.
 *
 * Arguments:
 *   0: _code <STRING> a Koppen code, for example "Cfb"
 *
 * Return: <ARRAY> [[r, g, b, a], groupLabel <STRING>]
 *   The tint is a translucent wash (alpha 0.35) so the terrain shows through.
 *   An unknown or empty code returns the neutral grey group.
 */
params [
    ["_code", "", [""]]
];

// The primary group letter is the first character of the code.
private _group = "";
if ((count _code) > 0) then {
    _group = toUpper (_code select [0, 1]);
};

private _tint = [0.50, 0.50, 0.50, 0.35];
private _label = "Unknown";
if (_group isEqualTo "A") then {
    _tint = [0.10, 0.55, 0.15, 0.35];
    _label = "Tropical";
};
if (_group isEqualTo "B") then {
    _tint = [0.85, 0.75, 0.40, 0.35];
    _label = "Arid";
};
if (_group isEqualTo "C") then {
    _tint = [0.45, 0.75, 0.35, 0.35];
    _label = "Temperate";
};
if (_group isEqualTo "D") then {
    _tint = [0.35, 0.60, 0.65, 0.35];
    _label = "Continental";
};
if (_group isEqualTo "E") then {
    _tint = [0.85, 0.90, 0.95, 0.35];
    _label = "Polar";
};

[_tint, _label]
