#include "..\..\script_component.hpp"

/*
Local microclimate (issue: the microclimateRadius setting).

The weather model gives one temperature for a wide area. Ground truth is
not uniform: cold air drains into a hollow and pools there, a forest
canopy shades the ground and holds cooler air beneath it, and a slope
drains clear. This samples the terrain within a radius and applies those
two mechanisms.

MECHANISM 1 - COLD-AIR POOLING (relief).
Dense cold air flows downhill and collects in the lowest ground, so a
hollow is cooler than a crest at the same regional temperature. The
temperature deficit follows the relief the model already measures, which
is the same quantity the wind speed-up uses (Taylor and Lee 1984,
Climatological Bulletin 18(2) 3-32). The deficit is bounded by the
observed strength of valley inversions rather than an unbounded fall with
depth.

MECHANISM 2 - CANOPY COOLING (surface cover).
A canopy intercepts solar radiation and transpires, so the air beneath it
is cooler than open ground by day; at night the canopy reduces radiative
loss and the sign reverses. The strength follows the foliage state the
terrain scan publishes (fnc_updateSeasonalFoliage).

The radius the user sets is the window this samples over: it decides how
far the model looks for a hollow or a canopy, not the physics itself.

Args:
  0: position (ARRAY, PositionASL, default [])
  1: radius (NUMBER, metres, the user setting, default 200)

Returns the temperature offset in degrees Celsius (negative for cooling).
*/

params [["_pos", [], [[]]], ["_radius", 200, [0]]];

if (count _pos < 2) exitWith { 0 };
if (_radius <= 0) exitWith { 0 };

// ─── Sample the relief within the radius ─────────────────────────────────
// Four cardinal samples at the radius, plus the centre.  A hollow has the
// centre below every neighbour; a crest has it above.
private _centre = getTerrainHeightASL (_pos select [0, 2]);
private _x = _pos select 0;
private _y = _pos select 1;
private _neighbours = [
    getTerrainHeightASL [_x + _radius, _y],
    getTerrainHeightASL [_x - _radius, _y],
    getTerrainHeightASL [_x, _y + _radius],
    getTerrainHeightASL [_x, _y - _radius]
];
private _meanNeighbour = 0;
{ _meanNeighbour = _meanNeighbour + _x; } forEach _neighbours;
_meanNeighbour = _meanNeighbour / 4;

// Positive in a hollow (centre below its surroundings).
private _relief = _meanNeighbour - _centre;

// ─── Mechanism 1: pooling ────────────────────────────────────────────────
// A strong inversion in a deep hollow reaches a few degrees; the relation
// is not linear without bound, so the deficit saturates.  The scale
// follows the relief over the sample radius: a shallow dip pools weakly,
// a deep basin strongly.
private _pooling = 0;
if (_relief > 0) then {
    // A 50 m fall within the radius carries the full inversion.
    private _depth = (_relief / 50) min 1;
    // The maximum observed valley-inversion deficit this applies at full
    // depth, before the user scale.
    private _maxDeficit = 3.0;
    _pooling = -_maxDeficit * _depth;
};

// ─── Mechanism 2: canopy cooling ─────────────────────────────────────────
// The foliage density the biome model publishes (0 open, 1 full canopy).
// By day a canopy cools the air beneath it; the sign follows the solar
// input, so a shaded forest is cooler than open ground when the sun is up
// and slightly warmer when it is not (reduced radiative loss).
private _foliage = missionNamespace getVariable [QEGVAR(environmental,currentFoliageDensity), 0];
if !(_foliage isEqualType 0) then { _foliage = 0; };
_foliage = _foliage max 0 min 1;
private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_solar isEqualType 0) then { _solar = 0; };

private _canopy = 0;
if (_foliage > 0.1) then {
    // Day: shade cools. Night: the canopy insulates the surface and the
    // air beneath stays a little warmer than open sky-facing ground.
    private _dayCooling = -2.5 * _foliage * (_solar max 0 min 1);
    private _nightWarming = 0.8 * _foliage * (1 - (_solar max 0 min 1));
    _canopy = _dayCooling + _nightWarming;
};

// ─── Wind mixes the pooling away ─────────────────────────────────────────
// A strong wind ventilates a hollow and destroys the inversion, so the
// pooling term fades as the wind rises.  The canopy term is sheltered by
// the canopy itself and is unaffected.
private _windStr = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
if !(_windStr isEqualType 0) then { _windStr = 0; };
if (_windStr > 2) then {
    _pooling = _pooling * (1 - (((_windStr - 2) / 6) min 1));
};

_pooling + _canopy
