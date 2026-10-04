#include "..\script_component.hpp"

/*
Start the wildlife client tick and the gunfire report handler.

Client-only and idempotent: a second call does nothing while the PFH is live.
The manifest is loaded once.  The FiredMan handler reports one bounded
stimulus through the reusable substrate.

Arguments: none.

Returns:
  Nothing.
*/

if (!hasInterface) exitWith {};
if (!isNil QGVAR(ambientPFH)) exitWith {};

private _interval = missionNamespace getVariable [QGVAR(tickInterval), 1.0];
if !(_interval isEqualType 0) then { _interval = 1.0; };
if (_interval < 0.5) then { _interval = 0.5; };

private _manifest = call (compile preprocessFileLineNumbers QPATHTOF(data\sound_manifest.sqf));
missionNamespace setVariable [QGVAR(manifest), _manifest];

GVAR(ambientPFH) = [FUNC(wildlifeTick), _interval] call CBA_fnc_addPerFrameHandler;

GVAR(firedManEH) = addMissionEventHandler ["FiredMan", {
    params ["_unit"];
    if (isNull _unit) exitWith {};
    [getPos _unit, 1] call EFUNC(ai,reportStimulus);
}];

AEE_LOG_INFO("wildlife client tick started")
