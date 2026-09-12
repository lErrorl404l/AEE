#include "..\script_component.hpp"

/*
Stores severe weather colour-correction and blur intensities; application is
handled by fnc_managePostProcess (optics addon).

Reads QGVAR(currentSandstorm), QGVAR(currentBlowingSnow), QGVAR(currentDustDevil).
Gates on GVAR(atmosphericEventsEnabled).  Stores the colour-correction array
and blur intensity for active severe weather, clears both when none active.

Sets: QEGVAR(optics,severeWeatherCC), QEGVAR(optics,severeWeatherBlur)
*/

if (!EGVAR(core,atmosphericEventsEnabled)) exitWith {};

private _sandstorm   = missionNamespace getVariable [QEGVAR(core,currentSandstorm), 0];
private _blowingSnow = missionNamespace getVariable [QEGVAR(core,currentBlowingSnow), 0];
private _dustDevil   = missionNamespace getVariable [QEGVAR(core,currentDustDevil), 0];
private _windSpeed   = vectorMagnitude wind;

if (_sandstorm > 0 || _dustDevil > 0) then {
    missionNamespace setVariable [QEGVAR(optics,severeWeatherCC), [0.8, 0.6, 0.0, [0.3, 0.25, 0.15, 0.0], [1.0, 0.85, 0.6, 0.5], [0.5, 0.5, 0.5, 0.0]]];
    missionNamespace setVariable [QEGVAR(optics,severeWeatherBlur), _windSpeed / 10];
    } else {
        if (_blowingSnow > 0) then {
        missionNamespace setVariable [QEGVAR(optics,severeWeatherCC), [1.0, 1.0, 0.0, [0.0, 0.0, 0.0, 0.0], [0.6, 0.65, 0.7, 0.5], [0.5, 0.5, 0.5, 0.0]]];
        missionNamespace setVariable [QEGVAR(optics,severeWeatherBlur), _windSpeed / 10];
    } else {
        missionNamespace setVariable [QEGVAR(optics,severeWeatherCC), []];
        missionNamespace setVariable [QEGVAR(optics,severeWeatherBlur), 0];
    };
};
