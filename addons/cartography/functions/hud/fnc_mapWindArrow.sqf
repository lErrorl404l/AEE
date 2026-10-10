#include "..\..\script_component.hpp"
/*
 * aee_cartography_fnc_mapWindArrow
 *
 * Pure kernel.  Turns a local wind vector into the two endpoints of a map
 * arrow, centred on the sample point.
 *
 * The vector is the mod's own computed local wind
 * (EFUNC(atmos,getLocalWind), the issue #136 field), [easterly, northerly]
 * in m/s.  The kernel reads no world and no engine state: the vector and the
 * arrow length arrive as arguments.  The arrow points the way the wind BLOWS
 * TOWARD (the vector direction), so a westerly blows east.
 *
 * Arguments:
 *   0: _wind    <ARRAY>  [easterly, northerly] local wind in m/s
 *   1: _lengthM <NUMBER> the arrow length in world metres
 *
 * Return: <ARRAY> [[x0, y0], [x1, y1]] the arrow segment, centred on [0, 0],
 *   in world metres.  A calm (magnitude <= 0.01 m/s) returns a zero segment,
 *   so a caller never draws a directionless arrow.
 */
params [
    ["_wind", [0, 0], [[]]],
    ["_lengthM", 0, [0]]
];

private _e = _wind select 0;
private _n = _wind select 1;
private _mag = sqrt ((_e * _e) + (_n * _n));

private _seg = [[0, 0], [0, 0]];
if ((_mag > 0.01) && (_lengthM > 0)) then {
    private _ux = _e / _mag;
    private _uy = _n / _mag;
    private _half = _lengthM * 0.5;
    _seg = [
        [-(_ux * _half), -(_uy * _half)],
        [_ux * _half, _uy * _half]
    ];
};

_seg
