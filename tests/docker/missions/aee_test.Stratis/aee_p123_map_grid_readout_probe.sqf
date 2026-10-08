// PHASE 123: the map grid and the MGRS line geometry, asserted live.
//
// The engine grid colours are merged config, and the MGRS line plan is a pure
// kernel, so both are measurable headless.  The engine edge NUMBERS are the
// colour of `colorGrid` and the engine in-map LINES are the colour of
// `colorGridMap` (engine source: the open-sourced Poseidon engine, UIMap.cpp,
// CStaticMap::DrawGrid).  Both are off: the engine ruler clips its left and
// right numbers at close zoom, so the AEE MGRS overlay is the single ruler.  It
// renders nothing.
//
// Emits [P123] PASS/FAIL lines.

private _pass = 0;
private _fail = 0;
private _notes = [];

// ── The grid fields: edge NUMBERS on, engine LINES off, size at the default. ─
private _gridTargets = [
    ["RscMapControl", configFile >> "RscMapControl"],
    ["RscDisplayStrategicMap.Map", configFile >> "RscDisplayStrategicMap" >> "controlsBackground" >> "Map"],
    ["ctrlMap", configFile >> "ctrlMap"]
];
{
    _x params ["_label", "_cfg"];
    private _numbers = getArray (_cfg >> "colorGrid");
    private _lines = getArray (_cfg >> "colorGridMap");
    private _numbersOff = ((count _numbers) >= 4) && {(_numbers select 3) == 0};
    private _linesOff = ((count _lines) >= 4) && {(_lines select 3) == 0};
    if (_numbersOff && {_linesOff}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["grid %1: colorGrid=%2 colorGridMap=%3", _label, str _numbers, str _lines];
    };
} forEach _gridTargets;

// ── The overlay and readout kernels are compiled. ──────────────────────────
{
    if (isNil _x) then {
        _fail = _fail + 1;
        _notes pushBack (_x + " not compiled");
    } else {
        _pass = _pass + 1;
    };
} forEach [
    "aee_optics_fnc_mgrsMapDraw",
    "aee_optics_fnc_mgrsGridLines",
    "aee_optics_fnc_mgrsCursorText",
    "aee_optics_fnc_mgrsMarkerText"
];

// ── The MGRS line plan: computed live, densified and collinear.  A visible
// kink would show as a join deviation well above the sub-pixel bound. ───────
private _anchor = call aee_core_fnc_getGeoAnchor;
if ((count _anchor) >= 9) then {
    private _c = (_anchor select 3) / 2;
    private _rect = [_c - 1000, _c - 1000, _c + 1000, _c + 1000];
    private _plan = [_anchor, _rect, 100] call aee_optics_fnc_mgrsGridLines;
    _plan params ["_segments", "_labels", "_interval"];
    private _segCount = count _segments;
    if ((_segCount > 4) && {(count _labels) > 0}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["grid plan: segments=%1 labels=%2 interval=%3", _segCount, count _labels, _interval];
    };
    private _worst = 0;
    private _worstPair = [];
    private _minLen = 1e9;
    if (_segCount > 1) then {
        for "_i" from 0 to (_segCount - 2) do {
            (_segments select _i) params ["_a0", "_a1"];
            (_segments select (_i + 1)) params ["_b0", "_b1"];
            if (((_a1 select 0) == (_b0 select 0)) && {(_a1 select 1) == (_b0 select 1)}) then {
                private _v1 = [(_a1 select 0) - (_a0 select 0), (_a1 select 1) - (_a0 select 1)];
                private _v2 = [(_b1 select 0) - (_b0 select 0), (_b1 select 1) - (_b0 select 1)];
                private _n1 = sqrt (((_v1 select 0) ^ 2) + ((_v1 select 1) ^ 2));
                private _n2 = sqrt (((_v2 select 0) ^ 2) + ((_v2 select 1) ^ 2));
                private _len = _n1 min _n2;
                if ((_len > 0) && {_len < _minLen}) then { _minLen = _len; };
                private _cross = abs (((_v1 select 0) * (_v2 select 1)) - ((_v1 select 1) * (_v2 select 0)));
                if (_len > 0) then {
                    private _dev = _cross / _len;
                    if (_dev > _worst) then {
                        _worst = _dev;
                        _worstPair = [_a0, _a1, _b1];
                    };
                };
            };
        };
    };
    if (_worst < 2.0) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        // 2 m is one map pixel at the probe's 2 km view, so this bounds the
        // visible bend to under a pixel; the old two-chord line measured ~13 m.
        _notes pushBack format ["grid deviation %1 m interval %2 segs %3 minLen %4 anchor %5 pair %6", _worst, _interval, _segCount, _minLen, str _anchor, str _worstPair];
    };
} else {
    _fail = _fail + 1;
    _notes pushBack "no geo anchor";
};

// ── The cursor readout carries OUR MGRS at the displayed precision. ────────
private _cursor = ["35T NQ 123 456", 42] call aee_optics_fnc_mgrsCursorText;
if (((_cursor find "35T NQ 123 456") >= 0) && {(_cursor find " m") >= 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["cursor readout: %1", _cursor];
};

if (_fail == 0) then {
    diag_log text format ["[P123] [PASS] map grid and readouts on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P123] [FAIL] map grid and readouts: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
