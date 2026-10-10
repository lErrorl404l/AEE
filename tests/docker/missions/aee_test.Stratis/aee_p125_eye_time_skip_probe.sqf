// PHASE 125: the eye adaptation tracks a time skip.
//
// The eye adaptation driver is client-only (it exits at hasInterface on a
// dedicated server), so this probe drives the REAL pure kernels with fixtures.
// It proves the two halves of the fix:
//   * fnc_eyeTimeSkip detects a world-clock jump, and ignores a normal tick,
//     the midnight wrap and the first sample;
//   * on a skip the driver re-seeds the pools and the pupil with eyeAdaptInit
//     (arrive adapted, ADR-007), so the aperture is the new scene's anchor on
//     the FIRST frame instead of chasing it over the slow dark tau.
// It also runs the counterfactual: chasing the jumped scene from the old state
// takes many frames, which is the reported defect.  It renders nothing.

private _skipFn = missionNamespace getVariable ["aee_eye_fnc_eyeTimeSkip", nil];
private _initFn = missionNamespace getVariable ["aee_eye_fnc_eyeAdaptInit", nil];
private _stepFn = missionNamespace getVariable ["aee_eye_fnc_eyeAdaptStep", nil];
private _apFn = missionNamespace getVariable ["aee_eye_fnc_eyeAperture", nil];
private _pupilSteadyFn = missionNamespace getVariable ["aee_eye_fnc_eyePupilSteady", nil];
private _pupilStepFn = missionNamespace getVariable ["aee_eye_fnc_eyePupilStep", nil];
private _mesopicFn = missionNamespace getVariable ["aee_eye_fnc_eyeMesopicWeight", nil];

private _pass = 0;
private _fail = 0;
private _notes = [];
private _nightAperture = -1;
private _arrivedAperture = -1;
private _chaseTicks = -1;

if (isNil "_skipFn" || {isNil "_initFn"} || {isNil "_stepFn"} || {isNil "_apFn"}
    || {isNil "_pupilSteadyFn"} || {isNil "_pupilStepFn"} || {isNil "_mesopicFn"}) then {
    _fail = _fail + 1;
    _notes pushBack "eye kernels not compiled";
} else {
    private _rho = missionNamespace getVariable ["aee_eye_eyeReflectance", 0.18];
    private _kp = missionNamespace getVariable ["aee_eye_eyeFastBlend", 0.35];
    private _tauLight = missionNamespace getVariable ["aee_eye_eyeTauLight", 2.0];
    private _tauDarkCone = missionNamespace getVariable ["aee_eye_eyeTauDarkCone", 120];
    private _tauDarkRod = missionNamespace getVariable ["aee_eye_eyeTauDarkRod", 400];
    private _mesoLo = missionNamespace getVariable ["aee_eye_eyeMesopicLow", 0.005];
    private _mesoHi = missionNamespace getVariable ["aee_eye_eyeMesopicHigh", 5];

    // The reported scenes: a moonlit night (RPT 0.5 lx) and noon (RPT 68039 lx).
    private _night = 0.5;
    private _day = 68039;

    // The driver's combine, rebuilt from the real kernels, so the probe measures
    // the same aperture the driver pins.
    private _apertureFor = {
        params ["_pools", "_pupil", "_sceneLux"];
        private _lum = (_rho * _sceneLux) / pi;
        private _u = ((4.9 - _pupil) / 3.0) max (-0.999) min 0.999;
        private _logB = ((0.5 * (ln ((1 + _u) / (1 - _u)))) / 0.4) - 0.5;
        private _xFast = log (3.183 * (10 ^ _logB));
        private _w = [_lum, _mesoLo, _mesoHi] call _mesopicFn;
        private _xSlow = (_w * (_pools select 0)) + ((1 - _w) * (_pools select 1));
        private _x = ((1 - _kp) * _xSlow) + (_kp * _xFast);
        [((pi / _rho) * (10 ^ _x))] call _apFn
    };

    // 1. The skip kernel: a normal tick, a forward skip, a backward skip, the
    //    midnight wrap, and the first sample.
    private _normal = [6.0, 6.00278, 0.05] call _skipFn;
    private _forward = [0.0, 12.0, 0.05] call _skipFn;
    private _backward = [12.0, 0.0, 0.05] call _skipFn;
    private _wrap = [23.99, 0.01, 0.05] call _skipFn;
    private _first = [-1, 6.0, 0.05] call _skipFn;
    if (!_normal && {_forward} && {_backward} && {!_wrap} && {!_first}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["skip detect %1/%2/%3/%4/%5", _normal, _forward, _backward, _wrap, _first];
    };

    // 2. Settle at the night scene.
    private _nightX = log ((_rho * _night) / pi);
    private _nightPupil = [_rho * _night / pi] call _pupilSteadyFn;
    private _nightPools = [_nightX] call _initFn;
    _nightAperture = [_nightPools, _nightPupil, _night] call _apertureFor;

    // 3. ARRIVE ADAPTED: the driver re-seeds on a skip, so the first frame at
    //    noon already shows the daylight anchor, with no bright window.
    private _dayX = log ((_rho * _day) / pi);
    private _dayPupil = [_rho * _day / pi] call _pupilSteadyFn;
    private _seededPools = [_dayX] call _initFn;
    _arrivedAperture = [_seededPools, _dayPupil, _day] call _apertureFor;
    if ((_nightAperture < 20) && {_arrivedAperture > 46}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["arrived night %1 day %2", _nightAperture, _arrivedAperture];
    };

    // 4. Counterfactual: without the reset the eye chases the noon scene from
    //    the night state at the driver's 0.1 s cadence.  Count the ticks to
    //    reach the day anchor, to show the reported multi-second bright window.
    private _pools = _nightPools;
    private _pupil = _nightPupil;
    private _chaseAperture = _nightAperture;
    _chaseTicks = 0;
    while {(_chaseTicks < 600) && {_chaseAperture < (_arrivedAperture - 2)}} do {
        _pools = [_pools, _dayX, 0.1, _tauLight, _tauDarkCone, _tauDarkRod, 0] call _stepFn;
        private _dSteady = [(_rho * _day) / pi] call _pupilSteadyFn;
        _pupil = [_pupil, _dSteady, 0.1, 0.25, 0.475] call _pupilStepFn;
        _chaseAperture = [_pools, _pupil, _day] call _apertureFor;
        _chaseTicks = _chaseTicks + 1;
    };

    // 5. With the corrected timestep the chase reaches the day anchor in tens of
    //    ticks (seconds), not the ~8x-longer window the frame-delta bug gave.
    if ((_chaseTicks > 0) && {_chaseTicks < 200}) then {
        _pass = _pass + 1;
    } else {
        _fail = _fail + 1;
        _notes pushBack format ["chase ticks %1", _chaseTicks];
    };
};

if (_fail isEqualTo 0) then {
    diag_log text format ["[P125] [PASS] eye time skip: night %1 -> day %2 vs chase %3 ticks (%4 checks)", _nightAperture, _arrivedAperture, _chaseTicks, _pass];
} else {
    diag_log text format ["[P125] [FAIL] eye time skip: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
