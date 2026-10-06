#include "..\script_component.hpp"

/*
Perception kernel (wildlife ecology).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.
It folds the environment sample, the habitat score, the species rules and the
animal state into the perception vector the think kernel consumes.  No
threshold lives here: every threshold comes from the species rules and the
caller, so the ecology owns the policy.

The state is [hunger, thirst, threat, timeBin, weather, acousticLevel].  The
acousticLevel element is the propagated auditory stimulus from the acoustic
kernel, so a real, attenuated gunshot raises the perceived threat.  The
heardCall is the decoded call from the call-receive kernel, [callType,
urgency], or empty.

The need element is the pair [hungerNeed, thirstNeed], each the need pressure
above the species threshold, so the think kernel can order thirst before
hunger.  A need at or below its threshold is 0.

Arguments:
  0: Array  - the environment sample, empty means no local sample
  1: Number - the habitat score, 0 to 1
  2: Array  - the species rules [threatSensitivity, hungerThreshold,
              thirstThreshold, alarmWeight]
  3: Array  - the state [hunger, thirst, threat, timeBin, weather,
              acousticLevel]
  4: Array  - the decoded heard call [callType, urgency], or empty

Returns:
  Array - the perception vector [suitability, threat, need, heardCall]
*/

params [
    ["_environment", [], [[]]],
    ["_habitatScore", 0, [0]],
    ["_species", [], [[]]],
    ["_state", [], [[]]],
    ["_heardCall", [], [[]]]
];

private _hunger = 0;
private _thirst = 0;
private _threat = 0;
private _acoustic = 0;
if ((count _state) >= 1) then { _hunger = (_state select 0) max 0 min 1; };
if ((count _state) >= 2) then { _thirst = (_state select 1) max 0 min 1; };
if ((count _state) >= 3) then { _threat = (_state select 2) max 0 min 1; };
if ((count _state) >= 6) then { _acoustic = (_state select 5) max 0 min 1; };

private _threatSensitivity = 1;
private _hungerThreshold = 0.4;
private _thirstThreshold = 0.6;
private _alarmWeight = 1;
if ((count _species) >= 1) then { _threatSensitivity = (_species select 0) max 0; };
if ((count _species) >= 2) then { _hungerThreshold = (_species select 1) max 0 min 1; };
if ((count _species) >= 3) then { _thirstThreshold = (_species select 2) max 0 min 1; };
if ((count _species) >= 4) then { _alarmWeight = (_species select 3) max 0; };

// Suitability is the habitat score, but only with a local sample: no sample,
// no ground truth, so the animal does not trust the patch.
private _suitability = 0;
if (_environment isNotEqualTo []) then {
    _suitability = (_habitatScore max 0) min 1;
};

// Threat is the strongest of the state threat, the propagated acoustic
// stimulus and a decoded alarm.
private _perceivedThreat = _threat;
_perceivedThreat = _perceivedThreat max (_acoustic * _threatSensitivity);

if ((_heardCall isEqualType []) && ((count _heardCall) >= 1)) then {
    if ((toLower (_heardCall select 0)) == "alarm") then {
        private _urgency = 1;
        if ((count _heardCall) >= 2) then { _urgency = (_heardCall select 1) max 0 min 1; };
        _perceivedThreat = _perceivedThreat max (_urgency * _alarmWeight);
    };
};
_perceivedThreat = _perceivedThreat max 0 min 1;

// Need is the pressure above the species threshold, per drive.
private _hungerNeed = 0;
if (_hunger > _hungerThreshold) then { _hungerNeed = _hunger; };
private _thirstNeed = 0;
if (_thirst > _thirstThreshold) then { _thirstNeed = _thirst; };

[_suitability, _perceivedThreat, [_hungerNeed, _thirstNeed], _heardCall]
