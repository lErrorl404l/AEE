#include "..\script_component.hpp"
/*
The environment a shot is fired in (issue #167).

The ballistics addon reads the environment from the AEE core state when
that addon is loaded, and from the International Standard Atmosphere
when it is not. That is the whole of its environment requirement, so the
ballistics addon can be built and used as a standalone mod: it pulls
what it needs and falls back to physics for the rest.

Returns [tempC, pressureHPa, rhoRel], where rhoRel is the air density
relative to the ISA sea level value of 1.225 kg/m3.
*/
private _tempC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _pressure = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013.25];
private _density = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];

if !(_tempC isEqualType 0) then { _tempC = 15; };
if !(_pressure isEqualType 0) then { _pressure = 1013.25; };
if !(_density isEqualType 0) then { _density = 1.225; };
if (_density <= 0.01) then { _density = 1.225; };

[_tempC, _pressure, (_density / 1.225) max 0.1 min 2.0]
