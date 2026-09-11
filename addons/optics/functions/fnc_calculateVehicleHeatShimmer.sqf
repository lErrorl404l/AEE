#include "..\script_component.hpp"

/*
Heat shimmer intensity near vehicle engine compartments (0–1).

When a vehicle's engine is running, hot exhaust and cooling airflow create
refractive distortion above the engine bay / exhaust.  Intensity scales
with engine load (speed / throttle) and the temperature differential
between exhaust and ambient air.

High wind disperses the hot-air layer, reducing the effect.

Stored in QGVAR(vehicleHeatShimmerIntensity) for consumption by
visual post-process systems.
*/

params [["_unit", call CBA_fnc_currentUnit, [objNull]]];

if (!EGVAR(core,opticsEnabled)) exitWith {
    missionNamespace setVariable [QGVAR(vehicleHeatShimmerIntensity), 0];
    0
};

if (isNil "_unit" || !alive _unit) exitWith { 0 };

private _vehicle = vehicle _unit;

if (_vehicle isEqualTo _unit) exitWith {
    missionNamespace setVariable [QGVAR(vehicleHeatShimmerIntensity), 0];
    0
};

if (!canMove _vehicle) exitWith {
    missionNamespace setVariable [QGVAR(vehicleHeatShimmerIntensity), 0];
    0
};

private _engineOn     = isEngineOn _vehicle;
private _speed        = abs speed _vehicle;
private _temp         = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _windSpd      = vectorMagnitude wind;

if (isNil "_temp")    then { _temp = 15; };
if (isNil "_windSpd") then { _windSpd = 0; };

private _intensity = 0;
if (_engineOn) then {
    // Thermal contrast: cooler ambient → more visible shimmer
    private _tempContrast = ((40 - _temp) / 40) max 0.2 min 1;
    // Load factor from speed
    private _load = (_speed / 100) min 1;
    _intensity = (0.3 + _load * 0.7) * _tempContrast;
};

// Wind disperses the hot-air boundary layer
if (_windSpd > 2) then {
    _intensity = _intensity * (1 - ((_windSpd / 20) min 0.8));
};

_intensity = _intensity max 0 min 1;

missionNamespace setVariable [QGVAR(vehicleHeatShimmerIntensity), _intensity];

_intensity
