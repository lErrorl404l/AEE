// PHASE 104: the call emit and receive semantics, and the heard-call bus.
//
// A call is a signal, not an ambient loop.  fnc_callEmit turns a condition and
// the animal's perception into a typed call with an urgency; fnc_callReceive
// decodes a heard call against the receiver's relation and state into a
// response.  The bus, fnc_callPublish and fnc_callSample, mirrors the
// disturbance field: the same cell key, horizon and cap, and the strongest
// live call at a cell wins.
//
// Every kernel here is pure, so the probe drives them with fixtures.  It
// renders nothing and plays nothing.
//
// Emits [P104] PASS/FAIL lines.

missionNamespace setVariable ["aee_wildlife_logDebug", false];
missionNamespace setVariable ["aee_core_logDebug", false];

private _fnEmit = missionNamespace getVariable ["aee_wildlife_fnc_callEmit", []];
private _fnReceive = missionNamespace getVariable ["aee_wildlife_fnc_callReceive", []];
private _fnPublish = missionNamespace getVariable ["aee_wildlife_fnc_callPublish", []];
private _fnSample = missionNamespace getVariable ["aee_wildlife_fnc_callSample", []];
if ((_fnEmit isEqualType []) || (_fnReceive isEqualType []) || (_fnPublish isEqualType []) || (_fnSample isEqualType [])) exitWith {
    diag_log text "[P104] [FAIL] call kernels not compiled (emit/receive/publish/sample)";
};

private _pass = 0;
private _fail = 0;
private _notes = [];

// A gregarious, in-season group under full threat: the emit fixture.
private _speciesOn = [1, true];
private _perceptionHigh = [1, 1, 1, []];
private _state = [0.2, 0.2, 0.5, 12, [0, 0, 0], 0];

// ── Emit ──────────────────────────────────────────────────────────────────

// 1. A perceived predator emits an alarm at full urgency.
private _alarm = [_speciesOn, _perceptionHigh, _state, "predator"] call _fnEmit;
if (((count _alarm) == 2) && {(_alarm select 0) == "alarm"} && {(_alarm select 1) > 0.9}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["predator emit %1", _alarm];
};

// 2. No trigger, no call.
if (([[], [], [], ""] call _fnEmit) isEqualTo []) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack "empty trigger emitted a call";
};

// 3. A season trigger emits mating only when the season is active.
private _off = [[0.8, false], [0.5, 0, 0, []], _state, "season"] call _fnEmit;
private _on = [[0.8, true], [0.5, 0, 0, []], _state, "season"] call _fnEmit;
if ((_off isEqualTo []) && {(_on select 0) == "mating"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["season emit off %1 on %2", _off, _on];
};

// 4. A cohesion trigger is gated on the gregariousness floor: a solitary
//    group emits no contact call, a gregarious one does.
private _solitary = [[0.4, true], [0.5, 0, 0, []], _state, "cohesion"] call _fnEmit;
private _social = [[0.5, true], [0.5, 0, 0, []], _state, "cohesion"] call _fnEmit;
if ((_solitary isEqualTo []) && {(_social select 0) == "contact"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["cohesion solitary %1 social %2", _solitary, _social];
};

// 5. A resource trigger emits a food call.
private _food = [[0.6, true], [0.5, 0, 0, []], _state, "resource"] call _fnEmit;
if ((_food select 0) == "food") then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["resource emit %1", _food];
};

// ── Receive ───────────────────────────────────────────────────────────────

// 6. An alarm to a gregarious conspecific gathers or mobs.
private _gather = ["alarm", 1, 10, 0, [200, 0.8]] call _fnReceive;
if ((_gather select 0) == 3) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["gregarious alarm response %1", _gather];
};

// 7. An alarm to a solitary conspecific flees at a strong call and goes
//    silent at a weak one.
private _strong = ["alarm", 1, 0, 0, [200, 0.2]] call _fnReceive;
private _weak = ["alarm", 0.4, 190, 0, [200, 0.2]] call _fnReceive;
if (((_strong select 0) == 2) && {(_weak select 0) == 1}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["solitary alarm strong %1 weak %2", _strong, _weak];
};

// 8. A prey flees an alarm and a predator investigates it.
private _prey = ["alarm", 1, 10, 2, [200, 0.5]] call _fnReceive;
private _predator = ["alarm", 1, 10, 1, [200, 0.5]] call _fnReceive;
if (((_prey select 0) == 2) && {(_predator select 0) == 5}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["prey %1 predator %2", _prey, _predator];
};

// 9. A call beyond the audibility range is not heard, and a neutral relation
//    decodes nothing.
private _beyond = ["alarm", 1, 300, 0, [200, 0.8]] call _fnReceive;
private _neutral = ["alarm", 1, 10, 3, [200, 0.8]] call _fnReceive;
if ((_beyond isEqualTo [0, 0]) && {_neutral isEqualTo [0, 0]}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["beyond %1 neutral %2", _beyond, _neutral];
};

// 10. A territorial call draws a reply from a conspecific.
private _reply = ["territorial", 0.5, 10, 0, [200, 0.8]] call _fnReceive;
if ((_reply select 0) == 4) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["territorial reply %1", _reply];
};

// 11. Distance attenuates the strength but does not silence a heard call.
private _near = ["contact", 1, 0, 0, [200, 0.8]] call _fnReceive;
private _far = ["contact", 1, 100, 0, [200, 0.8]] call _fnReceive;
if (((_near select 1) > (_far select 1)) && {(_far select 1) > 0}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["strength near %1 far %2", _near, _far];
};

// ── Bus ───────────────────────────────────────────────────────────────────

// 12. A published call is sampled at its cell.
private _key = [3, 4];
private _bus = [[], _key, "alarm", 0.9, "bird", 100] call _fnPublish;
private _heard = [_bus, _key, 100] call _fnSample;
if (((count _heard) == 3) && {(_heard select 0) == "alarm"} && {(_heard select 2) == "bird"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["bus sample %1", _heard];
};

// 13. An expired call is never heard.
private _expired = [_bus, _key, 500] call _fnSample;
if (_expired isEqualTo []) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["expired call heard %1", _expired];
};

// 14. The bus caps at the budget and keeps the newest rows.
private _big = [];
for "_i" from 1 to 300 do {
    _big = [_big, [_i, 0], "contact", 0.5, "x", 0] call _fnPublish;
};
if ((count _big) <= 256) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["bus cap %1", count _big];
};

// 15. The strongest live call at a cell wins the sample.
private _bus2 = [];
_bus2 = [_bus2, [0, 0], "contact", 0.2, "a", 10] call _fnPublish;
_bus2 = [_bus2, [0, 0], "alarm", 0.9, "b", 10] call _fnPublish;
private _best = [_bus2, [0, 0], 10] call _fnSample;
if (((count _best) == 3) && {(_best select 0) == "alarm"}) then {
    _pass = _pass + 1;
} else {
    _fail = _fail + 1;
    _notes pushBack format ["strongest wins %1", _best];
};

diag_log text format ["[P104] bus: published %1 rows, capped %2, strongest %3", 300, count _big, _best select 0];

if (_fail == 0) then {
    diag_log text format ["[P104] [PASS] call emit and receive semantics (%1 checks)", _pass];
} else {
    diag_log text format ["[P104] [FAIL] call semantics: %1 passed, %2 failed: %3", _pass, _fail, str _notes];
};
