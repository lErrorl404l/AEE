#include "..\script_component.hpp"

/*
Decision kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It maps the perception vector and the caller thresholds to one action, a call
plan and a movement mode.  It is the ecology extension of the substrate
decide kernel fnc_agentDecide, which stays the generic fallback.

The shape is the A-Life and Oblivion sense-think-act arbitration: the drives
compete, and the strongest live drive wins.  The priority is the threat
first, then the needs with thirst before hunger, then the environment
boundary, then rest.  No threshold lives here: every threshold is an
argument, so the species rules and the caller own the policy.

The perception is [suitability, threat, need, heardCall] with the need pair
[hungerNeed, thirstNeed].  The species rules are [gregariousness].

Arguments:
  0: Array  - the perception vector
  1: Array  - the species rules [gregariousness]
  2: Array  - the thresholds [flee, freeze, drink, forage, boundary]

Returns:
  Array - [action, callPlan, movement] where action is 0 rest, 1 forage,
          2 drink, 3 flee, 4 freeze; callPlan is the call type or -1;
          movement is 0 stay, 1 move to resource, 2 avoid
*/

params [
    ["_perception", [], [[]]],
    ["_species", [], [[]]],
    ["_thresholds", [], [[]]]
];

private _suitability = 0;
private _threat = 0;
private _hunger = 0;
private _thirst = 0;
if ((count _perception) >= 1) then { _suitability = _perception select 0; };
if ((count _perception) >= 2) then { _threat = _perception select 1; };
if ((count _perception) >= 3) then {
    private _need = _perception select 2;
    if ((_need isEqualType []) && ((count _need) >= 2)) then {
        _hunger = _need select 0;
        _thirst = _need select 1;
    };
};

private _gregariousness = 0;
if ((count _species) >= 1) then { _gregariousness = (_species select 0) max 0; };

private _flee = 0.7;
private _freeze = 0.3;
private _drink = 0.5;
private _forage = 0.2;
private _boundary = 0.3;
if ((count _thresholds) >= 1) then { _flee = _thresholds select 0; };
if ((count _thresholds) >= 2) then { _freeze = _thresholds select 1; };
if ((count _thresholds) >= 3) then { _drink = _thresholds select 2; };
if ((count _thresholds) >= 4) then { _forage = _thresholds select 3; };
if ((count _thresholds) >= 5) then { _boundary = _thresholds select 4; };

private _action = 0;
private _callPlan = -1;
private _movement = 0;

if (_threat > _flee) then {
    _action = 3;
    _movement = 2;
    _callPlan = "alarm";
} else {
    if (_threat > _freeze) then {
        _action = 4;
    } else {
        if (_thirst > _drink) then {
            _action = 2;
            _movement = 1;
        } else {
            if (_hunger > _forage) then {
                _action = 1;
                _movement = 1;
            } else {
                if (_suitability < _boundary) then {
                    _movement = 2;
                } else {
                    if (_gregariousness >= 0.5) then { _callPlan = "contact"; };
                };
            };
        };
    };
};

[_action, _callPlan, _movement]
