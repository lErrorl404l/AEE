#include "..\script_component.hpp"

/*
Budgeted ecology tick (wildlife ecology).

Client-local.  It is the cognition driver over the fauna registry the reusable
substrate owns (fnc_agentRegister).  For each animal it runs the four stages:
perceive with the local environment sample and the heard call, think for a
plan, act through the registered callback, and recover for the returned
seconds.  The think plan is [action, callPlan, movement], which the extended
act callback consumes.

The tick is bounded twice.  The count budget caps the animals visited per call
and the millisecond budget (QGVAR(cognitionBudgetMs), default 1.0 ms) caps the
elapsed time.  The unsolved remainder is re-queued at the FRONT of the pending
list, so no animal is dropped and none starves.  The first animal of a call is
always processed, so the tick always makes progress.  The shape mirrors the
thermal paint sweep in fnc_applyBuildingThermal.

With cognition disabled the tick clears the ecology flag and exits, so the
generic substrate fnc_aiTick drives the animals exactly as before.

Arguments:
  0: Bool - dry run, compute the plan and skip the callback

Returns:
  Number - the number of animals ticked
*/

params [["_dryRun", false, [false]]];

if (!hasInterface) exitWith { 0 };

private _agents = missionNamespace getVariable [QEGVAR(ai,agents), []];
if !(_agents isEqualType []) then { _agents = []; };

private _enabled = missionNamespace getVariable [QGVAR(cognitionEnabled), false];
if !(_enabled isEqualType true) then { _enabled = false; };

// With cognition off the ecology flag is cleared, so the generic substrate
// drives every animal again.
if (!_enabled) exitWith {
    {
        private _anchor = _x select 1;
        if ((_anchor isEqualType objNull) && {!isNull _anchor}) then {
            _anchor setVariable [QEGVAR(ai,ecologyDriven), nil];
        };
    } forEach _agents;
    0
};

// The pending queue holds the registry entries not yet solved this cycle.
// It refills from the registry when it empties.
private _pending = missionNamespace getVariable [QGVAR(ecologyPending), []];
if !(_pending isEqualType []) then { _pending = []; };
if ((count _pending) == 0) then { _pending = +_agents; };

private _countBudget = WILDLIFE_COGNITION_BATCH;

private _msBudget = missionNamespace getVariable [QGVAR(cognitionBudgetMs), 1.0];
if !(_msBudget isEqualType 0) then { _msBudget = 1.0; };

private _now = CBA_missionTime;
private _start = diag_tickTime;

private _field = missionNamespace getVariable [QEGVAR(ai,disturbance), []];
if !(_field isEqualType []) then { _field = []; };
private _events = missionNamespace getVariable [QGVAR(soundEvents), []];
if !(_events isEqualType []) then { _events = []; };
private _propIndex = missionNamespace getVariable [QEGVAR(weather,currentSoundPropagation), 1];
if !(_propIndex isEqualType 0) then { _propIndex = 1; };
private _store = missionNamespace getVariable [QGVAR(environment), []];
if !(_store isEqualType []) then { _store = []; };
private _comm = missionNamespace getVariable [QEGVAR(ambience,communicationEnabled), false];
if !(_comm isEqualType true) then { _comm = false; };
private _bus = missionNamespace getVariable [QGVAR(callBus), []];
if !(_bus isEqualType []) then { _bus = []; };

private _solved = 0;
private _remainder = [];

for "_i" from 0 to ((count _pending) - 1) do {
    if !([_solved, _countBudget, ((diag_tickTime - _start) * 1000), _msBudget] call FUNC(ecologyBudget)) exitWith {
        _remainder = _pending select [_i];
    };

    private _entry = _pending select _i;
    _solved = _solved + 1;

    if ((_entry isEqualType []) && ((count _entry) >= 5)) then {
        _entry params ["_id", "_anchor", "_senses", "_thresholds", "_callback"];

        private _isObject = (_anchor isEqualType objNull) && {!isNull _anchor};
        private _pos = [0, 0, 0];
        if (_isObject) then {
            _pos = getPos _anchor;
        } else {
            if ((_anchor isEqualType []) && {(count _anchor) >= 2}) then { _pos = _anchor; };
        };

        if (_isObject) then { _anchor setVariable [QEGVAR(ai,ecologyDriven), true]; };

        // The environment sample at the animal's cell, if the cache holds it.
        private _key = [_pos] call EFUNC(ai,disturbanceKey);
        private _sample = [];
        for "_s" from 0 to ((count _store) - 1) do {
            private _row = _store select _s;
            if ((_row isEqualType []) && ((count _row) >= 2)) then {
                private _rkey = _row select 0;
                if ((_rkey isEqualType []) && ((count _rkey) >= 2)) then {
                    if (((_rkey select 0) == (_key select 0)) && ((_rkey select 1) == (_key select 1))) then {
                        _sample = _row select 1;
                    };
                };
            };
        };

        private _habitat = _anchor getVariable [QGVAR(habitatWeights), [0, 0, 0, 0]];
        if !(_habitat isEqualType []) then { _habitat = [0, 0, 0, 0]; };
        private _suitability = [_sample, _habitat] call FUNC(environmentSuitability);

        private _hunger = _anchor getVariable [QGVAR(hunger), 0.1];
        if !(_hunger isEqualType 0) then { _hunger = 0.1; };
        private _thirst = _anchor getVariable [QGVAR(thirst), 0.1];
        if !(_thirst isEqualType 0) then { _thirst = 0.1; };

        private _disturbance = [_field, _key, _now, WILDLIFE_ENVIRONMENT_HALF_LIFE] call EFUNC(ai,disturbanceSample);
        private _acoustic = 0;
        if ((count _events) > 0) then {
            private _occluders = [_pos] call EFUNC(ambience,acousticOccluders);
            private _level = [
                _events, _pos, _now, WILDLIFE_ACOUSTIC_EVENT_HORIZON, _propIndex, _occluders
            ] call EFUNC(ambience,acousticSample);
            _acoustic = _level select 0;
        };

        private _timeBin = ((floor (dayTime / 3.43)) max 0) min 6;
        private _rain = rain;
        if !(_rain isEqualType 0) then { _rain = 0; };
        private _windVector = wind;
        private _wind = (((_windVector select 0) ^ 2) + ((_windVector select 1) ^ 2)) ^ 0.5;
        private _state = [_hunger, _thirst, _disturbance, _timeBin, [_rain, _wind, 0], _acoustic];

        private _species = _anchor getVariable [QGVAR(speciesRules), [1, 0.4, 0.6, 1]];
        if !(_species isEqualType []) then { _species = [1, 0.4, 0.6, 1]; };

        // Sample the heard-call bus at the animal's cell.  The receiver is a
        // conspecific at no distance: the bus is keyed by cell, so a call
        // from the same cell is heard at full strength.
        private _heard = [];
        if (_comm) then {
            private _sampled = [_bus, _key, _now] call EFUNC(ambience,callSample);
            if ((count _sampled) >= 2) then {
                _heard = [_sampled select 0, _sampled select 1, 0, 0];
            };
        };
        _anchor setVariable [QGVAR(heardCall), _heard];

        private _perception = [_sample, _suitability, _species, _state, _heard] call FUNC(wildlifePerceive);
        private _plan = [_perception, _species, _thresholds] call FUNC(wildlifeThink);
        private _action = _plan select 0;

        _anchor setVariable [QGVAR(perception), _perception];
        _anchor setVariable [QGVAR(ecologyState), _state];

        if (!_dryRun) then {
            if (_callback isEqualType {}) then {
                private _recovery = [_anchor, _action, _state, _plan] call _callback;
                if (_recovery isEqualType 0) then {
                    _entry set [5, _now + _recovery];
                };
            };
        };
    };
};

// The unsolved remainder stays at the FRONT for the next call: nothing is
// dropped and nothing starves.
missionNamespace setVariable [QGVAR(ecologyPending), _remainder];

_solved
