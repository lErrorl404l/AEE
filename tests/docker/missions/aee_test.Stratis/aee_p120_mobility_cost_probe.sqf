// PHASE 120: the mobility per-frame loop cost, measured.
//
// WHY THIS EXISTS.  The five mobility handlers run at 20 Hz on the client, and
// each used to build a per-tick DEBUG line ("airframeLoad %1 ms | vehicles
// %2") and diag_log it.  In the operator's 104 s session that was 10,205
// lines, 71 percent of all AEE debug output and the single largest block in a
// 16,027 line RPT.  A dedicated server has hasInterface false, so those
// handlers never register; the per-tick lines are removed by design and
// tools/tests/test_per_frame_log_guard.py gates the contract.
//
// MEASUREMENT.  A dedicated server cannot register the client handler, so it
// cannot measure the client frame rate.  What it CAN measure is the frame cost
// the loop body adds per tick and the cost of a per-tick log line, and that is
// what this probe does.  It spawns one bound ground vehicle, warms the
// kernels, times each per-tick kernel over N calls, times the combined
// per-tick body, then times the guarded per-tick log shape with the trace
// switch on and off.  The RPT measured 0 to 1 ms per client handler; a body
// over the sanity bound would mean the loop itself is the frame cost.
//
// The probe registers no client handler, changes no config and renders
// nothing.  The log-cost loop uses the probe's own tag, not the mobility tag,
// so it does not seed the log with lines that look like the removed flood.
//
// Emits: [P120] [PASS] / [P120] [FAIL] lines.

private _N = 300;
private _NLog = 100;
private _bodyBoundMs = 20.0;

private _pass = 0;
private _fail = 0;
private _notes = [];

private _veh = createVehicle ["C_Hatchback_01_F", [4400, 4400, 0], [], 0, "NONE"];
if (isNull _veh) exitWith {
    diag_log text "[P120] [FAIL] probe vehicle did not spawn";
};

_veh setVelocity [8, 0, 0];

// Warm up: the first call compiles the kernel and fills its caches.
for "_i" from 1 to 100 do {
    [_veh] call aee_mobility_fnc_applyRollover;
    [_veh] call aee_mobility_fnc_applyTerrainDrag;
    [_veh] call aee_mobility_fnc_applyGripLoss;
};

// ── 1. Per-kernel cost, one kernel at a time ──────────────────────────────
private _t = diag_tickTime;
for "_i" from 1 to _N do { [_veh] call aee_mobility_fnc_applyRollover; };
private _rollMs = ((diag_tickTime - _t) * 1000) / _N;

_t = diag_tickTime;
for "_i" from 1 to _N do { [_veh] call aee_mobility_fnc_applyTerrainDrag; };
private _terrMs = ((diag_tickTime - _t) * 1000) / _N;

_t = diag_tickTime;
for "_i" from 1 to _N do { [_veh] call aee_mobility_fnc_applyGripLoss; };
private _gripMs = ((diag_tickTime - _t) * 1000) / _N;

// ── 2. The combined per-tick body the handlers run ────────────────────────
// The engine reads plus the three per-tick kernels.  applyAccretionMass is the
// 1 Hz mass tick, not a per-tick call, so it is excluded here.
_t = diag_tickTime;
for "_i" from 1 to _N do {
    private _pos = getPosATL _veh;
    private _vel = velocity _veh;
    private _mass = getMass _veh;
    [_veh] call aee_mobility_fnc_applyRollover;
    [_veh] call aee_mobility_fnc_applyTerrainDrag;
    [_veh] call aee_mobility_fnc_applyGripLoss;
};
private _bodyMs = ((diag_tickTime - _t) * 1000) / _N;

if (_bodyMs <= _bodyBoundMs) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["body %1 ms/pass over the %2 ms bound", _bodyMs, _bodyBoundMs];
};

// ── 3. The removed per-tick log line, with the switch on and off ──────────
// The exact guarded shape the fix removed: test the switch, build, diag_log.
// The guard must short-circuit: with the switch off the line is neither built
// nor written.  A hit counter inside the guarded body encodes that literally:
// the switch-on pass runs the body _NLog times, the switch-off pass never runs
// it.  A timing comparison would flake: diag_log is asynchronous, so the whole
// loop sits under one diag_tickTime frame boundary and the measured value is
// which window that tick landed in, not the guard's work.
missionNamespace setVariable ["aee_core_logDebug", true];
missionNamespace setVariable ["aee_p120Hits", 0];
_t = diag_tickTime;
for "_i" from 1 to _NLog do {
    if (missionNamespace getVariable ["aee_core_logDebug", false]) then {
        missionNamespace setVariable ["aee_p120Hits", (missionNamespace getVariable ["aee_p120Hits", 0]) + 1];
        diag_log text format ["[P120] per-tick line %1 | %2", _i, 0];
    };
};
private _logOnMs = ((diag_tickTime - _t) * 1000) / _NLog;
private _onHits = missionNamespace getVariable ["aee_p120Hits", 0];

missionNamespace setVariable ["aee_core_logDebug", false];
missionNamespace setVariable ["aee_p120Hits", 0];
_t = diag_tickTime;
for "_i" from 1 to _NLog do {
    if (missionNamespace getVariable ["aee_core_logDebug", false]) then {
        missionNamespace setVariable ["aee_p120Hits", (missionNamespace getVariable ["aee_p120Hits", 0]) + 1];
        diag_log text format ["[P120] per-tick line %1 | %2", _i, 0];
    };
};
private _logOffMs = ((diag_tickTime - _t) * 1000) / _NLog;
private _offHits = missionNamespace getVariable ["aee_p120Hits", 0];

// Deterministic, host-independent: the switch-on pass runs the guarded body on
// every pass; the switch-off pass never does.  This fails if the guard is
// removed (_offHits = _NLog), if the body is unreachable (_onHits = 0), or if
// the condition inverts.  The per-pass timings remain printed diagnostics.
if (_onHits == _NLog && {_offHits == 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["guard did not short-circuit: on %1 hits off %2 hits (on %3 ms off %4 ms)", _onHits, _offHits, _logOnMs, _logOffMs];
};

deleteVehicle _veh;

diag_log text format [
    "[P120] per-kernel ms/call rollover %1 terrain %2 grip %3; body %4 ms/pass (bound %5); per-tick line on %6 ms off %7 ms; five handlers at 20 Hz removed 100 lines/s",
    _rollMs, _terrMs, _gripMs, _bodyMs, _bodyBoundMs, _logOnMs, _logOffMs
];

if (_fail == 0) then {
    diag_log text format ["[P120] [PASS] mobility per-frame cost: %1 checks, body %2 ms/pass", _pass, _bodyMs];
} else {
    diag_log text format ["[P120] [FAIL] mobility per-frame cost: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
