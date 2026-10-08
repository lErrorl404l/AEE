// PHASE 127: the cardinal grid geometry, the world-metre interval and the
// positional MGRS labels, live.
//
// The overlay draws a CARDINAL grid (fnc_mgrsGridLines): each line follows a
// map axis, so a line is straight by construction and has zero tilt from the
// cardinal axes.  This is a deliberate change from the true MGRS grid; ADR-030
// records the reason.  This probe proves, on the live world:
//   1. every emitted segment is axis-aligned (a vertical line at constant
//      world x or a horizontal line at constant world y), so the tilt is zero;
//   2. the lines land on whole world-metre steps of the chosen interval, so
//      the grid is cardinal in world coordinates, not projected from UTM;
//   3. every line carries a positional MGRS label: the digit group at a fixed
//      point of the line, with the digit count that matches the interval;
//   4. the plan emits one segment per line, so there is no interior joint.
//
// It renders nothing.
//
// Emits [P127] PASS/FAIL lines.

private _fnAnchor = missionNamespace getVariable ["aee_core_fnc_getGeoAnchor", nil];
private _fnGrid = missionNamespace getVariable ["aee_optics_fnc_mgrsGridLines", nil];
if (isNil "_fnAnchor" || {isNil "_fnGrid"}) exitWith {
    diag_log text "[P127] [FAIL] cardinal grid kernels not compiled";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

private _anchor = call _fnAnchor;
private _mapSize = _anchor select 3;
if (_mapSize <= 0) then { _mapSize = 8192; };

// The visible 2 km view at the world centre, with a 100 m floor.
private _c = _mapSize / 2;
private _rect = [_c - 1000, _c - 1000, _c + 1000, _c + 1000];
private _plan = [_anchor, _rect, 100] call _fnGrid;
_plan params ["_segments", "_labels", "_interval"];
private _segCount = count _segments;
private _labelCount = count _labels;

if (_segCount == 0) exitWith {
    diag_log text format ["[P127] [FAIL] cardinal grid: no segments on %1", worldName];
};

// ── 1. cardinal geometry: every line is axis-aligned, so the tilt is zero ──
private _vertical = 0;
private _horizontal = 0;
private _tilt = 0;
{
    _x params ["_pA", "_pB"];
    private _vx = (_pB select 0) - (_pA select 0);
    private _vy = (_pB select 1) - (_pA select 1);
    if ((abs _vx) < 0.000001) then {
        _vertical = _vertical + 1;
        if ((abs _vy) < 0.000001) then { _tilt = 1; };
    } else {
        if ((abs _vy) < 0.000001) then {
            _horizontal = _horizontal + 1;
        } else {
            _tilt = 1;
        };
    };
} forEach _segments;
if ((_tilt == 0) && {_vertical > 0} && {_horizontal > 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["cardinal: vertical=%1 horizontal=%2 tiltFlag=%3", _vertical, _horizontal, _tilt];
};

// ── 2. the world-metre interval: lines land on whole world-metre steps ─────
private _onGrid = true;
{
    _x params ["_pA", "_pB"];
    private _vx = (_pB select 0) - (_pA select 0);
    private _coord = if ((abs _vx) < 0.000001) then { _pA select 0 } else { _pA select 1 };
    if ((abs ((_coord / _interval) - (round (_coord / _interval)))) > 0.0001) then {
        _onGrid = false;
    };
} forEach _segments;
if (_onGrid && {_interval in [10, 100, 1000, 10000, 100000]}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["interval %1 m not a world step", _interval];
};

// ── 3. the positional MGRS labels: digits, both ends of each line, length ──
private _perAxis = round (5 - (log _interval));
private _labelsOk = (_labelCount > 0) && {_labelCount == (2 * _segCount)};
{
    _x params ["_pos", "_text"];
    if !(_text isEqualType "") then { _labelsOk = false; };
    if ((count _text) != _perAxis) then { _labelsOk = false; };
    {
        if ((_x < 48) || {_x > 57}) then { _labelsOk = false; };
    } forEach (toArray _text);
} forEach _labels;
if (_labelsOk) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["labels=%1 segments=%2 perAxis=%3", _labelCount, _segCount, _perAxis];
};

// ── 4. one segment per line: no interior joint ─────────────────────────────
private _joints = 0;
if (_segCount > 1) then {
    for "_i" from 0 to (_segCount - 2) do {
        (_segments select _i) params ["_a0", "_a1"];
        (_segments select (_i + 1)) params ["_b0", "_b1"];
        if (((_a1 select 0) == (_b0 select 0)) && {(_a1 select 1) == (_b0 select 1)}) then {
            _joints = _joints + 1;
        };
    };
};
if ((_segCount > 4) && {_joints == 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["plan: segments=%1 joints=%2", _segCount, _joints];
};

diag_log text format ["[P127] cardinal grid: interval=%1 m segments=%2 (vertical=%3 horizontal=%4) joints=%5 labels=%6 perAxis=%7",
    _interval, _segCount, _vertical, _horizontal, _joints, _labelCount, _perAxis];

if (_fail == 0) then {
    diag_log text format ["[P127] [PASS] cardinal grid geometry on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P127] [FAIL] cardinal grid geometry: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
