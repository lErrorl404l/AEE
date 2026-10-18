#include "..\script_component.hpp"

/*
AEE - Volcanic Eruption EDEN / Zeus Module Init.

Reads the module arguments, publishes the eruption parameters into AEE's
atmos state, and enables the volcanic model.  The module's own position is
the volcano vent.

Publishes (aee_atmos):
  volcanoPosition, volcanicVEI, volcanicVentAltitude, volcanicAshEmission,
  volcanicSO2Emission, volcanicHeatFlux, volcanicEnabled

Each eruption parameter is the CBA setting of the same name unless the Eden
module attribute overrides it, so a mission that sets nothing gets the
configured value rather than a hard-coded default.

The module logic is deleted after reading, so toggling it in Zeus cannot
re-trigger it.
*/

params ["_logic", "", "_activated"];

if (!_activated) exitWith {};

missionNamespace setVariable [QGVAR(volcanoPosition), getPosASL _logic];
missionNamespace setVariable [QGVAR(volcanicVEI), _logic getVariable ["vei", missionNamespace getVariable [QGVAR(volcanicVEI), 5]]];
missionNamespace setVariable [QGVAR(volcanicVentAltitude), _logic getVariable ["ventAltitude", missionNamespace getVariable [QGVAR(volcanicVentAltitude), 2000]]];
missionNamespace setVariable [QGVAR(volcanicAshEmission), _logic getVariable ["ashEmission", missionNamespace getVariable [QGVAR(volcanicAshEmission), 5.0e6]]];
missionNamespace setVariable [QGVAR(volcanicSO2Emission), _logic getVariable ["so2Emission", missionNamespace getVariable [QGVAR(volcanicSO2Emission), 5.0e5]]];
missionNamespace setVariable [QGVAR(volcanicHeatFlux), _logic getVariable ["heatFlux", missionNamespace getVariable [QGVAR(volcanicHeatFlux), 1.0e11]]];
missionNamespace setVariable [QGVAR(volcanoLatitude), _logic getVariable ["latitude", 45]];
missionNamespace setVariable [QGVAR(volcanoSlope), _logic getVariable ["slope", 15]];
missionNamespace setVariable [QGVAR(volcanicEnabled), true];

deleteVehicle _logic;
