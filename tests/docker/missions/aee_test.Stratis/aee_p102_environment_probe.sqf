// PHASE 102: the neighbourhood environment sampler budget and re-queue.
//
// The sampler walks a local grid of cells and samples each cell from the
// engine surface.  A per-call object-query cap and a millisecond budget bound
// the work; the unsampled cells are re-queued at the FRONT of the pending
// list, so no cell starves across calls.  The pure cache kernel ages and caps
// the per-cell store, so one policy owns the bound.
//
// This probe drives the real sampler with a fixed centre and a fixed grid, and
// the pure cache kernel with a fixture store.  It renders nothing and plays
// nothing.
//
// Emits [P102] PASS/FAIL lines.

missionNamespace setVariable ["aee_wildlife_logDebug", false];
missionNamespace setVariable ["aee_core_logDebug", false];

private _fnSample = missionNamespace getVariable ["aee_wildlife_fnc_sampleNeighbourhood", []];
private _fnGrid = missionNamespace getVariable ["aee_wildlife_fnc_environmentGrid", []];
if ((_fnSample isEqualType []) || (_fnGrid isEqualType [])) exitWith {
    diag_log text "[P102] [FAIL] environment kernels not compiled (sample/grid)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// A fixed centre on the Stratis land mass, and the default 5 by 5 grid at
// 25 m, so the sampler walks exactly 25 cells.
private _centre = [3000, 3000, 0];
private _cells = 25;

// Start from a clean sampler state so the probe owns the pending list.
missionNamespace setVariable ["aee_wildlife_environment", []];
missionNamespace setVariable ["aee_wildlife_environmentPending", []];

// 1. A zero budget stops the sweep before the first cell and re-queues the
//    WHOLE grid at the front.  No cell is lost.
[_centre, 25, 5, 12, 0] call _fnSample;
private _pending0 = missionNamespace getVariable ["aee_wildlife_environmentPending", []];
private _store0 = missionNamespace getVariable ["aee_wildlife_environment", []];
if (((count _pending0) == _cells) && {count _store0 == 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["zero budget: pending %1/%2 store %3", count _pending0, _cells, count _store0];
};

// 2. Repeated small-budget calls drain the pending list and cover every cell.
//    The store reaches the full grid, so the re-queue does not starve a cell.
private _calls = 0;
for "_k" from 1 to 80 do {
    private _p = missionNamespace getVariable ["aee_wildlife_environmentPending", []];
    if ((_p isEqualType []) && {(count _p) > 0}) then {
        [_centre, 25, 5, 12, 1] call _fnSample;
        _calls = _calls + 1;
    };
};
private _pendingN = missionNamespace getVariable ["aee_wildlife_environmentPending", []];
private _storeN = missionNamespace getVariable ["aee_wildlife_environment", []];
if (((count _pendingN) == 0) && {count _storeN == _cells}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["drain: calls %1 pending %2 store %3", _calls, count _pendingN, count _storeN];
};

// 3. A generous budget drains the whole grid in one call and records the
//    elapsed milliseconds.  The budget is the gate, not the host speed.
missionNamespace setVariable ["aee_wildlife_environment", []];
missionNamespace setVariable ["aee_wildlife_environmentPending", []];
[_centre, 25, 5, 12, 500] call _fnSample;
private _pendingBig = missionNamespace getVariable ["aee_wildlife_environmentPending", []];
private _lastMs = missionNamespace getVariable ["aee_wildlife_environmentLastMs", -1];
if (((count _pendingBig) == 0) && {_lastMs isEqualType 0} && {_lastMs >= 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["one-shot: pending %1 lastMs %2", count _pendingBig, _lastMs];
};

// 4. The pure cache kernel caps the store at 256 and keeps the NEWEST rows.
private _now = 1000;
private _fixture = [];
for "_i" from 0 to 299 do {
    _fixture pushBack [[_i, 0], [0.5, [], 0, 0, 10], _now];
};
private _capped = [_fixture, _now] call _fnGrid;
private _capFirst = -1;
if ((count _capped) > 0) then { _capFirst = (_capped select 0) select 0 select 0; };
if ((count _capped) == 256 && {_capFirst == 44}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["cap: count %1 firstKey %2", count _capped, _capFirst];
};

// 5. The pure cache kernel drops a row older than the 120 s horizon and keeps
//    a row inside it.
private _aged = [
    [[0, 0], [0, 0, 0, 0, 0], _now - 121],
    [[1, 0], [0, 0, 0, 0, 0], _now - 119]
];
private _fresh = [_aged, _now] call _fnGrid;
private _ageKey = -1;
if ((count _fresh) > 0) then { _ageKey = (_fresh select 0) select 0 select 0; };
if ((count _fresh) == 1 && {_ageKey == 1}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["age: count %1 key %2", count _fresh, _ageKey];
};

// Leave no synthetic sampler state behind for a later tick.
missionNamespace setVariable ["aee_wildlife_environment", []];
missionNamespace setVariable ["aee_wildlife_environmentPending", []];

diag_log text format ["[P102] sampler: %1 calls to drain %2 cells, one-shot lastMs %3", _calls, _cells, _lastMs];
diag_log text format ["[P102] cache kernel: cap %1 rows, horizon drop %2", count _capped, (2 - count _fresh)];

if (_fail == 0) then {
    diag_log text format ["[P102] [PASS] environment sampler budget and re-queue (%1 checks)", _pass];
} else {
    diag_log text format ["[P102] [FAIL] environment sampler budget: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
