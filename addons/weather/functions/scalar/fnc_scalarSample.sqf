#include "..\..\script_component.hpp"

/*
Sample a scalar field at a world position (issue #116).

The public read API: any consumer (particle emission, optics attenuation, AI
scent/detection, an external module) asks the engine for the field value at a
point instead of modelling the transport itself.  The sample is bilinear over
the same grid FUNC(updateScalarFields) publishes, so it matches the advected
field exactly at cell centres and interpolates between them.

Arguments:
  0: key      (STRING) field name ("smoke", "dust", ...)
  1: position (ARRAY)  world position, [x, y] or [x, y, z]; x and y are used

Return:
  NUMBER - the field concentration at the position, 0 when the field or the
  position is unknown.
*/

params [
    ["_key", "", [""]],
    ["_position", [0, 0], [[]]]
];

if (_key isEqualTo "") exitWith { 0 };
if (count _position < 2) exitWith { 0 };

private _grid = (missionNamespace getVariable [QGVAR(scalarFields), createHashMap]) getOrDefault [_key, []];
if ((count _grid) < 2) exitWith { 0 };

private _meta = (missionNamespace getVariable [QGVAR(scalarGridMeta), createHashMap]) getOrDefault [_key, []];
if ((count _meta) != 5) exitWith { 0 };
_meta params ["_w", "_h", "_originX", "_originY", "_cellM"];

// World position to fractional grid coordinates.
private _fx = ((_position select 0) - _originX) / _cellM;
private _fy = ((_position select 1) - _originY) / _cellM;

// Outside the grid: no field there.
if ((_fx < 0) || (_fy < 0) || (_fx > (_w - 1)) || (_fy > (_h - 1))) exitWith { 0 };

private _x0 = floor _fx;
private _y0 = floor _fy;
private _x1 = (_x0 + 1) min (_w - 1);
private _y1 = (_y0 + 1) min (_h - 1);
private _tx = _fx - _x0;
private _ty = _fy - _y0;

private _c00 = _grid select (_x0 + _y0 * _w);
private _c10 = _grid select (_x1 + _y0 * _w);
private _c01 = _grid select (_x0 + _y1 * _w);
private _c11 = _grid select (_x1 + _y1 * _w);

private _top = _c00 + (_c10 - _c00) * _tx;
private _bot = _c01 + (_c11 - _c01) * _tx;
_top + (_bot - _top) * _ty
