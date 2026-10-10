#include "..\script_component.hpp"

/*
Fixed-wing performance state line (issue #22).

Reports the published density altitude and density ratio under the flight
debug gate, so the ambient fixed-wing performance basis is readable.  The line
reads only.

Arguments: none.

Return Value: Nothing.
Public: No
Example: [] call aee_flight_fnc_logFixedWingState
*/

if (!AEE_TRACE_ON) exitWith {};

private _densityAltitudeM = missionNamespace getVariable [QGVAR(currentDensityAltitude), 0];
if !(_densityAltitudeM isEqualType 0) then { _densityAltitudeM = 0; };

private _densityRatio = missionNamespace getVariable [QGVAR(currentDensityRatio), 1];
if !(_densityRatio isEqualType 0) then { _densityRatio = 1; };

// AEE_LOG_DEBUG takes one argument, so the format call is assigned first.
private _message = format ["fixed-wing state | density altitude %1 m | density ratio %2", _densityAltitudeM, _densityRatio];
AEE_LOG_DEBUG(_message);
