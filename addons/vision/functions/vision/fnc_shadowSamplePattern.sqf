#include "..\..\script_component.hpp"

/*
Shadow scene-sampling pattern (aee-workshop-copy item 6, part 1).

Re-derived from fn_samplescene.sqf in Adaptive Shadows (Workshop 3792830104).
The mod publishes no licence, so this is a re-derived numeric kernel, not
copied code.  No mod content is copied.  The 25-point weighted pattern and the
0.52 optics contraction are UNSOURCED heuristics: they come from the mod's
own tuning, not from a published measurement.

The pattern is a set of screen-space points in normalised device coords,
each with a weight.  The centre point carries the highest weight, so the
classification is biased to what the eye is looking at.  When the player is
in optics, the pattern contracts toward the centre by the factor 0.52, so the
sample set narrows to the magnified field of view.

The kernel is pure: no missionNamespace, no GVAR or EGVAR, no engine command.
It reads only its arguments.  The driver applies the pattern with the real
camera commands; this kernel only builds the coordinates.

Arguments:
  0: Number  - requested sample count, clamped to 5..25
  1: Boolean - optics view; true contracts the pattern toward the centre

Returns:
  Array of [screenX, screenY, weight]
*/

params [
    ["_requestedCount", 13, [0]],
    ["_optics", false, [true]]
];

private _pattern = [
    [0.50, 0.50, 2.00],
    [0.32, 0.50, 1.25],
    [0.68, 0.50, 1.25],
    [0.50, 0.34, 1.20],
    [0.50, 0.66, 1.10],
    [0.32, 0.34, 1.00],
    [0.68, 0.34, 1.00],
    [0.32, 0.66, 0.95],
    [0.68, 0.66, 0.95],
    [0.14, 0.50, 0.80],
    [0.86, 0.50, 0.80],
    [0.50, 0.18, 0.80],
    [0.50, 0.82, 0.70],
    [0.14, 0.34, 0.70],
    [0.86, 0.34, 0.70],
    [0.14, 0.66, 0.65],
    [0.86, 0.66, 0.65],
    [0.32, 0.18, 0.65],
    [0.68, 0.18, 0.65],
    [0.32, 0.82, 0.60],
    [0.68, 0.82, 0.60],
    [0.08, 0.20, 0.55],
    [0.92, 0.20, 0.55],
    [0.08, 0.80, 0.50],
    [0.92, 0.80, 0.50]
];

private _count = round ((_requestedCount max 5) min (count _pattern));
private _out = [];

for "_i" from 0 to (_count - 1) do {
    private _point = _pattern select _i;
    private _screenX = _point select 0;
    private _screenY = _point select 1;
    private _weight = _point select 2;

    if (_optics) then {
        _screenX = 0.5 + ((_screenX - 0.5) * 0.52);
        _screenY = 0.5 + ((_screenY - 0.5) * 0.52);
    };

    _out pushBack [_screenX, _screenY, _weight];
};

_out
