#include "..\script_component.hpp"

/*
Call-emit kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
A call is a signal: it carries meaning that a receiver decodes from its type,
its urgency and its structure.  It is emitted under conditions, not on an
ambient loop, so no trigger means no call.

The species rules are [gregariousness, seasonActive].  The perception is
[suitability, threat, need, heardCall], the same vector the think kernel
consumes.  The state is [hunger, thirst, threat, timeBin, weather,
acousticLevel].  The trigger names the condition that starts the call:

  "predator"    a predator is perceived -> alarm
  "season"      the season and the condition allow it -> mating
  "conspecific" a conspecific is heard in the patch -> territorial
  "resource"    a resource is found -> food
  "cohesion"    the group holds together -> contact

The urgency scales with the perceived threat and the group's gregariousness,
and it is bounded to 0 to 1.  No threshold lives here: the trigger and the
vectors carry the policy.  A solitary group below the gregariousness floor
does not emit a contact call, and an inactive season does not emit mating.

Arguments:
  0: Array  - the species rules [gregariousness, seasonActive]
  1: Array  - the perception vector [suitability, threat, need, heardCall]
  2: Array  - the state [hunger, thirst, threat, timeBin, weather,
              acousticLevel]
  3: String - the trigger, empty means no call

Returns:
  Array - [callType, urgency] or []
*/

params [
    ["_species", [], [[]]],
    ["_perception", [], [[]]],
    ["_state", [], [[]]],
    ["_trigger", "", [""]]
];

private _type = toLower _trigger;
if (_type == "") exitWith { [] };

private _gregariousness = 0;
if ((count _species) >= 1) then {
    _gregariousness = ((_species select 0) max 0) min 1;
};

private _seasonActive = false;
if ((count _species) >= 2) then {
    private _flag = _species select 1;
    if (_flag isEqualType true) then { _seasonActive = _flag; };
    if (_flag isEqualType 0) then { _seasonActive = (_flag > 0); };
};

private _suitability = 0;
private _threat = 0;
if ((count _perception) >= 1) then {
    _suitability = ((_perception select 0) max 0) min 1;
};
if ((count _perception) >= 2) then {
    _threat = ((_perception select 1) max 0) min 1;
};

private _stateThreat = 0;
if ((count _state) >= 3) then {
    _stateThreat = ((_state select 2) max 0) min 1;
};

private _perceived = (_threat max _stateThreat) min 1;

// The alarm urgency is threat-dominant; the social urgency is group-dominant.
private _alarmUrgency = (((_perceived * 0.7) + (_gregariousness * 0.3)) max 0) min 1;
private _socialUrgency = (((_gregariousness * 0.7) + (_suitability * 0.3)) max 0) min 1;

private _result = [];
if (_type == "predator") then {
    _result = ["alarm", _alarmUrgency];
} else {
    if (_type == "conspecific") then {
        _result = ["territorial", _alarmUrgency];
    } else {
        if (_type == "resource") then {
            _result = ["food", _socialUrgency];
        } else {
            if (_type == "season") then {
                if (_seasonActive) then { _result = ["mating", _socialUrgency]; };
            } else {
                if (_type == "cohesion") then {
                    if (_gregariousness >= 0.5) then {
                        _result = ["contact", _socialUrgency];
                    };
                };
            };
        };
    };
};

_result
