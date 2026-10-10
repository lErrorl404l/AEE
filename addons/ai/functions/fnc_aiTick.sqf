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

    // An ecology-driven animal is owned by the wildlife ecology tick, so the
    // generic substrate does not drive it too.  The flag is absent until the
    // ecology tick sets it, so existing callers are unchanged.
    if (_isObject && {!isNull _anchor}) then {
        private _ecology = _anchor getVariable [QGVAR(ecologyDriven), false];
        if ((_ecology isEqualType true) && _ecology) then { continue; };
    };

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

        // A survival-driven agent takes its need from the physiology
        // survival pressure instead of the static value.  The flag is
        // absent until a caller sets it, so existing agents are unchanged.
        private _survivalDriven = _anchor getVariable [QGVAR(survivalDriven), false];
        if ((_survivalDriven isEqualType true) && _survivalDriven) then {
            private _survival = [_anchor] call FUNC(survivalNeed);
            if (_survival isEqualType 0) then { _need = _survival; };
        };
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

        private _logMsg = format ["agent %1 action %2 disturbance %3 need %4", _id, _action, _disturbance, _need];
        AEE_LOG_DEBUG(_logMsg);
    };

    _ticked = _ticked + 1;
};

missionNamespace setVariable [QGVAR(agents), _agents];

_ticked
