#include "..\script_component.hpp"

/*
Register one spawned animal with the reusable substrate and steer it.

Client-local.  The animal's engine FSM is disabled by the spawn path, so the
substrate action callback owns the movement.  The callback runs the needs
kernel each time it acts, publishes the need pressure on the anchor for
fnc_aiTick, flees with a vanilla fear call, travels to the nearest wanted
resource, resets the matching need on arrival, and leashes the animal to its
herd anchor at rest.  Movement uses moveTo and setDestination only.

The substrate calls the callback later, out of this function's scope, so the
resource providers and the herd anchors live in missionNamespace and are read
back inside the callback.  SQF has no lexical closure.

Arguments:
  0: String - the agent id
  1: Object - the agent
  2: String - the species class

Returns:
  Bool - true when the animal is registered
*/

params [
    ["_id", "", [""]],
    ["_agent", objNull, [objNull]],
    ["_species", "", [""]]
];

if (!hasInterface) exitWith { false };
if (isNull _agent) exitWith { false };
if (_id == "") exitWith { false };

// The resource providers read the published environmental facts.  They are
// stored once so the out-of-scope callback can reach them.
private _waterProvider = {
    params ["_point"];
    private _coast = [_point, 200] call EFUNC(environmental,getCoastDistance);
    if !(_coast isEqualType 0) then { _coast = 200; };
    1 - ((_coast / 200) min 1)
};
private _vegProvider = {
    params ["_point"];
    private _signals = missionNamespace getVariable [QEGVAR(environmental,terrainSignals), []];
    if !(_signals isEqualType []) then { _signals = []; };
    [_signals] call FUNC(vegScore)
};
missionNamespace setVariable [QGVAR(waterProvider), _waterProvider];
missionNamespace setVariable [QGVAR(vegProvider), _vegProvider];

// The herd size setting caps how many animals share one anchor.  The first
// animal of a species cluster sets the anchor.  A later animal joins the
// first anchor of the same species that has room, else it starts a new herd.
// The slot is released when an animal is culled, so the cap stays accurate.
private _herdSize = [QGVAR(herdSize), 4, 1] call EFUNC(core,readState);
_herdSize = (round _herdSize) max 1;

private _herds = missionNamespace getVariable [QGVAR(herds), []];
if !(_herds isEqualType []) then { _herds = []; };
private _herdAnchor = getPos _agent;
private _found = false;
for "_i" from 0 to ((count _herds) - 1) do {
    if (!_found) then {
        private _row = _herds select _i;
        if ((_row select 0) == _species) then {
            if ((count _row) < 3) then { _row pushBack 0; };
            private _members = _row select 2;
            if !(_members isEqualType 0) then { _members = 0; };
            if (_members < _herdSize) then {
                _herdAnchor = _row select 1;
                _row set [2, _members + 1];
                _found = true;
            };
        };
    };
};
if (!_found) then {
    _herds pushBack [_species, _herdAnchor, 1];
    missionNamespace setVariable [QGVAR(herds), _herds];
};
_agent setVariable [QGVAR(herdAnchor), _herdAnchor];

private _callback = {
    params ["_agent", "_action", "_state", ["_plan", [], [[]]]];
    if (isNull _agent) exitWith { 0 };

    private _hunger = _agent getVariable [QGVAR(hunger), 0.1];
    if !(_hunger isEqualType 0) then { _hunger = 0.1; };
    private _thirst = _agent getVariable [QGVAR(thirst), 0.1];
    if !(_thirst isEqualType 0) then { _thirst = 0.1; };

    // The hunger and thirst rates are operator settings.  Read them each
    // callback with the module's guarded read, so a missing or malformed
    // setting falls back to the kernel default.
    private _hungerRate = [QGVAR(hungerRate), 0.02, 1] call EFUNC(core,readState);
    private _thirstRate = [QGVAR(thirstRate), 0.03, 1] call EFUNC(core,readState);

    private _needs = [_hunger, _thirst, 1, _hungerRate, _thirstRate] call FUNC(needsTick);
    _hunger = _needs select 0;
    _thirst = _needs select 1;
    private _goal = _needs select 2;
    _agent setVariable [QGVAR(hunger), _hunger];
    _agent setVariable [QGVAR(thirst), _thirst];
    _agent setVariable [QEGVAR(ai,need), ((_hunger max _thirst) max 0) min 1];

    private _recovery = 1;
    private _position = getPos _agent;

    private _waterProvider = missionNamespace getVariable [QGVAR(waterProvider), {}];
    if !(_waterProvider isEqualType {}) then { _waterProvider = {}; };
    private _vegProvider = missionNamespace getVariable [QGVAR(vegProvider), {}];
    if !(_vegProvider isEqualType {}) then { _vegProvider = {}; };

    if (_action == 3) then {
        // Flee from the nearest player, with a vanilla fear call.
        private _unit = call CBA_fnc_currentUnit;
        private _direction = 0;
        if (!isNull _unit) then { _direction = _position getDir (getPos _unit); };
        private _away = [
            (_position select 0) + (40 * (sin (_direction + 180))),
            (_position select 1) + (40 * (cos (_direction + 180))),
            0
        ];
        _agent moveTo _away;
        _agent setDestination [_away, "LEADER PLANNED", false];
        // A species-appropriate fear source from the asset map.  The vanilla
        // clips are generic, so the choice is a deterministic draw seeded by
        // the species class, not a species-specific recording.
        private _assetMap = missionNamespace getVariable [QGVAR(assetMap), []];
        if !(_assetMap isEqualType []) then { _assetMap = []; };
        private _fear = ["fear", [], _assetMap] call FUNC(speciesSound);
        private _fearMedia = _fear select 0;
        if !(_fearMedia isEqualType []) then { _fearMedia = []; };
        if ((count _fearMedia) > 0) then {
            private _speciesGroup = _agent getVariable [QGVAR(speciesGroup), ""];
            if !(_speciesGroup isEqualType "") then { _speciesGroup = ""; };
            private _sum = 0;
            private _chars = toArray _speciesGroup;
            for "_ci" from 0 to ((count _chars) - 1) do {
                _sum = _sum + (_chars select _ci);
            };
            private _index = (_sum mod (count _fearMedia));
            private _fearSound = _fearMedia select _index;
            [_fearSound, _position, 0.9, WILDLIFE_SOUND_MAX_DISTANCE] call FUNC(playOneShot);
        };
        _recovery = 6;
    } else {
        if ((_goal > 0) || (_action == 2) || (_action == 1)) then {
            private _wantWater = ((_goal == 2) || (_action == 2));
            private _target = [
                _position, _wantWater, 100, 25, _waterProvider, _vegProvider
            ] call FUNC(pickResourceTarget);

            private _hereVeg = [_position] call _vegProvider;
            private _ring = [];
            for "_b" from 0 to 3 do {
                private _ang = _b * 90;
                _ring pushBack ([(_position select 0) + (20 * (sin _ang)), (_position select 1) + (20 * (cos _ang)), 0] call _vegProvider);
            };
            private _boundary = [_hereVeg, _ring, 0.2, (round CBA_missionTime), 0.02] call FUNC(habitatBoundary);
            private _leave = ((_boundary select 0) == 2);

            if ((((_target select 0) != 0) || ((_target select 1) != 0)) && !_leave) then {
                _agent moveTo _target;
                _agent setDestination [_target, "LEADER PLANNED", false];
                _recovery = 8;
            };

            // Arrival at the resource resets the matching need.
            if (_wantWater) then {
                private _coast = [_position, 200] call EFUNC(environmental,getCoastDistance);
                if (_coast isEqualType 0) then {
                    if (_coast < 25) then { _agent setVariable [QGVAR(thirst), 0]; };
                };
            } else {
                private _vegHere = [_position] call _vegProvider;
                if (_vegHere isEqualType 0) then {
                    if (_vegHere > 0.5) then { _agent setVariable [QGVAR(hunger), 0]; };
                };
            };
        } else {
            // Rest: hold near the herd anchor.
            private _herd = _agent getVariable [QGVAR(herdAnchor), _position];
            if !(_herd isEqualType []) then { _herd = _position; };
            if ((_agent distance _herd) > 60) then {
                private _leash = [_herd select 0, _herd select 1, 0];
                _agent moveTo _leash;
                _agent setDestination [_leash, "LEADER PLANNED", false];
                _recovery = 4;
            };
        };
    };

    // Calls.  The think plan is [action, callPlan, movement]; the call plan is
    // a call type or -1.  Emit through the call-emit kernel and publish to
    // the heard-call bus, and react to a heard call through the call-receive
    // kernel.  The ecology tick sets the perception, the state and the heard
    // call on the anchor.
    private _callPlan = -1;
    if ((count _plan) >= 2) then { _callPlan = _plan select 1; };

    private _comm = missionNamespace getVariable [QGVAR(communicationEnabled), false];
    if !(_comm isEqualType true) then { _comm = false; };

    if (_comm) then {
        if (_callPlan isEqualType "") then {
            private _trigger = "";
            if (_callPlan == "alarm") then { _trigger = "predator"; };
            if (_callPlan == "contact") then { _trigger = "cohesion"; };
            if (_trigger != "") then {
                private _perception = _agent getVariable [QGVAR(perception), []];
                private _ecologyState = _agent getVariable [QGVAR(ecologyState), []];
                private _speciesEmit = _agent getVariable [QGVAR(speciesEmit), [0.5, true]];
                if !(_speciesEmit isEqualType []) then { _speciesEmit = [0.5, true]; };
                private _call = [_speciesEmit, _perception, _ecologyState, _trigger] call FUNC(callEmit);
                if ((count _call) >= 2) then {
                    private _bus = missionNamespace getVariable [QGVAR(callBus), []];
                    if !(_bus isEqualType []) then { _bus = []; };
                    private _key = [getPos _agent] call EFUNC(ai,disturbanceKey);
                    private _speciesGroup = _agent getVariable [QGVAR(speciesGroup), ""];
                    if !(_speciesGroup isEqualType "") then { _speciesGroup = ""; };
                    _bus = [
                        _bus, _key, _call select 0, _call select 1, _speciesGroup, CBA_missionTime
                    ] call FUNC(callPublish);
                    private _budget = missionNamespace getVariable [QGVAR(callBudget), WILDLIFE_CALL_BUDGET];
                    if !(_budget isEqualType 0) then { _budget = WILDLIFE_CALL_BUDGET; };
                    if ((count _bus) > _budget) then {
                        _bus = _bus select [((count _bus) - _budget), _budget];
                    };
                    missionNamespace setVariable [QGVAR(callBus), _bus];
                };
            };
        };

        // React to a heard call.  The ecology tick stores the decoded
        // [callType, urgency, distance, relation] on the anchor.
        private _heard = _agent getVariable [QGVAR(heardCall), []];
        if ((count _heard) >= 4) then {
            private _range = missionNamespace getVariable [QGVAR(callRange), WILDLIFE_CALL_RANGE];
            if !(_range isEqualType 0) then { _range = WILDLIFE_CALL_RANGE; };
            private _speciesHear = _agent getVariable [QGVAR(speciesEmit), [0.5, true]];
            private _gregariousness = 0.5;
            if ((_speciesHear isEqualType []) && ((count _speciesHear) >= 1)) then {
                private _group = _speciesHear select 0;
                if (_group isEqualType 0) then { _gregariousness = (_group max 0) min 1; };
            };
            private _reaction = [
                _heard select 0, _heard select 1, _heard select 2, _heard select 3,
                [_range, _gregariousness]
            ] call FUNC(callReceive);
            private _response = _reaction select 0;
            if (_response == 2) then { _action = 3; };
            if (_response == 3) then {
                private _herd = _agent getVariable [QGVAR(herdAnchor), _position];
                if !(_herd isEqualType []) then { _herd = _position; };
                _agent moveTo [_herd select 0, _herd select 1, 0];
                _recovery = 4;
            };
        };
    };

    _recovery
};

// The ecology tick reads these.  The defaults are UNSOURCED modelling
// choices; a species-specific row is a later refinement.
_agent setVariable [QGVAR(speciesRules), [1, 0.4, 0.6, 1]];
_agent setVariable [QGVAR(habitatWeights), [0, 0, 0, 0]];
_agent setVariable [QGVAR(speciesEmit), [0.5, true]];
_agent setVariable [QGVAR(speciesGroup), _species];

[_id, _agent, [40], [0.6, 0.3, 0.5, 0.2], _callback, 2] call EFUNC(ai,agentRegister);

true
