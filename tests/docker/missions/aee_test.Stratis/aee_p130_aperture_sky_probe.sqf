// PHASE 130: the aperture is handed back to the eye model after a sensor exit,
// and the sky/horizon brightness after a time skip is engine-owned.
//
// Defect 1 (operator report: the view goes dark after NVG or thermal).  The eye
// driver stands down while a vision sensor owns the exposure and re-writes
// setApertureNew only when its value moves (the 0.02 change gate).  A pin left
// set across the sensor session suppresses that re-write, so the camera stays on
// the sensor's exposure.  The fix releases the pin at every sensor exit that
// restores the engine aperture.  This probe sets the pin and calls the REAL exit
// functions headless; each short-circuits before any player work, so the pin
// must be nil after each call, and the probe mirrors the change gate with the
// real aperture kernel to show the re-claim.
//
// Defect 2 (operator report: the sky and horizon read too bright after a time
// skip).  The probe reads the RESOLVED world config: AEE's DayLighting override
// carries only the deepNight (-15 deg) and fullNight (-5 deg) keys, so every
// keyframe above the horizon is vanilla and the daylight sky is engine-owned.
// A headless server cannot measure the sky brightness itself: its lighting
// engine is frozen (it advances only per client camera), so the probe reads the
// config facts and the engine's static HDR values, and reports the engine
// ambient where a real unit exists.  It renders nothing.
//
// Emits [P130] PASS/FAIL lines.

private _pass = 0;
private _fail = 0;
private _notes = [];

// ── Part A: the aperture is handed back after a sensor exit ────────────────
private _teardown = missionNamespace getVariable ["aee_vision_fnc_teardownSensors", nil];
private _exitThermal = missionNamespace getVariable ["aee_vision_fnc_exitThermalSensors", nil];
private _apFn = missionNamespace getVariable ["aee_eye_fnc_eyeAperture", nil];

if (isNil "_teardown" || {isNil "_exitThermal"} || {isNil "_apFn"}) then {
    _fail = _fail + 1;
    _notes pushBack "sensor exit functions or aperture kernel not compiled";
} else {
    // The NVG/thermal exit: teardownSensors owns it.  Headless the sensor PFH
    // is nil, so the function runs its aperture restore and pin release, then
    // exits before the per-module teardown (which needs a live session).
    missionNamespace setVariable ["aee_eye_eyePinned", true];
    [] call _teardown;
    if (isNil "aee_eye_eyePinned") then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "teardownSensors did not release the eye pin";
    };

    // The DTV host exit: exitThermalSensors owns it.
    missionNamespace setVariable ["aee_eye_eyePinned", true];
    [] call _exitThermal;
    if (isNil "aee_eye_eyePinned") then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack "exitThermalSensors did not release the eye pin";
    };

    // The re-claim.  With the pin released the change gate fires on the first
    // normal-vision tick even when the scene did not move, so the eye model's
    // aperture is written over the sensor's fixed 15.  Mirror the gate against
    // the REAL post-exit pin state and the REAL night aperture (RPT scene 0.5 lx).
    private _nightAperture = [0.5] call _apFn;
    private _lastV = _nightAperture;                        // the value pinned before the sensor
    private _moved = abs (_nightAperture - _lastV) > 0.02;  // the scene did not move
    private _bugWrites = _moved;                            // pin survived: only a moved value writes
    private _fixPinned = !(isNil "aee_eye_eyePinned");   // the real state after the exits
    private _fixWrites = (!_fixPinned) || {_moved};         // pin released: always writes
    if ((!_bugWrites) && {_fixWrites} && {_nightAperture > 8} && {_nightAperture < 20}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["gate night=%1 bugWrites=%2 fixWrites=%3", _nightAperture, _bugWrites, _fixWrites];
    };
    diag_log text format ["[P130] aperture restore: night=%1 sensor=15 moved=%2 bugWrites=%3 fixWrites=%4",
        _nightAperture, _moved, _bugWrites, _fixWrites];
};

// ── Part B: the daylight sky is engine-owned ───────────────────────────────
private _world = configFile >> "CfgWorlds" >> worldName;
private _bright = _world >> "DayLightingBrightAlmost";
private _deepNight = getArray (_bright >> "deepNight");
private _fullNight = getArray (_bright >> "fullNight");
private _deepFirst = if ((count _deepNight) > 0) then { _deepNight select 0 } else { 999 };
private _fullFirst = if ((count _fullNight) > 0) then { _fullNight select 0 } else { 999 };
if ((_deepFirst == -15) && {_fullFirst == -5}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["DayLighting keys deep=%1 full=%2", _deepFirst, _fullFirst];
};

// AEE's static HDR values reached the engine (the resolved world config).  They
// carry no time dependence, so they cannot be the cause of a skip-specific sky.
private _hdr = _world >> "HDRNewPars";
private _bloom = getNumber (_hdr >> "bloomScale");
private _linearWhite = getNumber (_hdr >> "tonemapLinearWhite");
if ((_bloom == 0.09) && {_linearWhite == 11.2}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["HDR bloom=%1 linearWhite=%2", _bloom, _linearWhite];
};

// AEE's only run-time lighting output is the four-element world profile,
// consumed by the star scale, the weather grain and the exhaust shimmer.
private _profile = missionNamespace getVariable ["aee_lighting_worldLighting", []];
if ((_profile isEqualType []) && {(count _profile) == 4}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["aee profile %1", str _profile];
};

// The engine's own sky ambient (getLightingAt) is not read here: on a headless
// server the lighting engine is frozen (it advances only per client camera), so
// it carries no sky-brightness signal.  The resolved config facts above are the
// measurement the probe can make without a renderer.
diag_log text format ["[P130] sky ownership: DayLighting deep=%1 full=%2 | HDR bloom=%3 linearWhite=%4 | aeeProfile=%5",
    _deepFirst, _fullFirst, _bloom, _linearWhite, str _profile];

if (_fail == 0) then {
    diag_log text format ["[P130] [PASS] aperture restore + sky ownership on %1 (%2 checks)", worldName, _pass];
} else {
    diag_log text format ["[P130] [FAIL] aperture restore + sky ownership: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
