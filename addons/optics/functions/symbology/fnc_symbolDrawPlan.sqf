#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbolDrawPlan
 *
 * Pure draw-plan kernel.  Turns one symbol specification into one ordered
 * list of geometry primitives in the unit box [-1, 1].  PURE: the spec
 * arrives as an argument and the only calls are the pure frame and icon
 * kernels, so this kernel reads no marker, no unit, no setting and no
 * engine draw command.
 *
 * Each primitive is [kind, points, colourHint].  kind is "line", "poly" or
 * "ellipse".  colourHint is "frame" for the outline, the echelon marks and
 * the label anchors, and "icon" for the inner glyph.  The draw layer applies
 * the RGBA from the spec, so geometry and colour stay separate.
 *
 * The order is: the frame outline first, the inner glyph next, the echelon
 * marks third and the label anchors last.
 *
 * A label anchor is a "poly" with exactly one point.  It marks where a text
 * field attaches, not a filled shape; the draw layer branches on the point
 * count.  The two anchors sit above and below the symbol, APP-6(C) Table 3-2.
 *
 * Arguments:
 *   0: _spec <ARRAY> [affiliation, frameShape, dimension, colourRGBA, iconId,
 *      echelon] from FUNC(symbolResolve)
 *
 * Return: <ARRAY> the ordered primitive list.
 */
params [
    ["_spec", [], [[]]]
];

private _affiliation = _spec select 0;
private _dimension = _spec select 2;
private _iconId = _spec select 4;
private _echelon = _spec select 5;

private _plan = [];

// 1. The frame outline.  FUNC(symbolFrame) derives the base shape from the
// affiliation, so the carried frameShape token is not read again.
{
    _plan pushBack ["poly", _x, "frame"];
} forEach ([_affiliation, _dimension] call FUNC(symbolFrame));

// 2. The inner glyph, already [kind, points] from FUNC(symbolIcon).
{
    _plan pushBack [_x select 0, _x select 1, "icon"];
} forEach ([_iconId] call FUNC(symbolIcon));

// 3. The echelon marks, above the frame, APP-6(C) Table 3-7.  A dot is a
// filled ellipse, a bar is a line and an X is two crossed lines.  An
// unknown echelon adds no mark.
private _row = 0.8;
private _marks = [];
if (_echelon isEqualTo "team") then {
    _marks = [["ellipse", [[0, _row], [0.05, 0.05], 0]]];
};
if (_echelon isEqualTo "squad") then {
    _marks = [["ellipse", [[0, _row], [0.06, 0.06], 0]]];
};
if (_echelon isEqualTo "section") then {
    _marks = [
        ["ellipse", [[-0.09, _row], [0.06, 0.06], 0]],
        ["ellipse", [[0.09, _row], [0.06, 0.06], 0]]
    ];
};
if (_echelon isEqualTo "platoon") then {
    _marks = [
        ["ellipse", [[-0.18, _row], [0.06, 0.06], 0]],
        ["ellipse", [[0, _row], [0.06, 0.06], 0]],
        ["ellipse", [[0.18, _row], [0.06, 0.06], 0]]
    ];
};
if (_echelon isEqualTo "company") then {
    _marks = [["line", [[-0.15, _row], [0.15, _row]]]];
};
if (_echelon isEqualTo "battalion") then {
    _marks = [
        ["line", [[-0.15, _row], [0.15, _row]]],
        ["line", [[-0.15, _row - 0.12], [0.15, _row - 0.12]]]
    ];
};
if (_echelon isEqualTo "regiment") then {
    _marks = [
        ["line", [[-0.15, _row], [0.15, _row]]],
        ["line", [[-0.15, _row - 0.12], [0.15, _row - 0.12]]],
        ["line", [[-0.15, _row - 0.24], [0.15, _row - 0.24]]]
    ];
};
if (_echelon isEqualTo "brigade") then {
    _marks = [
        ["line", [[-0.1, _row - 0.1], [0.1, _row + 0.1]]],
        ["line", [[-0.1, _row + 0.1], [0.1, _row - 0.1]]]
    ];
};
if (_echelon isEqualTo "division") then {
    _marks = [
        ["line", [[-0.22, _row - 0.1], [-0.02, _row + 0.1]]],
        ["line", [[-0.22, _row + 0.1], [-0.02, _row - 0.1]]],
        ["line", [[0.02, _row - 0.1], [0.22, _row + 0.1]]],
        ["line", [[0.02, _row + 0.1], [0.22, _row - 0.1]]]
    ];
};
if (_echelon isEqualTo "corps") then {
    _marks = [
        ["line", [[-0.3, _row - 0.1], [-0.14, _row + 0.1]]],
        ["line", [[-0.3, _row + 0.1], [-0.14, _row - 0.1]]],
        ["line", [[-0.08, _row - 0.1], [0.08, _row + 0.1]]],
        ["line", [[-0.08, _row + 0.1], [0.08, _row - 0.1]]],
        ["line", [[0.14, _row - 0.1], [0.3, _row + 0.1]]],
        ["line", [[0.14, _row + 0.1], [0.3, _row - 0.1]]]
    ];
};
{
    _plan pushBack [_x select 0, _x select 1, "frame"];
} forEach _marks;

// 4. The label anchors, above and below the symbol.  A one-point "poly" is
// the anchor convention the draw layer reads.
_plan pushBack ["poly", [[0, 1]], "frame"];
_plan pushBack ["poly", [[0, -1]], "frame"];

_plan
