#include "..\script_component.hpp"

/*
Register one spawned animal with the reusable substrate and steer it.

Client-local.  The animal's engine FSM is disabled by the spawn path, so the
substrate action callback owns the movement.  The callback runs the needs
kernel each time it acts, publishes the need pressure on the anchor for
fnc_aiTick, flees with a vanilla fear call, and otherwise travels toward the
current goal.  Movement uses moveTo and setDestination only.

The substrate calls the callback later, out of this function's scope, so the
callback reads no local of this function.  SQF has no lexical closure.

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

private _callback = {
    params ["_agent", "_action", "_state"];
    if (isNull _agent) exitWith { 0 };

    private _hunger = _agent getVariable [QGVAR(hunger), 0.1];
    if !(_hunger isEqualType 0) then { _hunger = 0.1; };
    private _thirst = _agent getVariable [QGVAR(thirst), 0.1];
    if !(_thirst isEqualType 0) then { _thirst = 0.1; };

    private _needs = [_hunger, _thirst, 1, 0.02, 0.03] call FUNC(needsTick);
    _hunger = _needs select 0;
    _thirst = _needs select 1;
    private _goal = _needs select 2;
    _agent setVariable [QGVAR(hunger), _hunger];
    _agent setVariable [QGVAR(thirst), _thirst];
    _agent setVariable [QEGVAR(ai,need), ((_hunger max _thirst) max 0) min 1];

    private _recovery = 1;
    private _position = getPos _agent;

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
        private _fearSound = "a3\sounds_f\ambient\animals\scared_animal1.wss";
        [_fearSound, _position, 0.9, WILDLIFE_SOUND_MAX_DISTANCE] call FUNC(playOneShot);
        _recovery = 6;
    } else {
        if ((_goal > 0) || (_action == 2) || (_action == 1)) then {
            // Travel toward the goal.  The resource search refines this in a
            // later slice of the fauna work.
            private _heading = ((_position getDir (getPos _agent)) + 90) mod 360;
            private _target = [
                (_position select 0) + (60 * (sin _heading)),
                (_position select 1) + (60 * (cos _heading)),
                0
            ];
            _agent moveTo _target;
            _agent setDestination [_target, "LEADER PLANNED", false];
            _recovery = 8;
        };
    };

    _recovery
};

[_id, _agent, [40], [0.6, 0.3, 0.5, 0.2], _callback, 2] call EFUNC(ai,agentRegister);

true
