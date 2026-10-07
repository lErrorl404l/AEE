#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_mgrsGridLines
 *
 * Compute the MGRS grid overlay for a visible world rectangle.  PURE: the
 * anchor and the rectangle arrive as arguments, so the kernel reads no map
 * control, no cursor and no engine grid.  It reuses the core conversion
 * kernels: FUNC(worldToMgrs) gives the visible easting and northing range,
 * FUNC(utmToWorld) gives the line geometry and FUNC(formatMgrs) gives the
 * labels.
 *
 * The engine map grid stays numeric.  The CfgWorlds Grid class formats
 * numbers only and no script command writes it, so this overlay draws the
 * MGRS lines over it instead of relabelling them in place.
 *
 * The interval is a decimal MGRS step chosen so the line count stays small:
 * 10 m, 100 m, 1 km, 10 km or 100 km.  The label carries the digit group
 * that matches the interval, so a 1 km line is labelled with its two-digit
 * easting or northing.
 *
 * Arguments:
 *   0: _anchor <ARRAY> the 9-element anchor from EFUNC(core,getGeoAnchor)
 *   1: _rect   <ARRAY> [xMin, yMin, xMax, yMax] world metres
 *
 * Return: [_segments, _labels, _interval]
 *   _segments <ARRAY> each [pointA, pointB, major], world [x, y, 0]
 *   _labels   <ARRAY> each [position, text, major], world [x, y, 0]
 *   _interval <NUMBER> the grid step in metres, 0 when nothing is drawn
 */
params [
    ["_anchor", [], [[]]],
    ["_rect", [0, 0, 0, 0], [[]]]
];

if ((count _anchor) < 9) exitWith { [[], [], 0] };
if ((count _rect) < 4) exitWith { [[], [], 0] };

private _xMin = _rect select 0;
private _yMin = _rect select 1;
private _xMax = _rect select 2;
private _yMax = _rect select 3;
if ((_xMax <= _xMin) || (_yMax <= _yMin)) exitWith { [[], [], 0] };

// The world sits in one UTM zone.  Take the zone from the anchor centre
// longitude and the hemisphere from the anchor centre latitude, so every
// line is projected the same way.
private _latCentre = _anchor select 0;
private _lonCentre = _anchor select 1;
private _zone = (floor ((_lonCentre + 180) / 6)) + 1;
if (_zone < 1) then { _zone = 1; };
if (_zone > 60) then { _zone = 60; };
private _hemisphere = "north";
if (_latCentre < 0) then { _hemisphere = "south"; };

// The visible easting and northing bounds come from the four corners.
private _corners = [[_xMin, _yMin], [_xMax, _yMin], [_xMin, _yMax], [_xMax, _yMax]];
private _eMin = 99999999;
private _eMax = -99999999;
private _nMin = 99999999;
private _nMax = -99999999;
private _conv = [];
private _e = 0;
private _n = 0;
{
    _conv = [_x + [0], _anchor, 10] call EFUNC(core,worldToMgrs);
    if ((count _conv) >= 5) then {
        _e = _conv select 3;
        _n = _conv select 4;
        if (_e < _eMin) then { _eMin = _e; };
        if (_e > _eMax) then { _eMax = _e; };
        if (_n < _nMin) then { _nMin = _n; };
        if (_n > _nMax) then { _nMax = _n; };
    };
} forEach _corners;

if ((_eMax <= _eMin) || (_nMax <= _nMin)) exitWith { [[], [], 0] };

// Interval: the smallest decimal step that keeps the line count at or below
// 12 per axis.  The count falls by a factor of ten at each step.
private _span = (_eMax - _eMin) max (_nMax - _nMin);
private _interval = 100000;
private _found = false;
{
    if (!_found && ((_span / _x) <= 12)) then {
        _interval = _x;
        _found = true;
    };
} forEach [10, 100, 1000, 10000, 100000];

// Digits per axis for the label: interval = 10 ^ (5 - perAxis).
private _perAxis = round (5 - (log _interval));
private _precision = _perAxis * 2;

private _segments = [];
private _labels = [];
private _samples = 3;
private _pts = [];
private _major = false;
private _full = "";
private _sample = 0;

// Vertical lines: constant easting.
private _line = (ceil (_eMin / _interval)) * _interval;
private _end = (floor (_eMax / _interval)) * _interval;
while { _line <= _end } do {
    _pts = [];
    for "_k" from 0 to (_samples - 1) do {
        _sample = _nMin + (((_nMax - _nMin) * _k) / (_samples - 1));
        _pts pushBack ([_line, _sample, _zone, _hemisphere, _anchor] call EFUNC(core,utmToWorld));
    };
    _major = (((_line / _interval) mod 10) == 0);
    for "_m" from 0 to (_samples - 2) do {
        _segments pushBack [_pts select _m, _pts select (_m + 1), _major];
    };
    if ((_perAxis >= 1) && (_perAxis <= 5)) then {
        _full = [_line, _nMax, _zone, _precision, _latCentre] call EFUNC(core,formatMgrs);
        if ((count _full) >= (5 + _precision)) then {
            _labels pushBack [_pts select (_samples - 1), _full select [5, _perAxis], _major];
        };
    };
    _line = _line + _interval;
};

// Horizontal lines: constant northing.
_line = (ceil (_nMin / _interval)) * _interval;
_end = (floor (_nMax / _interval)) * _interval;
while { _line <= _end } do {
    _pts = [];
    for "_k" from 0 to (_samples - 1) do {
        _sample = _eMin + (((_eMax - _eMin) * _k) / (_samples - 1));
        _pts pushBack ([_sample, _line, _zone, _hemisphere, _anchor] call EFUNC(core,utmToWorld));
    };
    _major = (((_line / _interval) mod 10) == 0);
    for "_m" from 0 to (_samples - 2) do {
        _segments pushBack [_pts select _m, _pts select (_m + 1), _major];
    };
    if ((_perAxis >= 1) && (_perAxis <= 5)) then {
        _full = [_eMax, _line, _zone, _precision, _latCentre] call EFUNC(core,formatMgrs);
        if ((count _full) >= (5 + _precision)) then {
            _labels pushBack [_pts select (_samples - 1), _full select [(5 + _perAxis), _perAxis], _major];
        };
    };
    _line = _line + _interval;
};

[_segments, _labels, _interval]
