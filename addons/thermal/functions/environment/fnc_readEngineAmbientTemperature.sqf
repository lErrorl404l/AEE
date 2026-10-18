#include "..\..\script_component.hpp"

/*
Engine ambient temperature: the black-surface and white-surface pair (issue:
unused weather levers).

`ambientTemperature` is a nular returning
[airTemperature, blackSurfaceTemperature, whiteSurfaceTemperature] in Celsius
(command DB `ambientTemperature`, acemod/arma3-wiki v2.22, Arma 3 2.06).  The
engine derives the black (sunlit) and white (shaded) surface temperatures from
its own solar and ground model, so the pair is ground truth that AEE does not
have to re-derive.

AEE computes its own surface temperature in FUNC(calculateThermalCrossover),
which is the value its consumers read.  This bridge publishes the engine pair
beside it, on the core bus, so a consumer can compare or substitute without
reading the engine command itself.  It WRITES nothing: there is no
`setAmbientTemperature` (the research records the engine-absent setter).

Reads:  ambientTemperature (engine)
Sets:   aee_core_engineAirTemperature, aee_core_engineBlackSurfaceTemperature,
        aee_core_engineWhiteSurfaceTemperature
Example: [] call aee_thermal_fnc_readEngineAmbientTemperature;
Public: No
*/

private _temps = ambientTemperature;
if !(_temps isEqualType []) exitWith {};
if ((count _temps) < 3) exitWith {};

private _air = _temps select 0;
private _black = _temps select 1;
private _white = _temps select 2;

if (_air isEqualType 0) then {
    missionNamespace setVariable [QEGVAR(core,engineAirTemperature), _air];
};
if (_black isEqualType 0) then {
    missionNamespace setVariable [QEGVAR(core,engineBlackSurfaceTemperature), _black];
};
if (_white isEqualType 0) then {
    missionNamespace setVariable [QEGVAR(core,engineWhiteSurfaceTemperature), _white];
};
