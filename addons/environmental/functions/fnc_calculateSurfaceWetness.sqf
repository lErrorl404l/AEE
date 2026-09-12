#include "..\script_component.hpp"

/*
Author: AEE
Description: Surface wetness is a balance of wetting (rain + dew) and drying (evaporation driven by temperature, wind, humidity, sun).
Arguments: None
Return Value: NUMBER: surface wetness 0..1
Example: [] call aee_environmental_fnc_calculateSurfaceWetness
Public: No
*/

private _wetness   = missionNamespace getVariable [QEGVAR(core,surfaceWetness), 0];
private _temp      = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _humidity  = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _windSpeed = vectorMagnitude wind;
private _overcast  = overcast;
private _rainRate  = rain;
private _interval  = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];

if (isNil "_rainRate") then { _rainRate = 0; };

// ─── Wetting — rain ──────────────────────────────────────────────────────
_wetness = _wetness + (_rainRate * 0.05);

// ─── Dew — Magnus dew point (Sonntag 1990, over water) ───────────────────
// Clear calm night, surface colder than the dew point: dew forms.
private _gamma = (ln (_humidity / 100)) + (17.62 * _temp / (243.12 + _temp));
private _dewPoint = 243.12 * _gamma / (17.62 - _gamma);
if (_temp < _dewPoint && _overcast < 0.3 && _windSpeed < 3) then {
    _wetness = _wetness + 0.02;
};

// ─── Drying — evaporation, per-hour rate scaled by the tick ──────────────
private _evapFactor = (0.01 + 0.001 * _windSpeed) * (1 + ((_temp - 15) * 0.05));
_wetness = _wetness - (_wetness * _evapFactor * (_interval / 3600));

_wetness = _wetness max 0 min 1;

missionNamespace setVariable [QEGVAR(core,surfaceWetness), _wetness];

_wetness
