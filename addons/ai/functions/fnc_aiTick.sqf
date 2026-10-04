#include "..\script_component.hpp"

/*
The reusable substrate client tick.

Runs the four stages over the registry: sense, decide (unless the agent is in
recovery), act through the registered callback, recover for the returned
seconds.  The field is the local disturbance field; the need pressure is read
from the anchor object variable aee_ai_need.  The callback returns the
recovery seconds, so the ecology owns the recovery policy.

Client-local only.  A machine with no player runs nothing.

Arguments:
  0: Bool - dry run, compute only and skip the callback

Returns:
  Number - the number of agents ticked
*/

params [["_dryRun", false, [false]]];

if (!hasInterface) exitWith { 0 };

private _agents = missionNamespace getVariable [QGVAR(agents), []];
private _field = missionNamespace getVariable [QGVAR(disturbance), []];
private _now = CBA_missionTime;
private _currentUnit = call CBA_fnc_currentUnit;
private _forceDecide = missionNamespace getVariable ["aee_ai_forceDecide", -1];
if !(_forceDecide isEqualType 0) then { _forceDecide = -1; };

private _ticked = 0;

for "_i" from 0 to ((count _agents) - 1) do {
    private _entry = _agents select _i;
    _entry params ["_id", "_anchor", "_senses", "_thresholds", "_callback", "_recoveryUntil"];

    private _anchorPos = [0, 0, 0];
    private _playerDistance = 1e10;
    private _isObject = (_anchor isEqualType objNull);

    if (_isObject && {!isNull _anchor}) then {
        _anchorPos = getPos _anchor;
    } else {
        if ((_anchor isEqualType []) && {(count _anchor) >= 2}) then {
            _anchorPos = _anchor;
        };
    };

    if (!isNil "_currentUnit" && {!isNull _currentUnit}) then {
        if (_isObject && {!isNull _anchor}) then {
            _playerDistance = _anchor distance _currentUnit;
        } else {
            _playerDistance = _anchorPos distance (getPos _currentUnit);
        };
    };

    private _need = 0;
    if (_isObject && {!isNull _anchor}) then {
        _need = _anchor getVariable [QGVAR(need), 0];
    };

    if (_now >= _recoveryUntil) then {
        private _key = [_anchorPos] call FUNC(disturbanceKey);
        private _disturbance = [_field, _key, _now, AI_STIMULUS_HALF_LIFE] call FUNC(disturbanceSample);
        private _state = [_disturbance, _playerDistance, _need, _senses] call FUNC(agentSense);
        private _action = [_state, _thresholds] call FUNC(agentDecide);

        if (_forceDecide >= 0) then {
            _action = _forceDecide;
        };

        if (!_dryRun) then {
            private _recovery = [_anchor, _action, _state] call _callback;
            if (_recovery isEqualType 0) then {
                _entry set [5, _now + _recovery];
                _agents set [_i, _entry];
            };
        };

        AEE_LOG_DEBUG(format ["agent %1 action %2 disturbance %3 need %4", _id, _action, _disturbance, _need]);
    };

    _ticked = _ticked + 1;
};

missionNamespace setVariable [QGVAR(agents), _agents];

_ticked
