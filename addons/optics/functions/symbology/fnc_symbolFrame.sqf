#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbolFrame
 *
 * Pure symbol frame kernel.  Maps an affiliation and a dimension to the frame
 * outline, as a list of polylines in the unit box [-1, 1].  PURE: both inputs
 * arrive as arguments, so the kernel reads no setting, no world and no engine
 * entity.
 *
 * Base shape, NATO APP-6(C) frame grammar:
 *   friend  rectangle, hostile diamond, neutral square, unknown quatrefoil
 * Dimension modifier, APP-6(C):
 *   land and sea closed frame, air a domed top edge, subsurface a curved
 *   bottom edge, space a filled apex, installation a filled top bar,
 *   equipment a circle
 * The arc samples use a parabola, a derived approximation of the standard's
 * curve.  The sea-surface hull arc of MIL-STD-2525 is a named per-2525
 * variant, UNSOURCED against APP-6(C), and is not drawn here.
 *
 * Arguments:
 *   0: _affiliation <STRING> "friend", "hostile", "neutral" or "unknown"
 *   1: _dimension   <STRING> a dimension token, for example "land" or "air"
 *
 * Return: <ARRAY> the polylines; each polyline is a list of [x, y] points.
 */
params [
    ["_affiliation", "friend", [""]],
    ["_dimension", "land", [""]]
];

// The base shape from the affiliation, APP-6(C).
private _shape = "rect";
if (_affiliation isEqualTo "hostile") then { _shape = "diamond"; };
if (_affiliation isEqualTo "neutral") then { _shape = "square"; };
if (_affiliation isEqualTo "unknown") then { _shape = "quatrefoil"; };
if (_dimension isEqualTo "equipment") then { _shape = "circle"; };

private _steps = 8;      // arc samples, a derived smoothness choice
private _poly = [];

// The closed rectangular family.  The dome and the curve replace an edge.
if (_shape isEqualTo "rect" || _shape isEqualTo "square") then {
    private _maxX = 1;       // friend rectangle half-width
    private _halfY = 0.6;    // friend rectangle half-height
    if (_shape isEqualTo "square") then {
        _maxX = 0.7;         // neutral square, equal half-extents
        _halfY = 0.7;
    };
    private _amp = 1 - _halfY;   // keeps the arc inside the unit box

    if (_dimension isEqualTo "subsurface") then {
        for "_i" from 0 to _steps do {
            private _t = -1 + (2 * _i / _steps);
            _poly pushBack [_maxX * _t, -_halfY - (_amp * (1 - _t * _t))];
        };
    } else {
        _poly pushBack [-_maxX, -_halfY];
        _poly pushBack [_maxX, -_halfY];
    };

    if (_dimension isEqualTo "air") then {
        for "_i" from 0 to _steps do {
            private _t = 1 - (2 * _i / _steps);
            _poly pushBack [_maxX * _t, _halfY + (_amp * (1 - _t * _t))];
        };
    } else {
        _poly pushBack [_maxX, _halfY];
        _poly pushBack [-_maxX, _halfY];
    };
};

if (_shape isEqualTo "diamond") then {
    _poly = [[0, -1], [1, 0], [0, 1], [-1, 0]];
};

if (_shape isEqualTo "quatrefoil") then {
    private _a = 0.5;        // lobe half-side, so the lobes reach the unit box
    private _wedge = 180 / _steps;
    for "_j" from 0 to 3 do {
        private _centreX = [0, _a, 0, -_a] select _j;
        private _centreY = [_a, 0, -_a, 0] select _j;
        private _start = [0, -90, 180, 90] select _j;
        for "_i" from 0 to _steps do {
            private _angle = _start + (_i * _wedge);
            _poly pushBack [
                _centreX + (_a * (cos _angle)),
                _centreY + (_a * (sin _angle))
            ];
        };
    };
};

if (_shape isEqualTo "circle") then {
    for "_i" from 0 to 23 do {
        private _angle = 360 * _i / 24;
        _poly pushBack [0.8 * (cos _angle), 0.8 * (sin _angle)];
    };
};

// The frame is one polyline.  Two dimensions add a filled marker.
private _out = [_poly];
if (_dimension isEqualTo "space") then {
    _out pushBack [[-0.4, 0.6], [0, 1], [0.4, 0.6]];               // filled apex
};
if (_dimension isEqualTo "installation") then {
    _out pushBack [[-0.7, 0.6], [0.7, 0.6], [0.7, 0.85], [-0.7, 0.85]];  // top bar
};

_out
