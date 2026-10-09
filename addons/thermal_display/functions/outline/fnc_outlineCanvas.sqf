#include "..\..\script_component.hpp"
/*
 * Fusion outline canvas manager (issue #204).
 *
 * Ported from workshop 3811605241 whale_ecoti_llll functions/fn_outlineMap.sqf.
 * The outline is drawn on a full-screen transparent RscMapControl (the
 * display class GVAR(fusionOutline), control idc 1301) with ctrlAddEventHandler
 * ["Draw", ...] and `drawLine`, so the engine produces an anti-aliased, native
 * thickness line on the interface layer where the NVG does not filter it.
 *
 * The engine refuses to move a map control outside the terrain, so the canvas
 * is placed in a map corner at maximum zoom (a few metres on screen, nothing
 * to draw) and hidden for the first two frames while the placement applies.
 * aee owns the segments and the namespace keys; only the technique is copied.
 *
 * Modes:
 *   "begin" -> [cx, cy, kx, ky, control] screen -> canvas calibration, or []
 *              while the canvas is not ready.
 *   "set"   -> store the segment list (drawn on the next map draw).
 *   "clear" -> store an empty list.
 *
 * Params:
 *   0: _mode (STRING, default "begin").
 *   1: _list (ARRAY) - segments [pointA, pointB, colour, width] for "set".
 *
 * Returns: ARRAY (the calibration for "begin", otherwise empty).
 */
params [["_mode", "begin", [""]], ["_list", [], [[]]]];

if (_mode == "set") exitWith { uiNamespace setVariable [QGVAR(outlineSegs), _list]; };

uiNamespace setVariable [QGVAR(outlineSegs), []];

private _disp = uiNamespace getVariable [QGVAR(outlineDisplay), displayNull];
if (isNull _disp) exitWith { [] };

private _m = _disp displayCtrl 1301;
if (isNull _m) exitWith { [] };

// First use: place the canvas in a map corner at maximum zoom, add the Draw
// handler once.
if !(_m getVariable [QGVAR(outlineReady), false]) then {
    _m ctrlSetFade 1;
    _m ctrlCommit 0;
    _m ctrlMapAnimAdd [0, 0.0001, [5, 5, 0]];
    ctrlMapAnimCommit _m;
    _m ctrlAddEventHandler ["Draw", {
        params ["_mc"];
        { _mc drawLine _x; } forEach (uiNamespace getVariable [QGVAR(outlineSegs), []]);
    }];
    _m setVariable [QGVAR(outlineReady), true];
    _m setVariable [QGVAR(outlineReadyFrame), diag_frameNo];
};

// Two frames for the placement to apply, then show the canvas.
if (diag_frameNo < ((_m getVariable [QGVAR(outlineReadyFrame), 0]) + 2)) exitWith { [] };
if ((ctrlFade _m) > 0) then {
    _m ctrlSetFade 0;
    _m ctrlCommit 0;
};

if (_mode == "clear") exitWith { [] };

// Screen -> canvas calibration, linear, re-measured each frame.
private _o  = _m ctrlMapScreenToWorld [0.5, 0.5];
private _pX = _m ctrlMapScreenToWorld [0.6, 0.5];
private _pY = _m ctrlMapScreenToWorld [0.5, 0.6];
private _kx = ((_pX select 0) - (_o select 0)) / 0.1;
private _ky = ((_pY select 1) - (_o select 1)) / 0.1;
if ((abs _kx) < 1e-6 || {(abs _ky) < 1e-6}) exitWith { [] };

[(_o select 0) - (0.5 * _kx), (_o select 1) - (0.5 * _ky), _kx, _ky, _m]
