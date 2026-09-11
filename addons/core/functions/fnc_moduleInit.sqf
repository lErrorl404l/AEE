#include "..\script_component.hpp"

params ["_logic", "", "_activated"];

if (!_activated) exitWith {};

missionNamespace setVariable [QGVAR(moduleBiomeOverride),   _logic getVariable ["biomeOverride", ""]];
missionNamespace setVariable [QGVAR(moduleTempOffset),      _logic getVariable ["tempOffset", 0]];
missionNamespace setVariable [QGVAR(modulePrecipBias),      _logic getVariable ["precipBias", 1]];
missionNamespace setVariable [QGVAR(moduleWindMultiplier),  _logic getVariable ["windMultiplier", 1]];
missionNamespace setVariable [QGVAR(moduleUpdateInterval),  _logic getVariable ["updateInterval", 5]];
