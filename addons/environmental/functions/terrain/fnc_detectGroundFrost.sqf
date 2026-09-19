#include "..\..\script_component.hpp"

/*
Ground frost detection on terrain surfaces.

Frost forms on a clear, calm night when the surface cools below 0 C
and the air is near saturation.  Uses the Magnus dew-point formula
(Alduchov & Eskridge 1996):

  g  = ln(RH/100) + (17.62 x T) / (243.12 + T)
  Td = (243.12 x g) / (17.62 - g)

Conditions for frost:
  Surface temperature <= 0 C
    (surface approx air - 2 C on clear calm nights, Brunt radiative cooling)
  Dew-point depression < 2 C   (air near saturation)
  Overcast < 0.3              (clear sky for radiative cooling)
  Wind < 5 m/s                (light wind, strong wind mixes the air)

Intensity (0 to 1):
  (0 - surfaceTemp) x (1 - depression/5), clamped to 0 to 1.

Stores:
  QGVAR(groundFrostIntensity) float, 0 to 1
  QGVAR(groundFrostPresent)   bool
Returns QGVAR(groundFrostIntensity)
*/

params [];

if (!(missionNamespace getVariable [QGVAR(groundFrostEnabled), true])) exitWith {
    missionNamespace setVariable [QGVAR(groundFrostIntensity), 0];
    missionNamespace setVariable [QGVAR(groundFrostPresent), false];
    0
};

// Read environment
private _temp     = missionNamespace getVariable [QEGVAR(core,currentTemperature), 20];
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _overcast = missionNamespace getVariable [QEGVAR(core,overcast), 0];
private _wind     = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];

// Dew point (Magnus, Alduchov & Eskridge 1996)
private _gamma      = ln (_humidity / 100) + (17.62 * _temp) / (243.12 + _temp);
private _dewPoint   = (243.12 * _gamma) / (17.62 - _gamma);
private _depression = _temp - _dewPoint;

// Surface temperature (Brunt radiative cooling)
private _surfaceTemp = _temp;
if (_overcast < 0.3 && _wind < 5) then {
    _surfaceTemp = _temp - 2;
};

// Frost conditions
private _intensity = 0;
if (_surfaceTemp <= 0 && _depression < 2 && _overcast < 0.3 && _wind < 5) then {
    _intensity = (0 - _surfaceTemp) * (1 - _depression / 5);
    _intensity = _intensity max 0 min 1;
};

missionNamespace setVariable [QGVAR(groundFrostIntensity), _intensity];
missionNamespace setVariable [QGVAR(groundFrostPresent), _intensity > 0];

_intensity
