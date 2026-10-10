#include "..\script_component.hpp"

/*
AEE - Volcanic Eruption EDEN / Zeus Module Init.

Reads the module arguments, publishes the eruption parameters into AEE's
atmos state, and enables the volcanic model.  The module's own position is
the volcano vent.

Publishes (aee_atmos):
  volcanoPosition, volcanoVEI, volcanoVentAltitude, volcanoAshEmission,
  volcanoSO2Emission, volcanoHeatFlux, volcanicEnabled

The module logic is deleted after reading, so toggling it in Zeus cannot
re-trigger it.
*/

params ["_logic", "", "_activated"];

if (!_activated) exitWith {};

missionNamespace setVariable [QGVAR(volcanoPosition), getPosASL _logic];
missionNamespace setVariable [QGVAR(volcanoVEI), _logic getVariable ["vei", 5]];
missionNamespace setVariable [QGVAR(volcanoVentAltitude), _logic getVariable ["ventAltitude", 2000]];
missionNamespace setVariable [QGVAR(volcanoAshEmission), _logic getVariable ["ashEmission", 5.0e6]];
missionNamespace setVariable [QGVAR(volcanoSO2Emission), _logic getVariable ["so2Emission", 5.0e5]];
missionNamespace setVariable [QGVAR(volcanoHeatFlux), _logic getVariable ["heatFlux", 1.0e11]];
missionNamespace setVariable [QGVAR(volcanoLatitude), _logic getVariable ["latitude", 45]];
missionNamespace setVariable [QGVAR(volcanoSlope), _logic getVariable ["slope", 15]];
missionNamespace setVariable [QGVAR(volcanicEnabled), true];

deleteVehicle _logic;
