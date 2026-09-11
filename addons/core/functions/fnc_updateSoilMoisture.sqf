#include "..\script_component.hpp"

/*
Soil moisture and evaporation.

Rain soaks the ground; evaporation (driven by temperature and wind)
dries it. Moist soil raises the relative humidity, closing the water
cycle: precipitation -> soil -> evaporation -> humidity -> cloud.

State: aee_core_soilMoisture (0..1).
*/

private _moisture = missionNamespace getVariable [QGVAR(soilMoisture), 0.2];
private _rainRate  = rain;
private _temp      = EGVAR(core,currentTemperature);
private _wind      = vectorMagnitude wind;
if (isNil "_temp") then { _temp = 15; };

// soak from rain, capped at field capacity
_moisture = _moisture + (_rainRate * 0.005);
// evaporation: warm, windy air dries the ground faster
private _evap = ((_temp max 0) * 0.00005) + (_wind * 0.00002);
_moisture = (_moisture - _evap) max 0 min 1;

missionNamespace setVariable [QGVAR(soilMoisture), _moisture];

// moist soil contributes to the relative humidity
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
_humidity = (_humidity + (_moisture * 10)) min 100;
missionNamespace setVariable [QEGVAR(core,currentHumidity), _humidity];

_moisture
