// PHASE 103: the ecology cognition tick budget.
//
// The ecology tick is bounded twice: a count budget caps the animals visited
// per call, and a millisecond budget caps the elapsed time.  The first animal
// of a call is always processed, so the tick always makes progress, and the
// unsolved remainder is re-queued at the FRONT of the pending list, so no
// animal starves.  The policy lives in the pure budget kernel
// fnc_ecologyBudget.
//
// The tick itself is client-only (it exits at once without an interface), so a
// dedicated server cannot drive its body.  This probe therefore drives the
// pure budget kernel with fixtures and confirms the tick compiles, is callable
// and honours the client gate on the headless server.  It renders nothing and
// plays nothing.
//
// Emits [P103] PASS/FAIL lines.

missionNamespace setVariable ["aee_wildlife_logDebug", false];
missionNamespace setVariable ["aee_core_logDebug", false];

private _fnBudget = missionNamespace getVariable ["aee_wildlife_fnc_ecologyBudget", []];
private _fnTick = missionNamespace getVariable ["aee_wildlife_fnc_ecologyTick", []];
if ((_fnBudget isEqualType []) || (_fnTick isEqualType [])) exitWith {
    diag_log text "[P103] [FAIL] cognition kernels not compiled (budget/tick)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// 1. The first animal of a call is always allowed, so the tick always makes
//    progress even when both budgets are already spent.
if ([0, 8, 999, 0] call _fnBudget) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "first animal was blocked";
};

// 2. The count budget stops the sweep.
if (!([8, 8, 0, 100] call _fnBudget)) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "count budget did not stop the sweep";
};

// 3. The millisecond budget stops the sweep before the count budget is met.
if (!([1, 8, 2, 1] call _fnBudget)) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "millisecond budget did not stop the sweep";
};

// 4. Under both budgets the sweep continues.
if ([1, 8, 0, 1] call _fnBudget) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "sweep stopped under both budgets";
};

// 5. A zero or negative count budget clamps to at least one, so the tick
//    still makes progress and then stops.
if (([0, 0, 0, 0] call _fnBudget) && {!([1, 0, 0, 0] call _fnBudget)}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "zero count budget clamp wrong";
};

// 6. A simulated sweep of 20 animals with a count budget of 8 allows exactly
//    eight of them, the batch the tick carries.
private _allowed = 0;
for "_i" from 0 to 19 do {
    if ([_i, 8, 0, 100] call _fnBudget) then { _allowed = _allowed + 1; };
};
if (_allowed == 8) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["batch allowed %1 of 20, expected 8", _allowed];
};

// 7. The tick compiles, is callable, and honours the client gate on the
//    headless server by returning the ticked count zero without error.
private _ticked = [true] call _fnTick;
if ((_ticked isEqualType 0) && {_ticked == 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["headless tick returned %1", _ticked];
};

diag_log text format ["[P103] budget: batch %1 of 20, headless tick %2", _allowed, _ticked];

if (_fail == 0) then {
    diag_log text format ["[P103] [PASS] ecology cognition tick budget (%1 checks)", _pass];
} else {
    diag_log text format ["[P103] [FAIL] ecology cognition tick budget: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
