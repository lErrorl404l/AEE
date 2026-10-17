#include "..\..\script_component.hpp"
/*
Author: AEE
Description: Clear-air (haze) extinction from relative humidity.

Hygroscopic aerosols swell as the humidity rises and scatter more light.
NOAA's operational visibility diagnostic (UPP CALVIS_GSD, Benjamin, Brown
& Smirnova) gives the clear-air visibility from the near-surface RH:
  q = clamp(RH / 100 - 0.15, 0, 0.8),   vis_RH = 90 exp(-2.5 q)  km
(90 km in dry air, 12.2 km at saturation).  The extinction is the WMO
meteorological optical range relation sigma = 3.0 / vis (5 % contrast).

Arguments: None
Return Value: NUMBER: haze extinction, per km (also aee_core_currentHaze)
Public: No
*/
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_humidity isEqualType 0) then { _humidity = 50; };
private _q = (((_humidity / 100) - 0.15) max 0) min 0.8;
private _visKm = 90 * exp (-2.5 * _q);
private _haze = 3.0 / _visKm;
missionNamespace setVariable [QEGVAR(core,currentHaze), _haze];
missionNamespace setVariable [QEGVAR(core,currentHazeVisibility), _visKm];
_haze
