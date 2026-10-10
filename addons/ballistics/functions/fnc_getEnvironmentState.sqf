#include "..\script_component.hpp"
/*
The environment a shot is fired in (issue #167).

The ballistics addon reads the environment from the AEE core state when
that addon is loaded, and from the International Standard Atmosphere
when it is not. That is the whole of its environment requirement, so the
ballistics addon can be built and used as a standalone mod: it pulls
what it needs and falls back to physics for the rest.

Returns [tempC, pressureHPa, rhoRel], where rhoRel is the air density
relative to the ISA sea level value of AERO_ISA_SEA_LEVEL_DENSITY kg/m3.
*/
private _tempC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _pressure = missionNamespace getVariable [QEGVAR(core,currentPressure), ISA_SEA_LEVEL_PRESSURE_HPA];
private _density = missionNamespace getVariable [QEGVAR(core,currentAirDensity), AERO_ISA_SEA_LEVEL_DENSITY];

if !(_tempC isEqualType 0) then { _tempC = 15; };
if !(_pressure isEqualType 0) then { _pressure = ISA_SEA_LEVEL_PRESSURE_HPA; };
if !(_density isEqualType 0) then { _density = AERO_ISA_SEA_LEVEL_DENSITY; };
if (_density <= 0.01) then { _density = AERO_ISA_SEA_LEVEL_DENSITY; };

[_tempC, _pressure, (_density / AERO_ISA_SEA_LEVEL_DENSITY) max 0.1 min 2.0]
