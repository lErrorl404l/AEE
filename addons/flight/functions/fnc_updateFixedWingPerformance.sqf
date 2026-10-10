#include "..\script_component.hpp"

/*
Fixed-wing performance driver (issue #22).

Reads the current atmosphere and publishes the ambient density altitude and
density ratio, so a script or the debug line reads the fixed-wing performance
basis without recomputing it.  The per-aircraft row is the pure kernel
FUNC(calculateFixedWingPerformance).  A caller runs that with the airframe's
own speed, stall speed, propulsion, height and wingspan.

The pressure altitude is the environment reference altitude.  The outside air
temperature and the air density come from the core state that the atmos and
ballistics kernels publish.  The density ratio is rho / 1.225, the same ratio
the helicopter lift and the airframe load kernels read.

Arguments: none.

Return Value: ARRAY - [densityAltitudeM, densityRatio]
Public: No
*/

private _pressureAltitudeM = missionNamespace getVariable [QEGVAR(core,referenceAltitude), 0];
if !(_pressureAltitudeM isEqualType 0) then { _pressureAltitudeM = 0; };

private _oatC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_oatC isEqualType 0) then { _oatC = 15; };

private _density = missionNamespace getVariable [QEGVAR(core,currentAirDensity), AERO_ISA_SEA_LEVEL_DENSITY];
if !(_density isEqualType 0) then { _density = AERO_ISA_SEA_LEVEL_DENSITY; };
if (_density <= 0) then { _density = AERO_ISA_SEA_LEVEL_DENSITY; };

private _densityAltitudeM = [_pressureAltitudeM, _oatC] call FUNC(calculateDensityAltitude);
private _densityRatio = _density / AERO_ISA_SEA_LEVEL_DENSITY;

missionNamespace setVariable [QGVAR(currentDensityAltitude), _densityAltitudeM];
missionNamespace setVariable [QGVAR(currentDensityRatio), _densityRatio];

[_densityAltitudeM, _densityRatio]
