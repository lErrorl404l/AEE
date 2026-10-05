#include "..\script_component.hpp"

/*
Applied airframe penalty state line.

fnc_applyAirframeLoad publishes the lift loss, the drag rise, the ice mass and
the lift ratio it applied.  Nothing read them.  This function is their
consumer: it reports the four published values in one grep-able line.

The line is gated on the mobility debug switch, aee_mobility_logDebug, or the
global aee_core_logDebug.  With the gate off the function returns before it
reads anything, so a forced trace costs nothing in normal play.

Arguments: none.

Return Value: Nothing.
Public: No
Example: [] call aee_mobility_fnc_logAirframeState
*/

if (!AEE_TRACE_ON) exitWith {};

private _liftLoss = missionNamespace getVariable [QGVAR(airLiftLoss), 0];
if !(_liftLoss isEqualType 0) then { _liftLoss = 0; };
private _dragRise = missionNamespace getVariable [QGVAR(airDragRise), 0];
if !(_dragRise isEqualType 0) then { _dragRise = 0; };
private _iceKg = missionNamespace getVariable [QGVAR(airIceMassKg), 0];
if !(_iceKg isEqualType 0) then { _iceKg = 0; };
private _liftRatio = missionNamespace getVariable [QGVAR(airLiftRatioApplied), 0];
if !(_liftRatio isEqualType 0) then { _liftRatio = 0; };

private _logMsg = format [
    "airframe state | applied liftLoss=%1 dragRise=%2 iceMassKg=%3 liftRatio=%4",
    round (_liftLoss * 1000) / 1000, round (_dragRise * 1000) / 1000,
    round (_iceKg * 100) / 100, round (_liftRatio * 1000) / 1000
];

AEE_LOG_DEBUG(_logMsg);
