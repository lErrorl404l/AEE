// PHASE 99: the mode-2 thermal pass budget.
//
// The client sensor PFH runs [] call aee_thermal_fnc_updateThermalAGC before
// the per-selection paint.  The optics worker measured sensorPFH at a 20.4 ms
// mean in a live RPT, dominated by that AGC sweep (9.0 ms mean) plus the
// paint solves; the RPT had tracing ON, so every timing in it was inflated.
// The AGC now builds the scene histogram from a persistent radiance cache and
// refreshes a bounded slice each pass (a small fraction of a 16.7 ms frame),
// so a single pass no longer walks every solved selection.  This probe drives
// the REAL kernels headlessly with tracing OFF, the way PHASE 10 budgets the
// star catalog and P92 budgets the optics kernel.
//
// The client paint itself is gated on hasInterface and cannot run here, so the
// probe measures the pure kernels the paint solve drives: the two-node solver,
// the band-radiance kernel and the sensor-resolution kernels.  Warm-up plus
// best of three, with the ~0.6 ms/call SQF overhead the P92 evidence recorded.
//
// Emits [P99] PASS/FAIL lines.

missionNamespace setVariable ["aee_thermal_logDebug", false];
missionNamespace setVariable ["aee_core_logDebug", false];

private _fnAGC = missionNamespace getVariable ["aee_thermal_fnc_updateThermalAGC", nil];
private _fnBand = missionNamespace getVariable ["aee_thermal_fnc_calculateBandRadiance", nil];
private _fnSolve = missionNamespace getVariable ["aee_thermal_fnc_solveTwoNodeSelection", nil];
private _fnThreshold = missionNamespace getVariable ["aee_thermal_fnc_calculateSensorThreshold", nil];
private _fnEdge = missionNamespace getVariable ["aee_thermal_fnc_evaluateThermalEdge", nil];
private _fnTarget = missionNamespace getVariable ["aee_thermal_fnc_resolveThermalTarget", nil];
private _fnVis = missionNamespace getVariable ["aee_thermal_fnc_resolveThermalVisibility", nil];
private _fnNoise = missionNamespace getVariable ["aee_thermal_fnc_calculateThermalNoise", nil];

if (isNil "_fnAGC" || {isNil "_fnBand"} || {isNil "_fnSolve"}
    || {isNil "_fnThreshold"} || {isNil "_fnEdge"} || {isNil "_fnTarget"}
    || {isNil "_fnVis"} || {isNil "_fnNoise"}) exitWith {
    diag_log text "[P99] [FAIL] thermal pass kernels not compiled (agc/band/solve/sensor)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// ── Seed a representative scene: 40 selections over 8 objects ─────────────
// One AGC sweep over this set is the un-amortised cost; the budgeted pass
// refreshes only a slice.  Fixed values keep the measurement deterministic.
private _selections = 40;
private _selMap = createHashMap;
private _epsMap = createHashMap;
for "_i" from 0 to (_selections - 1) do {
    private _key = format ["obj_%1|sel_%2", floor (_i / 5), _i];
    _selMap set [_key, 15 + (_i mod 40)];
    _epsMap set [_key, 0.2 + 0.02 * (_i mod 30)];
};

// The un-amortised cost: one band-radiance call per solved selection, which
// is what the AGC pass did before the budget.  Best of three.
private _fullWork = {
    private _t = 15;
    private _e = 0.5;
    for "_i" from 0 to 39 do {
        [_t + _i, _e, 15, 0.5, 15, 1, 15, false] call _fnBand;
    };
};
[] call _fullWork;
private _fullBest = 1e9;
for "_r" from 1 to 3 do {
    private _t0 = diag_tickTime;
    [] call _fullWork;
    private _ms = (diag_tickTime - _t0) * 1000;
    if (_ms < _fullBest) then { _fullBest = _ms; };
};

// The budgeted AGC pass: reset the throttle and the cache, call once, time it.
private _agcWork = {
    missionNamespace setVariable ["aee_thermal_agcLastT", diag_tickTime - 1];
    [] call _fnAGC;
};
missionNamespace setVariable ["aee_thermal_selTemperature", _selMap];
missionNamespace setVariable ["aee_thermal_selEmissivity", _epsMap];
missionNamespace setVariable ["aee_thermal_agcSelRad", createHashMap];
missionNamespace setVariable ["aee_thermal_agcSceneAnchor", []];
// The cold pass is the un-amortised first pass (empty cache): it recomputes
// up to the per-pass cap.  The warm passes are the steady state the runtime
// reaches after the first tick, when every held radiance is reused.
private _coldT0 = diag_tickTime;
[] call _agcWork;
private _coldMs = (diag_tickTime - _coldT0) * 1000;
[] call _agcWork;   // fill the remainder of the cache
[] call _agcWork;   // settle
[] call _agcWork;   // settle
private _passBest = 1e9;
for "_r" from 1 to 3 do {
    private _t0 = diag_tickTime;
    [] call _agcWork;
    private _ms = (diag_tickTime - _t0) * 1000;
    if (_ms < _passBest) then { _passBest = _ms; };
};

// 1. The steady-state pass is cheaper than the un-amortised sweep, and stays
//    a small fraction of a frame.  The comparative check proves the caching
//    on any host speed; the absolute cap catches a regression that drops it
//    (the full sweep is about 24 ms of call overhead alone).
if ((_passBest < _fullBest) && {_passBest < 15}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["AGC pass %1 ms vs full %2 ms for %3 selections", _passBest, _fullBest, _selections];
};

// 2. The sweep converges: after enough passes every selection is cached and
//    the published window is valid.  This proves the cursor does not starve
//    and the budget still reaches the whole scene.
for "_i" from 1 to 400 do {
    missionNamespace setVariable ["aee_thermal_agcLastT", diag_tickTime - 1];
    [] call _fnAGC;
};
private _cache = missionNamespace getVariable ["aee_thermal_agcSelRad", createHashMap];
private _radMin = missionNamespace getVariable ["aee_thermal_agcRadMin", -1];
private _radMax = missionNamespace getVariable ["aee_thermal_agcRadMax", -1];
if ((count _cache >= _selections)
    && {(_radMin isEqualType 0) && {(_radMax isEqualType 0) && {_radMax > _radMin}}}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["sweep did not converge: cache %1/%2 window %3..%4", count _cache, _selections, _radMin, _radMax];
};

// 3. Paint-solve kernel: the two-node solver is the per-selection cost the
//    paint drives.  20 calls, best of three.
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
if (_solveBest < 100) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["two-node solve %1 ms for 20 calls", _solveBest];
};

// 4. Band-radiance kernel: 20 calls, best of three.
private _bandWork = {
    for "_i" from 1 to 20 do {
        [37, 0.92, 15, 0.5, 15, 1, 15, false] call _fnBand;
    };
};
[] call _bandWork;
private _bandBest = 1e9;
for "_r" from 1 to 3 do {
    private _t0 = diag_tickTime;
    [] call _bandWork;
    private _ms = (diag_tickTime - _t0) * 1000;
    if (_ms < _bandBest) then { _bandBest = _ms; };
};
// The band-radiance kernel runs the Planck sky bisection, so it is the one
// kernel here that costs real time (~6.5 ms per call on the dedicated
// server).  The bound is generous: it catches an accidental per-call engine
// read, not the host speed.
if (_bandBest < 250) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["band radiance %1 ms for 20 calls", _bandBest];
};

// 5. Sensor-resolution kernels: the five pure kernels the paint calls per
//    selection, 20 iterations each, best of three.
private _sensorWork = {
    for "_i" from 1 to 20 do {
        [0.05, 5, 15] call _fnThreshold;
        [0.1, 0.05, 0.004349, 0] call _fnEdge;
        [0.02, 640, 1, 0, 0.05, 0.3, 15] call _fnTarget;
        [0.3, 0.004349, true, 1] call _fnVis;
        [0.05, 1000, 640, 50] call _fnNoise;
    };
};
[] call _sensorWork;
private _sensorBest = 1e9;
for "_r" from 1 to 3 do {
    private _t0 = diag_tickTime;
    [] call _sensorWork;
    private _ms = (diag_tickTime - _t0) * 1000;
    if (_ms < _sensorBest) then { _sensorBest = _ms; };
};
if (_sensorBest < 150) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["sensor kernels %1 ms for 100 calls", _sensorBest];
};

// Leave no synthetic scene state behind for any later tick.
missionNamespace setVariable ["aee_thermal_selTemperature", createHashMap];
missionNamespace setVariable ["aee_thermal_selEmissivity", createHashMap];
missionNamespace setVariable ["aee_thermal_agcSelRad", createHashMap];

diag_log text format ["[P99] scene sweep: full %1 ms for %2 selections, cold pass %3 ms, steady pass %4 ms", _fullBest, _selections, _coldMs, _passBest];
diag_log text format ["[P99] kernels: two-node %1 ms/20, band %2 ms/20, sensor %3 ms/100", _solveBest, _bandBest, _sensorBest];

if (_fail == 0) then {
    diag_log text format ["[P99] [PASS] thermal pass budget: amortised AGC and paint kernels (%1 checks)", _pass];
} else {
    diag_log text format ["[P99] [FAIL] thermal pass budget: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
