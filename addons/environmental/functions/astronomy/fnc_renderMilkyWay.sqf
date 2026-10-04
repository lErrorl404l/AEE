#include "..\..\script_component.hpp"

/*
Milky Way band renderer (night-sky debug).

Registers the client-side sampler once and the one Draw3D handler that draws
the band.  The sampler reads the gates and the force hooks; the handler draws
only QGVAR(milkyWaySamples) as line segments, so no object is created.

Registered once, idempotently (the isNil guards are required by the
validate_cba gate).  No server-side draw and no non-local object.
*/

if (!hasInterface) exitWith {};
if (!isNil QGVAR(milkyWayPFH)) exitWith {};

missionNamespace setVariable [QGVAR(milkyWaySamples), []];

GVAR(milkyWayPFH) = [FUNC(updateMilkyWay), MILKY_WAY_TICK] call CBA_fnc_addPerFrameHandler;
if (isNil QGVAR(milkyWayEH)) then {
    GVAR(milkyWayEH) = addMissionEventHandler ["Draw3D", { call FUNC(drawMilkyWay) }];
};
AEE_LOG_INFO("milky way: band PFH registered");
