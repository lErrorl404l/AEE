#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapDeclinationRose
 *
 * Pure kernel.  Turns a magnetic declination into the true-north and
 * magnetic-north rays of a map rose, so the map shows both the grid north
 * (up) and the compass north the deviation model computes.
 *
 * The declination is the mod's own computed value
 * (EGVAR(core,magneticDeclinationDeg), produced by
 * FUNC(magnetism,calculateCompassDeviation)): degrees east, positive east,
 * clamped +-30.  The kernel reads no world and no engine state.
 *
 * World axes: +x is east, +y is north, and the map is north up, so true
 * north is the +y ray.  A declination of D degrees east puts magnetic north
 * D degrees clockwise of true north, i.e. the ray (sin D, cos D).
 *
 * Arguments:
 *   0: _declinationDeg <NUMBER> declination in degrees, positive east
 *   1: _radiusM        <NUMBER> the ray length in world metres
 *
 * Return: <ARRAY> [[trueNorthEnd, magneticNorthEnd]]
 *   trueNorthEnd     <ARRAY> [x, y] the true-north ray endpoint from [0, 0]
 *   magneticNorthEnd <ARRAY> [x, y] the magnetic-north ray endpoint
 *   A non-positive radius returns two zero endpoints, so a caller never
 *   draws a zero-length ray.
 */
params [
    ["_declinationDeg", 0, [0]],
    ["_radiusM", 0, [0]]
];

private _trueN = [0, 0];
private _magN = [0, 0];
if (_radiusM > 0) then {
    // SQF sin/cos take DEGREES, so the declination feeds them directly.
    _trueN = [0, _radiusM];
    _magN = [(sin _declinationDeg) * _radiusM, (cos _declinationDeg) * _radiusM];
};

[_trueN, _magN]
