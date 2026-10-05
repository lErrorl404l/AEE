#include "..\script_component.hpp"

/*
On-demand wildlife health monitor.

A caller runs it from the debug console:

  [] call aee_wildlife_fnc_monitorWildlife;

The monitor prints the consolidated state line, the wildlife tick cost and the
AI tick cost, then returns the composed line.  The composed line starts with
"wildlife monitor |" and carries both tick costs, their budgets, the registry
counts and the gates.

The monitor is read-only.  Every timing sample runs the documented dry-run
path, so it computes state and stops before any sound, spawn or field write.
The function never plays a sound, never spawns an animal and never changes
state.  It is safe at any time and on a dedicated server, where the counts
and the gates still print and an impossible timing prints as "-".

Arguments: none.

Returns:
  String - the composed monitor line.
*/

// The registry reads are guarded exactly like fnc_logWildlifeState.  A
// dedicated server has no local player, so every read falls back to an empty
// or default value and no read can throw.
private _agents = missionNamespace getVariable [QEGVAR(ai,agents), []];
if !(_agents isEqualType []) then { _agents = []; };

private _field = missionNamespace getVariable [QEGVAR(ai,disturbance), []];
if !(_field isEqualType []) then { _field = []; };

private _fauna = missionNamespace getVariable [QGVAR(fauna), []];
if !(_fauna isEqualType []) then { _fauna = []; };
private _faunaLive = 0;
{
    if (_x isEqualType []) then {
        if ((count _x) >= 2) then {
            if (!isNull (_x select 1)) then { _faunaLive = _faunaLive + 1; };
        };
    };
} forEach _fauna;
private _faunaCap = missionNamespace getVariable [QGVAR(maxAnimals), 16];
if !(_faunaCap isEqualType 0) then { _faunaCap = 16; };

private _instances = missionNamespace getVariable [QGVAR(soundInstances), []];
if !(_instances isEqualType []) then { _instances = []; };
private _soundLive = 0;
private _now = CBA_missionTime;
{
    if (_x isEqualType 0) then {
        if (_x > _now) then { _soundLive = _soundLive + 1; };
    };
} forEach _instances;

private _enabled = missionNamespace getVariable [QGVAR(enabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
private _ambient = missionNamespace getVariable [QGVAR(ambientEnabled), true];
if !(_ambient isEqualType true) then { _ambient = true; };
private _animals = missionNamespace getVariable [QGVAR(animalsEnabled), false];
if !(_animals isEqualType true) then { _animals = false; };
private _density = missionNamespace getVariable [QGVAR(density), 1.0];
if !(_density isEqualType 0) then { _density = 1.0; };

// Block 1: the consolidated state line.  The dry-run tick computes the state
// and stops before any sound, spawn or field write.  Its own call to
// fnc_logWildlifeState emits the state line.
[[0, 0, 0], true] call FUNC(wildlifeTick);

// The dry-run contract of fnc_wildlifeTick and fnc_aiTick is the last
// argument true.  The sample is 100 iterations, a warm-up of a quarter, then
// the best of three thirds, exactly like PHASE10 and PHASE11.
private _iters = 100;
private _measure = {
    params ["_fn", "_args", "_iters"];
    for "_w" from 1 to (round (_iters / 4)) do { _args call _fn; };
    private _best = 1e9;
    for "_s" from 1 to 3 do {
        private _start = diag_tickTime;
        for "_i" from 1 to (round (_iters / 3)) do { _args call _fn; };
        private _elapsed = diag_tickTime - _start;
        if (_elapsed < _best) then { _best = _elapsed; };
    };
    (_best / (round (_iters / 3))) * 1000
};

// Block 2: the wildlife tick cost.  The dry-run path is machine-agnostic and
// safe on a dedicated server, so the sample always runs.
private _wildlifeMs = -1;
private _wildlifeFn = missionNamespace getVariable ["aee_wildlife_fnc_wildlifeTick", nil];
if (!isNil "_wildlifeFn") then {
    _wildlifeMs = [_wildlifeFn, [[0, 0, 0], true], _iters] call _measure;
};
private _wildlifeToken = "-";
if (_wildlifeMs >= 0) then {
    _wildlifeToken = format ["%1ms/2ms", round _wildlifeMs];
};
private _wildlifeMsg = format [
    "wildlife monitor wildlife | aee_wildlife_fnc_wildlifeTick: %1 (best of 3)",
    _wildlifeToken
];
AEE_LOG_INFO(_wildlifeMsg);

// Block 3: the AI tick cost.  fnc_aiTick exits early without an interface, so
// the sample is impossible on a dedicated server and the token prints "-".
// The counts and the gates still print below.
private _aiMs = -1;
private _aiFn = missionNamespace getVariable ["aee_ai_fnc_aiTick", nil];
if ((!isNil "_aiFn") && (hasInterface)) then {
    _aiMs = [_aiFn, [true], _iters] call _measure;
};
private _aiToken = "-";
if (_aiMs >= 0) then {
    _aiToken = format ["%1ms/2ms", round _aiMs];
};
private _aiMsg = format [
    "wildlife monitor ai | aee_ai_fnc_aiTick: %1 (best of 3)",
    _aiToken
];
AEE_LOG_INFO(_aiMsg);

// The composed line.  It carries the two costs and budgets, the registry
// counts and the gates in one grep-able statement.
private _line = format [
    "wildlife monitor | tick=%1 ai=%2 | agents=%3 field=%4 fauna=%5/%6 sound=%7/%8 | gates=on=%9 ambient=%10 animals=%11 density=%12",
    _wildlifeToken, _aiToken,
    count _agents, count _field, _faunaLive, _faunaCap, _soundLive, WILDLIFE_SOUND_INSTANCE_CAP,
    _enabled, _ambient, _animals, round (_density * 100) / 100
];
AEE_LOG_INFO(_line);

_line
