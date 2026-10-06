#include "..\script_component.hpp"

/*
Armour state line.

One grep of "armour state" answers the module's state.  Read only: the
only write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.

The line carries the two gate switches, the debug switch, and the resolved
protection of the current vehicle from the same derivation the gate uses.  The
derivation is a pure read; the line never attaches a handler and never changes
the damage path.  Every read has a safe default, so the first line is valid
with no vehicle present.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

private _armourEnabled = missionNamespace getVariable [QGVAR(armourEnabled), true];
if !(_armourEnabled isEqualType true) then { _armourEnabled = true; };

private _penetrationGate = missionNamespace getVariable [QGVAR(penetrationGate), true];
if !(_penetrationGate isEqualType true) then { _penetrationGate = true; };

private _penetrationDebug = missionNamespace getVariable [QGVAR(penetrationDebug), false];
if !(_penetrationDebug isEqualType true) then { _penetrationDebug = false; };

private _vehicleClass = "";
private _protectionLevel = 0;
private _protectionMM = 0;
private _protectionDefeats = "none";

private _vehicle = vehicle player;
if (!isNull _vehicle) then {
    _vehicleClass = typeOf _vehicle;
    private _protection = [_vehicle] call FUNC(deriveProtection);
    if (_protection isEqualType []) then {
        if ((count _protection) >= 3) then {
            _protectionLevel = _protection select 0;
            _protectionMM = _protection select 1;
            _protectionDefeats = _protection select 2;
        };
    };
};

if !(_vehicleClass isEqualType "") then { _vehicleClass = ""; };
if !(_protectionLevel isEqualType 0) then { _protectionLevel = 0; };
if !(_protectionMM isEqualType 0) then { _protectionMM = 0; };
if !(_protectionDefeats isEqualType "") then { _protectionDefeats = "none"; };

private _logMsg = format [
    "armour state | enabled=%1 gate=%2 debug=%3 | vehicle=%4 level=%5 rha=%6mm defeats=%7",
    _armourEnabled, _penetrationGate, _penetrationDebug,
    _vehicleClass, round _protectionLevel,
    round (_protectionMM * 100) / 100, _protectionDefeats
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
