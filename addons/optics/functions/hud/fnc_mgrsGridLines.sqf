#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_mgrsGridLines
 *
 * Compute the cardinal grid overlay for a visible world rectangle.  PURE: the
 * anchor and the rectangle arrive as arguments, so the kernel reads no map
 * control, no cursor and no engine grid.
 *
 * CARDINAL GRID.  Each line follows a map axis: a vertical line sits at one
 * constant world x and a horizontal line at one constant world y.  The map
 * control maps world to screen with a LINEAR transform, so a line along a
 * world axis is a straight screen line by construction, with no per-point
 * conversion and no chord to fit.  This is a DELIBERATE design change from a
 * true MGRS grid, which is aligned to UTM grid north and so tilted from the
 * map axes by the grid convergence (+0.85 degrees on Stratis).  ADR-030
 * records the reason: the map is north up, the compass and a real paper map
 * read cardinal, and the base engine's own grid is cardinal.
 *
 * The engine map grid stays numeric.  The CfgWorlds Grid class formats
 * numbers only and no script command writes it, so this overlay draws its own
 * lines over it.
 *
 * LABELS.  A cardinal line has NO single MGRS value, because the MGRS easting
 * and northing vary along it.  The label is therefore POSITIONAL by design:
 * FUNC(worldToMgrs) gives the MGRS reference at a fixed point of the line, and
 * the label carries the digit group that matches the interval.  A 1 km line is
 * labelled with its three-digit easting or northing at that point.
 *
 * Every line is labelled at BOTH ends, so the easting reads at the top and the
 * bottom and the northing at the left and the right.  The engine's own edge
 * ruler (CStaticMap::DrawGrid) places each number half a grid spacing from its
 * line and clips it to the control rect, and the northing spacing is
 * wScreen/hScreen times the easting spacing, so at close zoom the engine's
 * left and right numbers leave the control while its top and bottom numbers
 * stay.  AEE cannot change DrawGrid, so it supplies the complete four-edge
 * ruler itself.
 *
 * The interval is a decimal world-metre step chosen so the line count stays
 * small: 10 m, 100 m, 1 km, 10 km or 100 km.
 *
 * Arguments:
 *   0: _anchor       <ARRAY>  the 9-element anchor from EFUNC(lib,getGeoAnchor)
 *   1: _rect         <ARRAY>  [xMin, yMin, xMax, yMax] world metres
 *   2: _baseInterval <NUMBER> the finest step in metres, 0 for the default
 *
 * Return: [_segments, _labels, _interval]
 *   _segments <ARRAY> each [pointA, pointB, major], world [x, y, 0]
 *   _labels   <ARRAY> each [position, text, major], world [x, y, 0]
 *   _interval <NUMBER> the grid step in metres, 0 when nothing is drawn
 */
params [
    ["_anchor", [], [[]]],
    ["_rect", [0, 0, 0, 0], [[]]],
    ["_baseInterval", 0, [0]]
];

if ((count _anchor) < 9) exitWith { [[], [], 0] };
if ((count _rect) < 4) exitWith { [[], [], 0] };

private _xMin = _rect select 0;
private _yMin = _rect select 1;
private _xMax = _rect select 2;
private _yMax = _rect select 3;
if ((_xMax <= _xMin) || (_yMax <= _yMin)) exitWith { [[], [], 0] };

// Interval: the smallest decimal step at or above the floor (arg 2) that
// keeps the line count at or below 24 per axis.  The visible span sets the
// step.  The count falls by ten each step.  The step is in world metres, the
// same unit as the line positions, so a line lands on a whole step.
private _span = (_xMax - _xMin) max (_yMax - _yMin);

private _floor = 10;
if ((_baseInterval isEqualType 0) && (_baseInterval >= 10) && (_baseInterval <= 100000)) then {
    _floor = _baseInterval;
};
private _interval = 100000;
private _found = false;
{
    if (!_found && (_x >= _floor) && ((_span / _x) <= 24)) then {
        _interval = _x;
        _found = true;
    };
} forEach [10, 100, 1000, 10000, 100000];

// Digits per axis for the label: interval = 10 ^ (5 - perAxis).
private _perAxis = round (5 - (log _interval));
private _precision = _perAxis * 2;

private _segments = [];
private _labels = [];
private _major = false;
private _full = "";
private _conv = [];

// Vertical lines: constant world x.  The segment runs the full visible y
// range, so it is vertical by construction.  The label sits at the north end
// and carries the MGRS easting at that point.
private _line = (ceil (_xMin / _interval)) * _interval;
private _end = (floor (_xMax / _interval)) * _interval;
while { _line <= _end } do {
    _major = (((_line / _interval) mod 10) == 0);
    _segments pushBack [[_line, _yMin, 0], [_line, _yMax, 0], _major];
    if ((_perAxis >= 1) && (_perAxis <= 5)) then {
        _conv = [[_line, _yMax, 0], _anchor, _precision] call EFUNC(lib,worldToMgrs);
        _full = _conv select 0;
        if ((count _full) >= (5 + _precision)) then {
            private _easting = _full select [5, _perAxis];
            _labels pushBack [[_line, _yMax, 0], _easting, _major];
            _labels pushBack [[_line, _yMin, 0], _easting, _major];
        };
    };
    _line = _line + _interval;
};

// Horizontal lines: constant world y.  The label sits at the east end and
// carries the MGRS northing at that point.
_line = (ceil (_yMin / _interval)) * _interval;
_end = (floor (_yMax / _interval)) * _interval;
while { _line <= _end } do {
    _major = (((_line / _interval) mod 10) == 0);
    _segments pushBack [[_xMin, _line, 0], [_xMax, _line, 0], _major];
    if ((_perAxis >= 1) && (_perAxis <= 5)) then {
        _conv = [[_xMax, _line, 0], _anchor, _precision] call EFUNC(lib,worldToMgrs);
        _full = _conv select 0;
        if ((count _full) >= (5 + _precision)) then {
            private _northing = _full select [(5 + _perAxis), _perAxis];
            _labels pushBack [[_xMax, _line, 0], _northing, _major];
            _labels pushBack [[_xMin, _line, 0], _northing, _major];
        };
    };
    _line = _line + _interval;
};

[_segments, _labels, _interval]
