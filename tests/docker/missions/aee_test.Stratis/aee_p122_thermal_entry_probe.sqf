// PHASE 122: the thermal first-entry pre-warm contract, measured headlessly.
//
// WHY THIS EXISTS.  The first thermal entry used to create the eight
// ppEffects on the entry tick and commit them from a DISABLED state.  The
// engine defers the build of an enabled chain to the next commit, so the
// 907 ms build landed on the tick AFTER entry (operator RPT
// Arma3_x64_2026-10-08_17-51-36: applyThermalVision 907 ms, sensorPFH
// 967 ms, the worst tick of the run).  The fix moves creation and the
// first-use build off the entry path: FUNC(createThermalPPEffects) is the
// idempotent create choke point, and FUNC(warmThermalPPEffects) builds the
// chains once at postInit on an idle client tick.
//
// WHAT THIS PROBE MEASURES (all honest headless):
//   (1) The per-selection solve cost the entry paint drives: the REAL
//       aee_thermal_fnc_solveTwoNodeSelection on a fixed fixture, best of
//       three.  This is the script work removed from the first entry.
//   (2) The create/driver source contract: FUNC(createThermalPPEffects) is
//       callable, returns a BOOL, and is IDEMPOTENT - the eight handle
//       variables are identical across a repeat call, so the entry path
//       cannot churn the effects.
//   (3) The warm client gate: FUNC(warmThermalPPEffects) returns false on a
//       dedicated server (hasInterface is false) and changes no handle.
//   (4) Both kernel functions are compiled and registered.
//
// WHAT THIS PROBE DOES NOT MEASURE (state the ceiling, do not fake it):
//   - The engine-side chain build (the 907 ms) and the rendered image.  A
//     dedicated server has no display and no post-process chain.
//   - The eight handles being SET by the warm.  The warm is client-only
//     (it early-exits without hasInterface), so on this server the handles
//     can only come from the create function, and ppEffectCreate is NOT a
//     trustworthy headless measurement (the engine may refuse it).  The
//     probe therefore measures the create idempotency and the client gate,
//     not the engine build.  A client run is the only place the build cost
//     can be confirmed removed.
//
// Emits [P122] DIAG / [PASS] / [FAIL] lines.

missionNamespace setVariable ["aee_thermal_logDebug", false];
missionNamespace setVariable ["aee_core_logDebug", false];

private _fnCreate = missionNamespace getVariable ["aee_thermal_display_fnc_createThermalPPEffects", nil];
private _fnWarm = missionNamespace getVariable ["aee_thermal_display_fnc_warmThermalPPEffects", nil];
private _fnSolve = missionNamespace getVariable ["aee_thermal_fnc_solveTwoNodeSelection", nil];

if (isNil "_fnCreate" || {isNil "_fnWarm"} || {isNil "_fnSolve"}) exitWith {
    diag_log text "[P122] [FAIL] thermal pre-warm functions not compiled (create/warm/solve)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// The eight handle stores, in the order the create table declares them.
private _stores = [
    "aee_thermal_display_ppHandle_Thermal_Chroma",
    "aee_thermal_display_ppHandle_Thermal_Vignette",
    "aee_thermal_display_ppHandle_Thermal_Blur",
    "aee_thermal_display_ppHandle_Thermal_Grain",
    "aee_thermal_display_ppHandle_Thermal_CC",
    "aee_thermal_display_ppHandle_Thermal_Inversion",
    "aee_thermal_display_ppHandle_Thermal_WetDistortion",
    "aee_thermal_display_ppHandle_Thermal_Resolution"
];
private _readHandles = {
    _stores apply { missionNamespace getVariable [_x, -1] };
};

// ── 1. Per-selection solve cost (the paint kernel) ────────────────────────
private _solveWork = {
    for "_i" from 1 to 20 do {
        [objNull, "sel", "metal", "metal", 15, 0, 0, 1, 50, 20, 6, 0.5, 20, 20, 0, "vertical", 0.5, 15, false, 0.008, true, 5] call _fnSolve;
    };
};
[] call _solveWork;
private _solveBest = 1e9;
for "_r" from 1 to 3 do {
    private _t0 = diag_tickTime;
    [] call _solveWork;
    private _ms = (diag_tickTime - _t0) * 1000;
    if (_ms < _solveBest) then { _solveBest = _ms; };
};
// The solve is pure arithmetic; the bound is a SANITY ceiling, not a
// performance budget.  The host is shared and under load, so the measured
// figure (reported below) ranges a few ms to a few tens of ms per call; only
// a catastrophic regression (a config/engine call returning to the loop)
// should trip this.
if (_solveBest < 1000) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["two-node solve %1 ms for 20 calls", _solveBest];
};

// ── 2. Create function: script cost, return type, idempotency ─────────────
// The first call is the create path; the repeat call must be a no-op over
// the same handles.  On a headless host ppEffectCreate may refuse, so the
// idempotency check is on the handle SET (stable across calls), not on a
// cost drop, and the cost bound is loose: it catches a per-call engine read,
// not the host speed.
private _before = [] call _readHandles;
private _tFirst = diag_tickTime;
private _okFirst = [] call _fnCreate;
private _firstMs = (diag_tickTime - _tFirst) * 1000;
private _afterFirst = [] call _readHandles;
private _tRepeat = diag_tickTime;
private _okRepeat = [] call _fnCreate;
private _repeatMs = (diag_tickTime - _tRepeat) * 1000;
private _afterRepeat = [] call _readHandles;

if ((_okFirst isEqualType true) && {_okRepeat isEqualType true}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["create did not return a BOOL (first %1, repeat %2)", _okFirst, _okRepeat];
};
if (_afterRepeat isEqualTo _afterFirst) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["create is not idempotent: %1 -> %2", _afterFirst, _afterRepeat];
};
if (_firstMs < 500) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["create first call %1 ms over the 500 ms sanity bound", _firstMs];
};
private _live = { _x >= 0 } count _afterFirst;

// ── 3. The warm client gate ───────────────────────────────────────────────
// On this dedicated server hasInterface is false, so the warm must be a
// no-op: it returns false and leaves every handle exactly as it found it.
private _warmBefore = [] call _readHandles;
private _warmOk = [] call _fnWarm;
private _warmAfter = [] call _readHandles;
diag_log text format ["[P122] DIAG host hasInterface=%1 warmReturned=%2 handlesBefore=%3 handlesAfter=%4",
    hasInterface, _warmOk, str _warmBefore, str _warmAfter];
if ((hasInterface isEqualTo false) && {_warmOk isEqualTo false} && {_warmAfter isEqualTo _warmBefore}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["warm is not a server no-op: hasInterface %1 returned %2", hasInterface, _warmOk];
};

// ── 4. Kernel registration ────────────────────────────────────────────────
if (!isNil "_fnCreate" && {!isNil "_fnWarm"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "create/warm kernel not registered";
};

// ── Cleanup: release any handle the create call left behind ───────────────
{
    private _h = missionNamespace getVariable [_x, -1];
    if (_h >= 0) then {
        ppEffectDestroy _h;
        missionNamespace setVariable [_x, -1];
    };
} forEach _stores;

diag_log text format ["[P122] create ms first=%1 repeat=%2 liveHandles=%3; solve ms/20=%4",
    _firstMs, _repeatMs, _live, _solveBest];

if (_fail == 0) then {
    diag_log text format ["[P122] [PASS] thermal pre-warm contract: %1 checks (solve %2 ms/20, create %3 ms first, live %4)",
        _pass, _solveBest, _firstMs, _live];
} else {
    diag_log text format ["[P122] [FAIL] thermal pre-warm contract: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
