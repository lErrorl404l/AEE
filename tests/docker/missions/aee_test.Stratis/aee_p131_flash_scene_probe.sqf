// PHASE 131: the muzzle-flash scene coupling, headless.
//
// The eye driver samples the steady scene (physical sky plus the core local
// light) and holds a muzzle-flash transient (aee_optics_eyeFlashLux, stamped by
// the Fired handler).  The transient raises only the luminance the eye ADAPTS
// to.  It must never enter the PUBLISHED scene (aee_optics_eyeSceneLux),
// because the cross-module invariant INV-1 (night_scene_agreement) compares the
// published scene against the core illuminance, which carries no muzzle flash.
//
// A 5.56 shot in the operator RPT of 2026-10-08 published 4500.5 lx and raised
// a false INV-1 warning (drift 4499.97) while the core stayed at 0.53 lx.  This
// probe drives the pure kernel FUNC(eyeFlashScene), the flash kernel
// FUNC(eyeFlash) and the real evaluator with those RPT values.  It renders
// nothing and needs no player.
//
// Emits [P131] PASS/FAIL lines.

private _flashScene = missionNamespace getVariable ["aee_optics_fnc_eyeFlashScene", nil];
private _eyeFlash = missionNamespace getVariable ["aee_optics_fnc_eyeFlash", nil];
private _loadTable = missionNamespace getVariable ["aee_core_fnc_consistencyLoadTable", nil];
private _evaluate = missionNamespace getVariable ["aee_core_fnc_evaluateConsistency", nil];

if (isNil "_flashScene" || {isNil "_eyeFlash"} || {isNil "_loadTable"} || {isNil "_evaluate"}) exitWith {
    diag_log text "[P131] [FAIL] flash-scene kernels not compiled (eyeFlashScene/eyeFlash/consistency)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// The steady eye scene and the core illuminance from the operator RPT at
// 23:28:52 (night).  The flash term is the muzzle flash of the fired 5.56.
private _steady = 0.500858;
private _core = 0.530193;
private _flash = 4500;

// 1. The kernel keeps the flash out of the published scene.
private _split = [_steady, _flash, 10, 5] call _flashScene;
if ((_split isEqualType []) && {(count _split) == 2} && {abs ((_split select 0) - _steady) < 1e-6} && {abs ((_split select 1) - (_steady + _flash)) < 1e-3}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["split %1", str _split];
};

// 2. A closed window leaves both scenes steady.
private _closed = [_steady, _flash, 5, 10] call _flashScene;
if ((_closed isEqualType []) && {abs ((_closed select 0) - _steady) < 1e-6} && {abs ((_closed select 1) - _steady) < 1e-6}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["closed %1", str _closed];
};

// 3. The flash kernel maps the RPT visibleFire to the RPT scene offset.
private _flashLux = [3, false] call _eyeFlash;
if (abs (_flashLux - _flash) < 0.5) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["eyeFlash(3)=%1 (expected %2)", _flashLux, _flash];
};

// 4. The steady published scene passes INV-1 at night.
private _table = [] call _loadTable;
private _night = [
    ["aee_core_illuminanceLux", _core],
    ["aee_optics_eyeSceneLux", _steady],
    ["aee_core_currentTemperature", 17.5],
    ["aee_core_groundSurfaceTemp", 16.0],
    ["aee_core_avgGroundTemp", 15.7872],
    ["aee_core_currentSunElevation", -31.38],
    ["aee_thermal_skyBandTempC", -0.443878],
    ["aee_core_lightIsNight", true],
    ["aee_environmental_nightClassification", 4]
];
private _steadyResult = [_table, _night] call _evaluate;
private _steadyOk = _steadyResult select 0;
{ if !(_x select 1) then { _steadyOk = false; }; } forEach (_steadyResult select 1);
if (_steadyOk) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "steady night scene raised a row";
};

// 5. The flash-lit scene fails INV-1: the warning the RPT showed.
private _flashLit = +_night;
{
    if ((_x select 0) == "aee_optics_eyeSceneLux") then {
        _flashLit set [_forEachIndex, ["aee_optics_eyeSceneLux", _steady + _flash]];
    };
} forEach _flashLit;
private _flashResult = [_table, _flashLit] call _evaluate;
private _inv1 = [];
{ if ((_x select 0) == "INV-1") then { _inv1 = _x; }; } forEach (_flashResult select 1);
if ((count _inv1) == 4 && {!(_inv1 select 1)}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["flash-lit INV-1 %1", str _inv1];
};

diag_log text format ["[P131] flash scene: published=%1 adapt=%2 flash=%3 | INV-1 steady=%4 flashLit=%5",
    _split select 0, _split select 1, _flashLux, _steadyOk, !(_inv1 select 1)];

if (_fail == 0) then {
    diag_log text format ["[P131] [PASS] flash scene coupling: the published scene excludes the muzzle flash (%1 checks)", _pass];
} else {
    diag_log text format ["[P131] [FAIL] flash scene coupling: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
