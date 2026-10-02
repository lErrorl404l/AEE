// PHASE 79: the thermal startup, exercised on a headless server.
//
// WHY THIS EXISTS. The operator's client run showed a thermal flicker. On the
// FIRST AGC pass the published band `b` jumped about 59 display levels, when
// the no-AGC manual fallback window (span about 133) was replaced by the
// max-gain floor (span fullSpan/8 = 17.3655). That is an eight-fold gain
// change in one frame. The fix (c54ca9d) seeds the first AGC publication from
// the manual window, so the gain change ramps on the IIR time constant. It
// also seeds the two-node solver on first sight, so the transient lands on
// the solver equilibrium instead of marching from the air seed.
//
// WHY A HEADLESS PROBE. The paint path (fnc_applySelectionThermal) opens with
// `if (isNull _obj || {!hasInterface}) exitWith { 0 };`, and hasInterface is a
// read-only engine command. A dedicated server can never run the paint. The
// AGC solver and the two-node solver carry NO hasInterface gate, so this probe
// drives the REAL SQF directly. It does not fake the render.
//
// WHAT IS PROVEN HEADLESSLY:
//   (1) NO STARTUP JUMP. After the manual fallback the first AGC pass must
//       ramp, not snap. The probe first drives the AGC to its fixed point,
//       which is exactly what the pre-fix first pass published, and proves
//       that snap is large. It then asserts the real first-pass jump is small
//       and less than half of that snap.
//   (2) STABLE WHEN STABLE. With the scene held constant, the settled band
//       must not move across repeated passes. The probe counts level moves.
//   (2b) STABLE UNDER JITTER. The settled floor window breathed over 5
//       percent of its span in the client run, and the old 1 percent band
//       chased it. The scene is translated by that measured 5 percent on
//       alternate passes; the band must not move and the accepted window
//       must hold. This is the dead-band's contract.
//   (2c) STILL MOVES FOR A NEW SCENE. A sustained scene change far larger
//       than the dead-band must release: the window holds jitter, it never
//       freezes the display.
//   (3) SOLVER FIRST SIGHT. The real two-node solver, given the first-sight
//       step (1000000 s), must land on the seed-independent equilibrium. A
//       normal 5 s step must be a transient between the seed and that point.
//
// WHAT STILL NEEDS A CLIENT RUN: the rendered image (the painted colours and
// the engine thermal compositor). A server has no camera and no display.
//
// Bounded and deterministic: a fixed scene, one first pass, a fixed settle
// loop and a fixed stability loop. Emits [P79] DIAG/PASS/FAIL lines.

private _fnAGC = missionNamespace getVariable ["aee_thermal_fnc_updateThermalAGC", nil];
private _fnSolve = missionNamespace getVariable ["aee_thermal_fnc_solveTwoNodeSelection", nil];
private _fnBand = missionNamespace getVariable ["aee_thermal_fnc_calculateBandRadiance", nil];
private _fnGround = missionNamespace getVariable ["aee_thermal_fnc_calculateGroundTemperature", nil];
private _fnMat = missionNamespace getVariable ["aee_thermal_fnc_getMaterialThermal", nil];

if (isNil "_fnAGC" || {isNil "_fnSolve"} || {isNil "_fnBand"} || {isNil "_fnGround"} || {isNil "_fnMat"}) exitWith {
    diag_log text "[P79] [FAIL] kernel functions not compiled (AGC/solver/band/ground/material)";
};

private _fail = 0;

// A band maps a radiance into the display range 0..1. The flicker is measured
// in display levels, so one level is 1/255 of the band. This matches the
// paint line `_b = (_rad - _agcMin) / ((_agcMax - _agcMin) max 1e-6)`.
private _band = {
    params ["_rad", "_lo", "_hi"];
    (((_rad - _lo) / ((_hi - _lo) max 1e-6)) max 0) min 1
};

// ── (1) and (2): the AGC startup and the steady scene ─────────────────────
// The environment is read exactly as fnc_updateThermalAGC reads it, so the
// computed fallback window is the same window the display used before the
// first AGC pass.
private _airTemp = missionNamespace getVariable ["aee_core_currentTemperature", 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _groundTemp = [getPosASL player] call _fnGround;
if !(_groundTemp isEqualType 0) then {
    _groundTemp = missionNamespace getVariable ["aee_core_avgGroundTemp", _airTemp];
};
if !(_groundTemp isEqualType 0) then { _groundTemp = _airTemp; };
private _groundEps = (["ground"] call _fnMat) select 0;
private _manMinC = missionNamespace getVariable ["aee_thermal_thermalManualMinC", -40];
private _manMaxC = missionNamespace getVariable ["aee_thermal_thermalManualMaxC", 120];
if !(_manMinC isEqualType 0) then { _manMinC = -40; };
if !(_manMaxC isEqualType 0) then { _manMaxC = 120; };
if (_manMaxC <= _manMinC) then { _manMaxC = _manMinC + 1; };
private _fullMin = [_manMinC, _groundEps, _airTemp, 0.5, _groundTemp, 1, _airTemp, false] call _fnBand;
private _fullMax = [_manMaxC, _groundEps, _airTemp, 0.5, _groundTemp, 1, _airTemp, false] call _fnBand;
private _fullSpan = (_fullMax - _fullMin) max 1e-6;

// The operator's startup scene sat under the max-gain floor. Two selection
// bands straddle the probe radiance, so the raw scene midpoint IS the probe
// radiance. The pre-fix snap then maps that radiance from its fallback band to
// the floor centre, which is the full eight-fold gain change. The ground
// sample falls between the two bands, so it does not set the extremes.
private _coldC = 11;
private _hotC = 31;
private _radCold = [_coldC, _groundEps, _airTemp, 0.5, _groundTemp, 1, _airTemp, false] call _fnBand;
private _radHot = [_hotC, _groundEps, _airTemp, 0.5, _groundTemp, 1, _airTemp, false] call _fnBand;
private _probeRad = (_radCold + _radHot) / 2;
private _selTemps = createHashMap;
_selTemps set ["probe_obj|cold", _coldC];
_selTemps set ["probe_obj|hot", _hotC];
private _selEps = createHashMap;
missionNamespace setVariable ["aee_thermal_selTemperature", _selTemps];
missionNamespace setVariable ["aee_thermal_selEmissivity", _selEps];

// Reset the AGC state so the first pass is a true first publication. A state
// left by an earlier phase would hide the seed.
missionNamespace setVariable ["aee_thermal_agcLastT", -99];
missionNamespace setVariable ["aee_thermal_agcRadMin", -1];
missionNamespace setVariable ["aee_thermal_agcRadMax", -1];
missionNamespace setVariable ["aee_thermal_agcAcceptMin", -1];
missionNamespace setVariable ["aee_thermal_agcAcceptMax", -1];
missionNamespace setVariable ["aee_thermal_agcAtFloor", true];

// The first AGC pass. The throttle is forced by an old tick stamp. The IIR
// step uses the engine frame delta, so the probe reports that delta.
private _dt = diag_deltaTime;
missionNamespace setVariable ["aee_thermal_agcLastT", diag_tickTime - 1];
[] call _fnAGC;
private _firstMin = missionNamespace getVariable ["aee_thermal_agcRadMin", -1];
private _firstMax = missionNamespace getVariable ["aee_thermal_agcRadMax", -1];

// Drive the AGC to its fixed point. With constant inputs the IIR converges to
// the raw floor window, which is exactly what the pre-fix code published on
// the first pass. The convergence is the real SQF, not a mirror.
for "_i" from 1 to 300 do {
    missionNamespace setVariable ["aee_thermal_agcLastT", diag_tickTime - 1];
    [] call _fnAGC;
};
private _snapMin = missionNamespace getVariable ["aee_thermal_agcRadMin", -1];
private _snapMax = missionNamespace getVariable ["aee_thermal_agcRadMax", -1];

private _bFallback = [_probeRad, _fullMin, _fullMax] call _band;
private _bFirst = [_probeRad, _firstMin, _firstMax] call _band;
private _bSnap = [_probeRad, _snapMin, _snapMax] call _band;
private _firstJump = (abs (_bFirst - _bFallback)) * 255;
private _snapJump = (abs (_bSnap - _bFallback)) * 255;
private _floorSpan = _fullSpan / 8;

diag_log text format ["[P79] DIAG env air=%1 ground=%2 eps=%3 fullSpan=%4 floorSpan=%5 dt=%6",
    _airTemp toFixed 3, _groundTemp toFixed 3, _groundEps toFixed 3,
    _fullSpan toFixed 6, _floorSpan toFixed 6, _dt toFixed 6];
diag_log text format ["[P79] DIAG firstPass span=%1 min=%2 max=%3 | fixedPoint span=%4 min=%5 max=%6 | probeRad=%7",
    (_firstMax - _firstMin) toFixed 6, _firstMin toFixed 6, _firstMax toFixed 6,
    (_snapMax - _snapMin) toFixed 6, _snapMin toFixed 6, _snapMax toFixed 6, _probeRad toFixed 6];
diag_log text format ["[P79] DIAG band fallback=%1 first=%2 snap=%3 | snapJump=%4 levels firstJump=%5 levels",
    _bFallback toFixed 6, _bFirst toFixed 6, _bSnap toFixed 6,
    _snapJump toFixed 2, _firstJump toFixed 2];

private _STATED_JUMP_LEVELS = 20;
private _DEFECT_LEVELS = 30;

// The probe must have power. If the scene does not reproduce a large snap,
// the fix is not being tested and the result is inconclusive.
if (_snapJump > _DEFECT_LEVELS) then {
    diag_log text format ["[P79] [PASS] (1a) the pre-fix snap would jump %1 levels, so the defect is reproduced", _snapJump toFixed 1];
} else {
    diag_log text format ["[P79] [FAIL] (1a) the pre-fix snap jump is only %1 levels, too small to prove the fix", _snapJump toFixed 1];
    _fail = _fail + 1;
};

if ((_dt > 0) && {_firstJump <= _STATED_JUMP_LEVELS} && {_firstJump < (_snapJump / 2)}) then {
    diag_log text format ["[P79] [PASS] (1) no startup jump: the first AGC pass moved %1 levels (bound %2), against a %3-level snap",
        _firstJump toFixed 1, _STATED_JUMP_LEVELS, _snapJump toFixed 1];
} else {
    diag_log text format ["[P79] [FAIL] (1) the first AGC pass jumped %1 levels (bound %2, snap %3, dt %4)",
        _firstJump toFixed 1, _STATED_JUMP_LEVELS, _snapJump toFixed 1, _dt toFixed 6];
    _fail = _fail + 1;
};

// ── (2) stable when stable ────────────────────────────────────────────────
// The window is at its fixed point. With the inputs unchanged, repeated
// passes must not move the band. A move is one display level or more.
private _moves = 0;
private _prevB = _bSnap;
for "_i" from 1 to 20 do {
    missionNamespace setVariable ["aee_thermal_agcLastT", diag_tickTime - 1];
    [] call _fnAGC;
    private _lo = missionNamespace getVariable ["aee_thermal_agcRadMin", 0];
    private _hi = missionNamespace getVariable ["aee_thermal_agcRadMax", 1];
    private _b = [_probeRad, _lo, _hi] call _band;
    if ((abs (_b - _prevB)) * 255 >= 1) then { _moves = _moves + 1; };
    _prevB = _b;
};
if (_moves == 0) then {
    diag_log text "[P79] [PASS] (2) stable when stable: 0 band moves over 20 passes on a constant scene";
} else {
    diag_log text format ["[P79] [FAIL] (2) the settled band moved on %1 of 20 constant passes", _moves];
    _fail = _fail + 1;
};

// ── (2b) stable under a sub-band window swing ─────────────────────────────
// A client run (RPT 23:30:22) measured the SETTLED floor window breathing
// over 5 percent of its span (min 44.129..44.965, max 61.499..62.365 over the
// 17.37 span).  The old 1 percent band released on that swing and
// re-quantised every selection.  Translate the probe scene by the same 5
// percent of span and prove the band holds: the swing must not move b by
// more than _STATED_JITTER_LEVELS, and the accepted window itself must not
// move.  The translation is sized by the real band function, not guessed.
private _JITTER_FRAC = 0.05;
private _STATED_JITTER_LEVELS = 1;
private _jitterRads = _floorSpan * _JITTER_FRAC;
private _jitLo = 0;
private _jitHi = 50;
for "_i" from 1 to 50 do {
    private _tMid = (_jitLo + _jitHi) / 2;
    private _r = [_coldC + _tMid, _groundEps, _airTemp, 0.5, _groundTemp, 1, _airTemp, false] call _fnBand;
    if ((_r - _radCold) < _jitterRads) then { _jitLo = _tMid; } else { _jitHi = _tMid; };
};
private _jitterDT = (_jitLo + _jitHi) / 2;

private _accMin0 = missionNamespace getVariable ["aee_thermal_agcAcceptMin", 0];
private _accMax0 = missionNamespace getVariable ["aee_thermal_agcAcceptMax", 0];
private _jitterMoves = 0;
private _jitterPrevB = [_probeRad,
    (missionNamespace getVariable ["aee_thermal_agcRadMin", 0]),
    (missionNamespace getVariable ["aee_thermal_agcRadMax", 1])] call _band;
for "_i" from 1 to 20 do {
    private _shift = [0, _jitterDT] select ((_i mod 2) == 1);
    private _jMap = createHashMap;
    _jMap set ["probe_obj|cold", _coldC + _shift];
    _jMap set ["probe_obj|hot", _hotC + _shift];
    missionNamespace setVariable ["aee_thermal_selTemperature", _jMap];
    missionNamespace setVariable ["aee_thermal_agcLastT", diag_tickTime - 1];
    [] call _fnAGC;
    private _lo = missionNamespace getVariable ["aee_thermal_agcRadMin", 0];
    private _hi = missionNamespace getVariable ["aee_thermal_agcRadMax", 1];
    private _b = [_probeRad, _lo, _hi] call _band;
    if ((abs (_b - _jitterPrevB)) * 255 >= 1) then { _jitterMoves = _jitterMoves + 1; };
    _jitterPrevB = _b;
};
private _accMin1 = missionNamespace getVariable ["aee_thermal_agcAcceptMin", 0];
private _accMax1 = missionNamespace getVariable ["aee_thermal_agcAcceptMax", 0];
private _accHeld = (abs (_accMin1 - _accMin0) + abs (_accMax1 - _accMax0)) < (_floorSpan * 0.01);
diag_log text format ["[P79] DIAG jitter frac=%1 rads=%2 dT=%3 bandMoves=%4 acceptedHeld=%5",
    _JITTER_FRAC toFixed 3, _jitterRads toFixed 6, _jitterDT toFixed 6, _jitterMoves, _accHeld];
if ((_jitterMoves <= _STATED_JITTER_LEVELS) && _accHeld) then {
    diag_log text format ["[P79] [PASS] (2b) a %1 percent window swing moved b %2 level(s) (bound %3) and the accepted window held",
        (_JITTER_FRAC * 100) toFixed 0, _jitterMoves, _STATED_JITTER_LEVELS];
} else {
    diag_log text format ["[P79] [FAIL] (2b) a %1 percent window swing moved b %2 level(s) (bound %3), acceptedHeld=%4",
        (_JITTER_FRAC * 100) toFixed 0, _jitterMoves, _STATED_JITTER_LEVELS, _accHeld];
    _fail = _fail + 1;
};

// ── (2c) a genuine new scene still moves the band ─────────────────────────
// A sustained scene change far larger than the dead-band must release.  The
// window may hold jitter, never freeze the display.
private _REAL_FRAC = 0.40;
private _realDT = _jitterDT * (_REAL_FRAC / _JITTER_FRAC);
private _realMin0 = _accMin1;
private _bBefore = _jitterPrevB;
for "_i" from 1 to 100 do {
    private _rMap = createHashMap;
    _rMap set ["probe_obj|cold", _coldC + _realDT];
    _rMap set ["probe_obj|hot", _hotC + _realDT];
    missionNamespace setVariable ["aee_thermal_selTemperature", _rMap];
    missionNamespace setVariable ["aee_thermal_agcLastT", diag_tickTime - 1];
    [] call _fnAGC;
};
private _realMin1 = missionNamespace getVariable ["aee_thermal_agcAcceptMin", 0];
private _bAfter = [_probeRad,
    (missionNamespace getVariable ["aee_thermal_agcRadMin", 0]),
    (missionNamespace getVariable ["aee_thermal_agcRadMax", 1])] call _band;
private _realMoved = (abs (_bAfter - _bBefore)) * 255;
private _realDelta = abs (_realMin1 - _realMin0);
diag_log text format ["[P79] DIAG new scene frac=%1 dT=%2 acceptedDelta=%3 bMoved=%4 levels",
    _REAL_FRAC toFixed 3, _realDT toFixed 6, _realDelta toFixed 6, _realMoved toFixed 2];
if ((_realMoved > 5) && {_realDelta > (_floorSpan * _REAL_FRAC * 0.5)}) then {
    diag_log text format ["[P79] [PASS] (2c) a genuine new scene moved b %1 levels and released the window", _realMoved toFixed 1];
} else {
    diag_log text format ["[P79] [FAIL] (2c) a genuine new scene moved b %1 levels (acceptedDelta %2)",
        _realMoved toFixed 2, _realDelta toFixed 6];
    _fail = _fail + 1;
};

// ── (3) solver first sight ────────────────────────────────────────────────
// The real solver, called with the same arguments fnc_applySelectionThermal
// passes for an inert selection. The first-sight step is 1000000 s, which the
// caller selects when the state map holds no entry for the selection.
private _tAirS = 20.0;
private _tGroundS = 15.0;
private _tAirK = _tAirS + 273.15;
private _skyK = 0.0552 * (_tAirK ^ 1.5);
private _mrtS = (0.5 * ((_tGroundS + 273.15) ^ 4) + 0.5 * (_skyK ^ 4)) ^ 0.25 - 273.15;

private _solveInert = {
    params ["_t0", "_dtS"];
    [
        objNull, "", "metal", "metal",
        _tAirS, 0.0, 0.0, 1.0,
        50.0, 20.0, 6.0, 0.15,
        _t0, _t0, 0.0,
        "vertical", 0.5, _mrtS, false, 0.008, false, _dtS,
        0.0, -273, 0.0, 1.0, 0.0, 0.0
    ] call _fnSolve;
};

private _eqCold = ([0.0, 1000000] call _solveInert) select 1;
private _eqWarm = ([20.0, 1000000] call _solveInert) select 1;
private _transSkin = ([0.0, 5.0] call _solveInert) select 1;
private _seedDelta = abs (_eqCold - _eqWarm);

diag_log text format ["[P79] DIAG solver cold=%1 warm=%2 transient=%3 seedDelta=%4 (skin C)",
    _eqCold toFixed 4, _eqWarm toFixed 4, _transSkin toFixed 4, _seedDelta toFixed 4];

if ((_seedDelta < 0.05) && {_transSkin < _eqCold} && {_transSkin > 0}) then {
    diag_log text format ["[P79] [PASS] (3) solver first sight lands on equilibrium: cold %1 = warm %2 (delta %3), 5 s step %4",
        _eqCold toFixed 4, _eqWarm toFixed 4, _seedDelta toFixed 4, _transSkin toFixed 4];
} else {
    diag_log text format ["[P79] [FAIL] (3) solver first sight: cold %1 warm %2 delta %3 transient %4",
        _eqCold toFixed 4, _eqWarm toFixed 4, _seedDelta toFixed 4, _transSkin toFixed 4];
    _fail = _fail + 1;
};

// Remove the probe scene so no later phase reads it.
missionNamespace setVariable ["aee_thermal_selTemperature", nil];
missionNamespace setVariable ["aee_thermal_selEmissivity", nil];

if (_fail == 0) then {
    diag_log text format ["[P79] [PASS] thermal startup verified headlessly: first jump %1 levels (snap %2), 0 band moves, solver equilibrium %3 C",
        _firstJump toFixed 1, _snapJump toFixed 1, _eqCold toFixed 4];
} else {
    diag_log text format ["[P79] [FAIL] thermal startup: %1 check(s) failed", _fail];
};
