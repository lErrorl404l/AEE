#include "..\script_component.hpp"

/*
Call-receive kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
A heard call carries meaning only to a member of the same species or to a
reacting species.  The relation names the caller from the receiver's view:

  0 conspecific, 1 predator, 2 prey, 3 neutral

A neutral relation does not decode any call.  Distance attenuates the
strength, and a call beyond the receiver's audibility is ignored.  The
receiver state is [audibilityRange, gregariousness].  The response codes are:

  0 ignore, 1 go silent, 2 flee, 3 gather or mob, 4 reply, 5 investigate

An alarm to a gregarious conspecific gathers or mobs, a solitary conspecific
flees at a strong call and goes silent at a weak one, a prey flees and a
predator investigates.  A territorial or mating call draws a reply and a
contact or food call draws the group in.  No threshold lives here: the
receiver state carries the audibility and the gregariousness.

Arguments:
  0: String - the call type
  1: Number - the urgency, 0 to 1
  2: Number - the distance to the caller, metres
  3: Number - the relation, 0 to 3
  4: Array  - the receiver state [audibilityRange, gregariousness]

Returns:
  Array - [response, strength]
*/

params [
    ["_callType", "", [""]],
    ["_urgency", 0, [0]],
    ["_distance", 0, [0]],
    ["_relation", 3, [0]],
    ["_receiverState", [], [[]]]
];

private _type = toLower _callType;
private _urg = ((_urgency max 0) min 1);
private _dist = (_distance max 0);

private _range = 200;
private _gregariousness = 0;
if ((count _receiverState) >= 1) then { _range = (_receiverState select 0) max 0; };
if ((count _receiverState) >= 2) then {
    _gregariousness = ((_receiverState select 1) max 0) min 1;
};

// A call beyond the receiver's audibility is not heard.  A neutral relation
// does not decode any call.  An empty type is not a call.
if (_dist > _range) exitWith { [0, 0] };
if (_relation == 3) exitWith { [0, 0] };
if (_type == "") exitWith { [0, 0] };

// Distance attenuates the strength; a call at the receiver is full strength.
private _strength = 0;
if (_range > 0) then {
    _strength = (_urg * (1 - (_dist / _range))) max 0;
};
_strength = _strength min 1;

private _response = 0;
if (_type == "alarm") then {
    if (_relation == 0) then {
        if (_gregariousness >= 0.5) then {
            _response = 3;
        } else {
            if (_strength >= 0.5) then { _response = 2; } else { _response = 1; };
        };
    } else {
        // A prey flees an alarm.  A predator investigates it.
        if (_relation == 2) then { _response = 2; } else { _response = 5; };
    };
} else {
    if (_relation == 0) then {
        if (_type == "territorial") then {
            _response = 4;
        } else {
            if (_type == "mating") then { _response = 4; } else { _response = 3; };
        };
    };
};

[_response, _strength]
