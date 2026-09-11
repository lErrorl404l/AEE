#include "..\script_component.hpp"

/*
Author: AEE
Description: Accumulates surface wetness from rain and dries it by evaporation driven by temperature and wind.
Arguments: None
Return Value: NUMBER: surface wetness 0..1
Example: [] call aee_environmental_fnc_calculateSurfaceWetness
Public: No
*/

private _wetness = missionNamespace getVariable [QEGVAR(core,surfaceWetness), 0];
private _temp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _windSpeed = vectorMagnitude wind;

// Rain accumulation per tick
_wetness = _wetness + (rain * 0.01);

// Evaporation: temperature and wind driven
private _evaporation = 0.002 + (((_temp max 0) / 100) * 0.01) + ((_windSpeed / 20) * 0.01);
_wetness = _wetness - _evaporation;

_wetness = _wetness max 0 min 1;

missionNamespace setVariable [QEGVAR(core,surfaceWetness), _wetness];

_wetness
