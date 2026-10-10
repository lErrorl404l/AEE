// PHASE 80: the fusion pipeline, exercised on a headless server.
//
// WHY THIS EXISTS. The fusion overlay paints a physics-graded emissive
// rvmat over the native NVG frame. The final render cannot be proven on a
// server: there is no camera and no display, so the image is a client-only
// fact (the operator gate, plan Todo 2). Everything BELOW the render is
// SQF and carries no hasInterface gate, so this probe drives the REAL
// kernels directly and does not fake the result.
//
// WHAT IS PROVEN HEADLESSLY:
//   (1) the 256-level ladder: fnc_fusionBandIndex maps 0..1 to band 0..255
//       monotonically, and fnc_fusionMaterialPaths returns the 256 files in
//       index order, so band 0 selects the darkest file and 255 the brightest.
//   (2) the thermal-channel field gate: fnc_fusionFovGate accepts a target
//       inside the half-angle and refuses one beyond it.
//   (3) restore symmetry: fnc_applyFusionOverlay with mode "EXIT" returns
//       every saved material index and leaves the saved store empty.
//   (4) the mode cycle: fnc_cycleFusionMode toggles 0 <-> 1, the default is
//       I2-only (0), and a forced value clamps.
//   (5) state freshness: the real AGC kernel (aee_thermal_fnc_updateThermalAGC)
//       produces a valid window from seeded selection state, and the real
//       two-node solver is seed-independent at the first-sight step. No
//       player and no hasInterface are involved.
//
// WHAT STILL NEEDS A CLIENT RUN: the rendered image. Todo 2.
//
// Bounded and deterministic: fixed ladders, one restore, one cycle, a fixed
// AGC settle loop, two solver calls. Emits [P80] PASS/FAIL lines.

private _fnBandIdx = missionNamespace getVariable ["aee_thermal_display_fnc_fusionBandIndex", nil];
private _fnPaths = missionNamespace getVariable ["aee_thermal_display_fnc_fusionMaterialPaths", nil];
private _fnFov = missionNamespace getVariable ["aee_thermal_display_fnc_fusionFovGate", nil];
private _fnOverlay = missionNamespace getVariable ["aee_thermal_display_fnc_applyFusionOverlay", nil];
private _fnCycle = missionNamespace getVariable ["aee_thermal_display_fnc_cycleFusionMode", nil];
private _fnAGC = missionNamespace getVariable ["aee_thermal_fnc_updateThermalAGC", nil];
private _fnSolve = missionNamespace getVariable ["aee_thermal_fnc_solveTwoNodeSelection", nil];
private _fnBand = missionNamespace getVariable ["aee_thermal_fnc_calculateBandRadiance", nil];
private _fnFrameGeo = missionNamespace getVariable ["aee_thermal_display_fnc_fusionFrameGeometry", nil];

if (isNil "_fnBandIdx" || {isNil "_fnPaths"} || {isNil "_fnFov"}
    || {isNil "_fnOverlay"} || {isNil "_fnCycle"} || {isNil "_fnAGC"}
    || {isNil "_fnSolve"} || {isNil "_fnBand"} || {isNil "_fnFrameGeo"}) exitWith {
    diag_log text "[P80] [FAIL] fusion kernel functions not compiled (band/paths/fov/overlay/cycle/agc/solve/radiance/frame)";
};

private _fail = 0;

// ── (1) the 256-level ladder ──────────────────────────────────────────────
// Non-decreasing over the range, with the endpoints pinned, and the file
// list in index order. Monotonicity of the emitted brightness is the
// generator's contract (emissive = band/255 * 500) and is asserted by the
// material generator check; this probe asserts the index mapping that
// selects the file.
private _samples = [0, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 1];
private _prev = -1;
private _mono = true;
private _distinct = 0;
{
    private _band = [_x] call _fnBandIdx;
    if (_band < _prev) then { _mono = false; };
    if (_band != _prev) then { _distinct = _distinct + 1; };
    _prev = _band;
} forEach _samples;
private _bandLo = [0] call _fnBandIdx;
private _bandHi = [1] call _fnBandIdx;
private _bandOver = [2] call _fnBandIdx;
private _bandUnder = [-1] call _fnBandIdx;
if (_mono && {_bandLo == 0} && {_bandHi == 255} && {_bandOver == 255} && {_bandUnder == 0}) then {
    diag_log text format ["[P80] [PASS] (1a) ladder index: monotonic, 0 -> %1, 1 -> %2, clamped, %3 distinct of %4",
        _bandLo, _bandHi, _distinct, count _samples];
} else {
    diag_log text format ["[P80] [FAIL] (1a) ladder index: mono=%1 lo=%2 hi=%3 over=%4 under=%5",
        _mono, _bandLo, _bandHi, _bandOver, _bandUnder];
    _fail = _fail + 1;
};

private _paths = [] call _fnPaths;
private _pathsOk = (count _paths == 256);
if (_pathsOk) then {
    if ((_paths select 0) find "fusion_emissive_000" < 0) then { _pathsOk = false; };
    if ((_paths select 255) find "fusion_emissive_255" < 0) then { _pathsOk = false; };
    {
        private _n = str _forEachIndex;
        while { count _n < 3 } do { _n = "0" + _n; };
        if ((_x find ("fusion_emissive_" + _n)) < 0) then { _pathsOk = false; };
    } forEach _paths;
};
if (_pathsOk) then {
    diag_log text format ["[P80] [PASS] (1b) ladder files: %1 ordered paths, index 0 -> %2", count _paths, _paths select 0];
} else {
    diag_log text format ["[P80] [FAIL] (1b) ladder files: count=%1 first=%2 last=%3",
        count _paths, _paths param [0, "<none>"], _paths param [count _paths - 1, "<none>"]];
    _fail = _fail + 1;
};

// ── (2) the thermal-channel field gate ────────────────────────────────────
// View axis is +Y. A target at 17 degrees is inside a 20-degree half-angle,
// one at 30 degrees is outside, and one exactly on the bound is accepted.
private _eye = [0, 0, 0];
private _viewDir = [0, 1, 0];
private _d = 100;
// Offsets are the direction cosines of 10, 35 and 20 degrees, written as
// literals so the probe does not depend on the trig convention of the
// interpreter. A position at 10 degrees from +Y is inside a 20-degree
// half-angle; 35 degrees is outside; 20 degrees is exactly on the bound.
private _inside = [_eye, _viewDir, [_d * 0.173648, _d * 0.984808, 0], 20] call _fnFov;
private _outside = [_eye, _viewDir, [_d * 0.573576, _d * 0.819152, 0], 20] call _fnFov;
private _edge = [_eye, _viewDir, [_d * 0.342020, _d * 0.939693, 0], 20] call _fnFov;
private _behind = [_eye, _viewDir, [0, -_d, 0], 20] call _fnFov;
if (_inside && {!_outside} && {_edge} && {!_behind}) then {
    diag_log text "[P80] [PASS] (2) FOV gate: 10 deg accepted, 35 deg refused, 20 deg edge accepted, behind refused";
} else {
    diag_log text format ["[P80] [FAIL] (2) FOV gate: inside10=%1 outside35=%2 edge20=%3 behind=%4",
        _inside, _outside, _edge, _behind];
    _fail = _fail + 1;
};

// ── (3) restore symmetry on EXIT ──────────────────────────────────────────
// The overlay saves each object's own materials before the first swap. The
// restore must put every index back and empty the store. A real object is
// used so the engine call runs: a swept store would not prove the restore.
private _obj = createVehicle ["C_Hatchback_01_F", [4400, 4400, 0], [], 0, "NONE"];
_obj enableSimulation false;
private _before = getObjectMaterials _obj;
private _slots = count _before;
if (_slots > 0 && {_pathsOk}) then {
    for "_i" from 0 to (_slots - 1) do {
        _obj setObjectMaterial [_i, _paths select 0];
    };
};
missionNamespace setVariable ["aee_thermal_display_fusionOverlaySaved", [[_obj, _before]]];
[objNull, "EXIT"] call _fnOverlay;
private _after = getObjectMaterials _obj;
private _store = missionNamespace getVariable ["aee_thermal_display_fusionOverlaySaved", []];
private _restored = (_after isEqualTo _before);
private _storeEmpty = (_store isEqualTo []);
deleteVehicle _obj;
if ((_slots > 0) && _restored && _storeEmpty) then {
    diag_log text format ["[P80] [PASS] (3) EXIT restore: %1 material slots returned, saved store empty", _slots];
} else {
    diag_log text format ["[P80] [FAIL] (3) EXIT restore: slots=%1 restored=%2 storeEmpty=%3",
        _slots, _restored, _storeEmpty];
    _fail = _fail + 1;
};

// ── (4) the mode cycle ────────────────────────────────────────────────────
// Default I2-only (0); force 1; toggle back to 0; a forced 5 clamps to 1.
private _mDefault = missionNamespace getVariable ["aee_thermal_display_fusionMode", 0];
[1] call _fnCycle;
private _mForced1 = missionNamespace getVariable ["aee_thermal_display_fusionMode", -99];
[] call _fnCycle;
private _mToggled = missionNamespace getVariable ["aee_thermal_display_fusionMode", -99];
[5] call _fnCycle;
private _mClamped = missionNamespace getVariable ["aee_thermal_display_fusionMode", -99];
[0] call _fnCycle;
private _mReset = missionNamespace getVariable ["aee_thermal_display_fusionMode", -99];
if (_mDefault == 0 && {_mForced1 == 1} && {_mToggled == 0} && {_mClamped == 1} && {_mReset == 0}) then {
    diag_log text "[P80] [PASS] (4) mode cycle: default 0, force 1, toggle 0, forced 5 clamps to 1";
} else {
    diag_log text format ["[P80] [FAIL] (4) mode cycle: default=%1 force1=%2 toggle=%3 clamp=%4 reset=%5",
        _mDefault, _mForced1, _mToggled, _mClamped, _mReset];
    _fail = _fail + 1;
};

// ── (5) state freshness through the real kernels ──────────────────────────
// Seed the selection state directly: the paint caller
// (fnc_applySelectionThermal) is hasInterface-gated, so a server cannot run
// it, but the AGC and solver kernels carry no gate. Drive the AGC to a
// valid window, then map the hot selection's radiance to a band.
private _selMap = createHashMap;
_selMap set ["p80_obj|cold", 11];
_selMap set ["p80_obj|hot", 31];
missionNamespace setVariable ["aee_thermal_selTemperature", _selMap];
missionNamespace setVariable ["aee_thermal_agcLastT", -99];
missionNamespace setVariable ["aee_thermal_agcRadMin", -1];
missionNamespace setVariable ["aee_thermal_agcRadMax", -1];
missionNamespace setVariable ["aee_thermal_agcAcceptMin", -1];
missionNamespace setVariable ["aee_thermal_agcAcceptMax", -1];
missionNamespace setVariable ["aee_thermal_agcAtFloor", true];
for "_i" from 1 to 60 do {
    missionNamespace setVariable ["aee_thermal_agcLastT", diag_tickTime - 1];
    [] call _fnAGC;
};
private _agcLo = missionNamespace getVariable ["aee_thermal_agcRadMin", -1];
private _agcHi = missionNamespace getVariable ["aee_thermal_agcRadMax", -1];
private _windowOk = (_agcLo isEqualType 0) && {(_agcHi isEqualType 0)} && {_agcHi > _agcLo};
private _airTemp = missionNamespace getVariable ["aee_core_currentTemperature", 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _radHot = [31, 0.92, _airTemp, 0.5, _airTemp, 1, _airTemp, false] call _fnBand;
private _bHot = if (_windowOk) then { ((_radHot - _agcLo) / (_agcHi - _agcLo)) max 0 min 1 } else { 0 };
private _bandHot = [_bHot] call _fnBandIdx;

// The real solver, called with the same 28 arguments the paint path passes
// for an inert selection. The first-sight step is 1000000 s, which the
// caller selects when the state map holds no entry: the result must be
// independent of the seed, or the display would depend on spawn order.
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
private _solverOk = (finite _eqCold) && {finite _eqWarm} && {abs (_eqCold - _eqWarm) < 0.05};

if (_windowOk && {_bandHot > 0}) then {
    diag_log text format ["[P80] [PASS] (5a) fresh AGC: window %1..%2, hot selection band %3 (no player)",
        _agcLo toFixed 6, _agcHi toFixed 6, _bandHot];
} else {
    diag_log text format ["[P80] [FAIL] (5a) fresh AGC: windowOk=%1 lo=%2 hi=%3 band=%4",
        _windowOk, _agcLo, _agcHi, _bandHot];
    _fail = _fail + 1;
};
if (_solverOk) then {
    diag_log text format ["[P80] [PASS] (5b) solver first sight: seed-independent equilibrium %1 = %2",
        _eqCold toFixed 4, _eqWarm toFixed 4];
} else {
    diag_log text format ["[P80] [FAIL] (5b) solver first sight: cold=%1 warm=%2",
        _eqCold toFixed 4, _eqWarm toFixed 4];
    _fail = _fail + 1;
};

// ── (6) the field-of-view frame geometry ──────────────────────────────────
// The frame half-extent is tan(thermalHalfAngle) / tan(nvgFieldHalf), so it
// is DERIVED from the resolved half-angle and is not a fixed 20. The ENVG-B
// sits at the field edge (ratio 1), the narrower channels sit inside it, and
// a thermal field wider than the tube is clamped.
private _geoEcoti = [15, 40] call _fnFrameGeo;
private _geoBnvd = [17, 40] call _fnFrameGeo;
private _geoEnvg = [20, 40] call _fnFrameGeo;
private _geoZero = [0, 40] call _fnFrameGeo;
private _geoClamp = [45, 40] call _fnFrameGeo;
private _geoWide = [20, 80] call _fnFrameGeo;
private _geoOk = (_geoEcoti > 0)
    && (_geoEcoti < _geoBnvd) && (_geoBnvd < _geoEnvg)
    && (abs (_geoEnvg - 1) < 0.0001)
    && (_geoZero < 0.0001)
    && (abs (_geoClamp - 1) < 0.0001)
    && (_geoWide < _geoEnvg)
    && (abs (_geoEcoti - _geoEnvg) > 0.1);
if (_geoOk) then {
    diag_log text format ["[P80] [PASS] (6) frame geometry: ECOTI %1 < BNVD %2 < ENVG %3, clamped at the field edge",
        _geoEcoti toFixed 4, _geoBnvd toFixed 4, _geoEnvg toFixed 4];
} else {
    diag_log text format ["[P80] [FAIL] (6) frame geometry: ecoti=%1 bnvd=%2 envg=%3 zero=%4 clamp=%5 wide=%6",
        _geoEcoti toFixed 4, _geoBnvd toFixed 4, _geoEnvg toFixed 4,
        _geoZero toFixed 4, _geoClamp toFixed 4, _geoWide toFixed 4];
    _fail = _fail + 1;
};

// ── verdict ───────────────────────────────────────────────────────────────
if (_fail == 0) then {
    diag_log text "[P80] [PASS] fusion pipeline: ladder, FOV gate, EXIT restore, mode cycle, fresh kernels, frame geometry";
} else {
    diag_log text format ["[P80] [FAIL] %1 fusion assertion(s) failed", _fail];
};
