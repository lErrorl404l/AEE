// PHASE 127: the MGRS grid line straightness and the conversion jitter, live.
//
// The overlay draws each grid line as one straight chord (fnc_mgrsGridLines).
// This probe proves, on the live world:
//   1. the plan emits one chord per line, so there is no interior joint to
//      bead at the seam;
//   2. the emitted chord is faithful: the live midpoint of a line deviates
//      from the chord by under one map pixel (span/1024);
//   3. the per-sample conversion jitter: a dense 41-point sample of one line
//      wanders from its chord, which is why densifying added joints rather
//      than removing the bend (the exact series bows by under a millimetre at
//      this span, proved in tools/tests/test_mgrs_map_layer.py);
//   4. the grid is aligned to UTM grid north, so a line is tilted from the
//      map's cardinal axes by the grid convergence (reported, not a defect).
//
// It renders nothing.
//
// Emits [P127] PASS/FAIL lines.

private _fnAnchor = missionNamespace getVariable ["aee_core_fnc_getGeoAnchor", nil];
private _fnW2M = missionNamespace getVariable ["aee_core_fnc_worldToMgrs", nil];
private _fnU2W = missionNamespace getVariable ["aee_core_fnc_utmToWorld", nil];
private _fnGrid = missionNamespace getVariable ["aee_optics_fnc_mgrsGridLines", nil];
if (isNil "_fnAnchor" || {isNil "_fnW2M"} || {isNil "_fnU2W"} || {isNil "_fnGrid"}) exitWith {
    diag_log text "[P127] [FAIL] MGRS straightness kernels not compiled";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

private _anchor = call _fnAnchor;
private _mapSize = _anchor select 3;
if (_mapSize <= 0) then { _mapSize = 8192; };
private _zone = (floor (((_anchor select 1) + 180) / 6)) + 1;
if (_zone < 1) then { _zone = 1; };
if (_zone > 60) then { _zone = 60; };
private _hemi = "north";
if ((_anchor select 0) < 0) then { _hemi = "south"; };

// The visible 2 km view at the world centre.  One pixel is span/1024, the
// same conservative pixel the planner uses.
private _c = _mapSize / 2;
private _span = 2000;
private _rect = [_c - 1000, _c - 1000, _c + 1000, _c + 1000];
private _pixel = _span / 1024;

// ── 1. one chord per line: no interior joint ──────────────────────────────
private _plan = [_anchor, _rect, 100] call _fnGrid;
_plan params ["_segments", "_labels", "_interval"];
private _segCount = count _segments;
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
    _notes pushBack format ["plan: segments=%1 joints=%2 interval=%3", _segCount, _joints, _interval];
};

// ── 2/3/4. the chord, the jitter and the convergence on one line ──────────
// A constant-easting line at the nearest 100 m to the view centre.
private _cMgrs = [[_c, _c, 0], _anchor, 10] call _fnW2M;
private _eLine = (ceil ((_cMgrs select 3) / 100)) * 100;
private _nLo = (_cMgrs select 4) - 1000;
private _nHi = (_cMgrs select 4) + 1000;
private _pA = [_eLine, _nLo, _zone, _hemi, _anchor] call _fnU2W;
private _pB = [_eLine, _nHi, _zone, _hemi, _anchor] call _fnU2W;
private _vx = (_pB select 0) - (_pA select 0);
private _vy = (_pB select 1) - (_pA select 1);
private _len = sqrt ((_vx * _vx) + (_vy * _vy));

private _chordDev = 0;
private _wander = 0;
private _tilt = 0;
if (_len > 0) then {
    private _pM = [_eLine, (_nLo + _nHi) / 2, _zone, _hemi, _anchor] call _fnU2W;
    _chordDev = abs (((_pM select 0) - (_pA select 0)) * _vy - ((_pM select 1) - (_pA select 1)) * _vx) / _len;
    private _p = [];
    private _d = 0;
    for "_k" from 1 to 40 do {
        _p = [_eLine, _nLo + ((_nHi - _nLo) * _k / 40), _zone, _hemi, _anchor] call _fnU2W;
        _d = abs (((_p select 0) - (_pA select 0)) * _vy - ((_p select 1) - (_pA select 1)) * _vx) / _len;
        if (_d > _wander) then { _wander = _d; };
    };
    _tilt = _vx atan2 _vy;
};

// 2. the chord is faithful: the live midpoint is under a pixel from it.
if ((_len > 0) && {_chordDev < _pixel}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["chord deviation %1 m at pixel %2 m", _chordDev, _pixel];
};

// 3. the jitter is sub-pixel, so a two-point chord is adequate.  The value is
// reported as the root-cause evidence; the exact-series bow at this span is
// under a millimetre, so a value above that is the live conversion jitter.
if ((_len > 0) && {_wander < _pixel}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["dense wander %1 m at pixel %2 m", _wander, _pixel];
};

// 4. the grid convergence: a true MGRS line is off cardinal by this angle.
if ((_len > 0) && {(abs _tilt) < 3}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["line tilt %1 deg", _tilt];
};

diag_log text format ["[P127] grid: interval=%1 segments=%2 joints=%3; chordDev=%4 m wander=%5 m pixel=%6 m; tilt=%7 deg (MGRS grid north); labels=%8",
    _interval, _segCount, _joints, _chordDev, _wander, _pixel, _tilt, count _labels];

if (_fail == 0) then {
    diag_log text format ["[P127] [PASS] MGRS grid straightness on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P127] [FAIL] MGRS grid straightness: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
