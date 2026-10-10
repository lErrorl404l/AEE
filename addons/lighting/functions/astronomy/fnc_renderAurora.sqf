#include "..\..\script_component.hpp"

/*
Aurora curtain renderer (night-sky debug).

Registers the client-side aurora worker once.  The worker reads the
space-weather aurora state and the debug force hooks, then draws the curtain
with local particle sources, so the effect is cosmetic and client-only.

Registered once, idempotently (the isNil guard is required by the
validate_cba gate).  No server-side draw and no non-local object.
*/

if (!hasInterface) exitWith {};
if (!isNil QGVAR(auroraPFH)) exitWith {};

missionNamespace setVariable [QGVAR(auroraSources), []];

GVAR(auroraPFH) = [FUNC(updateAurora), AURORA_TICK] call CBA_fnc_addPerFrameHandler;
AEE_LOG_INFO("aurora: curtain PFH registered");
