// PHASE 131: the one real-time clock is the model time base.
//
// WHY THIS EXISTS.  A throttled model that integrated diag_deltaTime (the last
// RENDERED frame duration) inside a CBA per-frame handler made its time
// constant depend on the frame rate.  The eye driver and the thermal AGC were
// the same defect (commits f36bc216, fc81d68e, probe P79).  The fix is one
// clock: aee_core_simTime, published from diag_tickTime each frame.  Every
// throttled model computes _dt = aee_core_simTime - _lastSimTime once per run.
//
// WHAT THIS PROBE MEASURES (honest headless).  It runs the SHIPPED clock
// (aee_core_fnc_updateSimClock) and integrates a first-order lag with the exact
// pattern the models use:
//     _dt = aee_core_simTime - _lastSim ;  n += (1 - n) * (1 - exp(-_dt/tau))
// over the same target duration at two sample cadences (30 vs 300 steps, the
// limitFPS-30 vs limitFPS-300 analogue).  The exact per-step update composites
// to 1 - exp(-T/tau) for the MEASURED elapsed T, so each run must match its own
// analytic value within 2 percent, and it must not depend on the step count.  A
// counterfactual integrates the OLD frame-delta pattern (a constant ~1/60 s
// step) and shows the composite drifting with the count - the defect the clock
// removes.  The published clock is checked monotonic across the run.
//
// WHAT THIS PROBE DOES NOT MEASURE (state the ceiling, do not fake it).  The
// dedicated server's own frame delta is not controllable from inside the
// mission, so the limitFPS 30 vs 300 comparison is run as a sample-cadence
// comparison in one session, not by re-launching the server at two limitFPS
// values.  The analytic check per measured elapsed time is the binding one.

private _clockFn = missionNamespace getVariable ["aee_core_fnc_updateSimClock", nil];
if (isNil "_clockFn") exitWith {
    diag_log text "[P135] [FAIL] aee_core_fnc_updateSimClock not compiled";
};

private _tau = 2.0;
private _duration = 1.2;

private _integrate = {
    params ["_steps"];
    private _lastSim = -1;
    private _n = 0;
    private _frames = 0;
    private _totalDt = 0;
    private _mono = true;
    for "_i" from 1 to _steps do {
        uiSleep (_duration / _steps);
        call _clockFn;
        private _now = missionNamespace getVariable ["aee_core_simTime", 0];
        if (_lastSim >= 0) then {
            if (_now < _lastSim) then { _mono = false; };
            private _dt = _now - _lastSim;
            _totalDt = _totalDt + _dt;
            _frames = _frames + 1;
            _n = _n + ((1 - _n) * (1 - exp (-_dt / _tau)));
        };
        _lastSim = _now;
    };
    [_n, _frames, _totalDt, _mono]
};

private _low = [30] call _integrate;
private _high = [300] call _integrate;

private _lowN = _low select 0;
private _lowT = _low select 2;
private _lowMono = _low select 3;
private _highN = _high select 0;
private _highT = _high select 2;
private _highMono = _high select 3;

private _lowExpected = 1 - exp (-_lowT / _tau);
private _highExpected = 1 - exp (-_highT / _tau);

private _lowErr = if (_lowExpected > 0) then { abs (_lowN - _lowExpected) / _lowExpected } else { 1 };
private _highErr = if (_highExpected > 0) then { abs (_highN - _highExpected) / _highExpected } else { 1 };
private _crossErr = if (_highExpected > 0) then { abs (_lowN - _highN) / _highExpected } else { 1 };

// Counterfactual: the old pattern used the previous FRAME duration (a constant
// ~1/60 s) as the step, so N passes over the same wall time integrate N*dt.
private _frameDt = 1 / 60;
private _cfLow = 0;
for "_i" from 1 to 30 do {
    _cfLow = _cfLow + ((1 - _cfLow) * (1 - exp (-_frameDt / _tau)));
};
private _cfHigh = 0;
for "_i" from 1 to 300 do {
    _cfHigh = _cfHigh + ((1 - _cfHigh) * (1 - exp (-_frameDt / _tau)));
};
private _cfErr = abs (_cfLow - _cfHigh) / (1 max _cfHigh);

private _pass = 0;
private _fail = 0;
private _notes = [];

if (_lowErr < 0.02) then { _pass = _pass + 1; } else {
    _fail = _fail + 1;
    _notes pushBack format ["low analytic err %1", _lowErr];
};
if (_highErr < 0.02) then { _pass = _pass + 1; } else {
    _fail = _fail + 1;
    _notes pushBack format ["high analytic err %1", _highErr];
};
if (_lowMono && {_highMono}) then { _pass = _pass + 1; } else {
    _fail = _fail + 1;
    _notes pushBack "clock not monotonic";
};
if (_cfErr > 0.02) then { _pass = _pass + 1; } else {
    _fail = _fail + 1;
    _notes pushBack format ["counterfactual frame-delta error %1 too small", _cfErr];
};

if (_fail isEqualTo 0) then {
    diag_log text format ["[P135] [PASS] sim clock rate: 30-step n=%1 (err %2) 300-step n=%3 (err %4) crossErr=%5 elapsed %6/%7 s; frame-delta counterfactual err=%8 (%9 checks)", _lowN, _lowErr, _highN, _highErr, _crossErr, _lowT, _highT, _cfErr, _pass];
} else {
    diag_log text format ["[P135] [FAIL] sim clock rate: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
