#include "..\script_component.hpp"

/*
Soil moisture and evaporation.

Rain soaks the ground; evaporation (driven by temperature, wind,
humidity, and solar radiation) dries it. Moist soil raises the relative
humidity, closing the water cycle: precipitation -> soil -> evaporation
-> humidity -> cloud.

Evaporation uses the FAO-56 Penman-Monteith reference evapotranspiration
(ET0) form (Allen et al. 1998), scaled to the game tick. Warm, windy,
dry, sunny air dries the ground faster.

State: aee_core_soilMoisture (0..1).
*/

private _moisture = missionNamespace getVariable [QGVAR(soilMoisture), 0.2];
private _rainRate  = rain;
private _temp      = EGVAR(core,currentTemperature);
private _wind      = vectorMagnitude wind;
private _humidity  = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _solar     = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0.5];
if (isNil "_temp") then { _temp = 15; };

// soak from rain, capped at field capacity
_moisture = _moisture + (_rainRate * 0.005);
// evaporation: FAO-56 Penman-Monteith ET0, scaled to the game tick
private _slope = 4098 * 0.6108 * exp((17.27 * _temp) / (_temp + 237.3)) / ((_temp + 237.3) ^ 2);
private _es    = 0.6108 * exp((17.27 * _temp) / (_temp + 237.3));
private _ea    = _es * (_humidity / 100);
private _gamma = 0.000665 * 101.3;
private _Rn    = _solar * 0.1;
private _u2    = _wind;
private _evap  = ((0.408 * _slope * _Rn) + (_gamma * (37 / (_temp + 273.15)) * _u2 * (_es - _ea))) / (_slope + (_gamma * (1 + 0.34 * _u2)));
_evap = (_evap max 0) * 0.0002;
_moisture = (_moisture - _evap) max 0 min 1;

missionNamespace setVariable [QGVAR(soilMoisture), _moisture];

// moist soil contributes to the relative humidity
_humidity = (_humidity + (_moisture * 10)) min 100;
missionNamespace setVariable [QEGVAR(core,currentHumidity), _humidity];

_moisture
