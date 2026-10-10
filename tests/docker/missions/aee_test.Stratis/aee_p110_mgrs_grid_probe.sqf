// PHASE 110: the MGRS map grid and cursor readout kernels on the live world.
//
// The map control and the cursor exist only on a client, so the probe drives
// the REAL pure kernels with the live anchor: the UTM-to-world inverse
// FUNC(utmToWorld), the grid planner FUNC(mgrsGridLines) and the readout
// formatter FUNC(mgrsCursorText).  It renders nothing.
//
// Emits [P110] PASS/FAIL lines.

private _fnAnchor = missionNamespace getVariable ["aee_lib_fnc_getGeoAnchor", nil];
private _fnW2M = missionNamespace getVariable ["aee_lib_fnc_worldToMgrs", nil];
private _fnU2W = missionNamespace getVariable ["aee_lib_fnc_utmToWorld", nil];
private _fnGrid = missionNamespace getVariable ["aee_cartography_fnc_mgrsGridLines", nil];
private _fnCursor = missionNamespace getVariable ["aee_cartography_fnc_mgrsCursorText", nil];
if (isNil "_fnAnchor" || {isNil "_fnW2M"} || {isNil "_fnU2W"} || {isNil "_fnGrid"} || {isNil "_fnCursor"}) exitWith {
    diag_log text "[P110] [FAIL] MGRS grid kernels not compiled (getGeoAnchor/worldToMgrs/utmToWorld/mgrsGridLines/mgrsCursorText)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

private _anchor = call _fnAnchor;
private _mapSize = _anchor select 3;
private _centre = [_mapSize / 2, _mapSize / 2, 0];

// 1. the UTM inverse round-trips the world centre
private _written = [_centre, _anchor, 10] call _fnW2M;
private _hemisphere = "north";
if ((_anchor select 0) < 0) then { _hemisphere = "south"; };
private _back = [
    _written select 3, _written select 4, _written select 5, _hemisphere, _anchor
] call _fnU2W;
private _drift = _centre distance _back;
if (_drift <= 1.0) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["utm inverse drifted %1 m", _drift];
};

// 2. the grid planner returns lines and labels for a 2 km view
private _half = 1000;
private _rect = [
    (_centre select 0) - _half,
    (_centre select 1) - _half,
    (_centre select 0) + _half,
    (_centre select 1) + _half
];
private _plan = [_anchor, _rect] call _fnGrid;
_plan params ["_segments", "_labels", "_interval"];
if ((count _segments) > 0 && {(count _labels) > 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "grid planner returned no lines or labels";
};

// 3. the interval is a decimal MGRS step
if (_interval in [10, 100, 1000, 10000, 100000]) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["interval %1 is not a decimal MGRS step", _interval];
};

// 4. every segment stays near the requested rectangle
private _inRect = true;
{
    _x params ["_pA", "_pB"];
    {
        if ((_x select 0) < ((_rect select 0) - 300) || {(_x select 0) > ((_rect select 2) + 300)}
            || {(_x select 1) < ((_rect select 1) - 300)} || {(_x select 1) > ((_rect select 3) + 300)}) then {
            _inRect = false;
        };
    } forEach [_pA, _pB];
} forEach _segments;
if (_inRect) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "a grid segment left the visible rectangle";
};

// 5. the cursor readout carries the reference and the elevation
private _cursor = [_written select 0, 123] call _fnCursor;
if ((_cursor find " m") >= 0 && {(_cursor find (_written select 0)) >= 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["cursor readout unexpected: %1", _cursor];
};

diag_log text format ["[P110] grid: interval=%1 segments=%2 labels=%3; utm drift=%4 m; cursor='%5'", _interval, count _segments, count _labels, _drift, _cursor];

if (_fail == 0) then {
    diag_log text format ["[P110] [PASS] MGRS grid and cursor kernels on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P110] [FAIL] MGRS grid kernels: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
