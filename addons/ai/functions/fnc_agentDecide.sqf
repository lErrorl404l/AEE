#include "..\script_component.hpp"

/*
Agent decide kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Stage 2 of
the four-stage model.  Maps the sense state and a caller-supplied threshold
table to one action id.  No constant lives here, so the ecology owns every
threshold.  Priority: flee, freeze, drink, forage, else rest.

Arguments:
  0: Array - the state from fnc_agentSense, [disturbance, proximity, need]
  1: Array - thresholds [flee, freeze, drink, forage]

Returns:
  Number - action id: 0 rest, 1 forage, 2 drink, 3 flee, 4 freeze
*/

params [
    ["_state", [], [[]]],
    ["_thresholds", [], [[]]]
];

private _disturbance = _state select 0;
private _need = _state select 2;
private _fleeThreshold = _thresholds select 0;
private _freezeThreshold = _thresholds select 1;
private _drinkThreshold = _thresholds select 2;
private _forageThreshold = _thresholds select 3;

private _action = 0;

if (_disturbance > _fleeThreshold) then {
    _action = 3;
} else {
    if (_disturbance > _freezeThreshold) then {
        _action = 4;
    } else {
        if (_need > _drinkThreshold) then {
            _action = 2;
        } else {
            if (_need > _forageThreshold) then {
                _action = 1;
            };
        };
    };
};

_action
