#include "..\script_component.hpp"
/*
 * aee_lib_fnc_pandolfTerrainFactor
 *
 * Terrain factor eta of the Pandolf load-carriage equation.  Pure.
 *
 * Soule & Goldman 1972 (J Appl Physiol 32:706): blacktop 1.0, dirt road
 * 1.1, light brush 1.2, heavy brush 1.5, swampy bog 1.8, loose sand 2.1.
 * Snow: Pandolf, Haisman & Goldman 1976 (Ergonomics 19:683),
 * eta = 1.30 + 0.082 D, D the footprint depth in cm (here the snow depth,
 * the depth a boot sinks into fresh snow).
 *
 * Arguments:
 *   0: surface class name (STRING, surfaceType)
 *   1: snow depth, m
 * Return: eta
 */
params [["_surface", "", [""]], ["_snowM", 0, [0]]];
if (_snowM > 0.01) exitWith { 1.30 + (0.082 * (_snowM * 100)) };
private _name = toLowerANSI _surface;
private _eta = 1.2;
{
    private _key = _x select 0;
    if ((_name find _key) >= 0) exitWith { _eta = _x select 1; };
} forEach [
    ["marsh", 1.8], ["swamp", 1.8], ["bog", 1.8], ["mud", 1.8],
    ["sand", 2.1], ["beach", 2.1], ["desert", 2.1], ["dune", 2.1],
    ["snow", 1.3], ["ice", 1.0],
    ["forest", 1.5], ["thicket", 1.5], ["undergrowth", 1.5], ["bush", 1.5],
    ["grass", 1.2], ["field", 1.2], ["weed", 1.2], ["meadow", 1.2], ["crop", 1.2],
    ["gravel", 1.1], ["dirt", 1.1], ["soil", 1.1], ["track", 1.1], ["trail", 1.1], ["rock", 1.1], ["stony", 1.1],
    ["asphalt", 1.0], ["tarmac", 1.0], ["concrete", 1.0], ["road", 1.0], ["runway", 1.0], ["cobble", 1.0], ["pavement", 1.0]
];
_eta
