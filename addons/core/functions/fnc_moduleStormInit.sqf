#include "..\script_component.hpp"
/*
    AEE — Storm Control Module Init

    EDEN / Zeus module handler. Reads the module arguments and publishes the
    storm override into AEE's shared state:

      aee_core_stormOverrideType       — "thunderstorm", "sandstorm",
                                         "snowstorm", or "clear"
      aee_core_stormOverrideIntensity  — 0..1 severity
      aee_core_stormOverrideUntil      — mission time (seconds) when the
                                         override expires

    Intended consumption: the fx addon (addons/fx) reads these variables in
    fnc_triggerSevereWeatherFX.sqf and forces the matching severe-weather
    effect while time < aee_core_stormOverrideUntil. The maintainer decides
    how the fx addon consumes the override; this function only publishes it.

    The module logic is deleted after reading, so the module cannot be
    re-triggered by toggling it in Zeus.
*/

params ["_logic", "_isActivating"];

if (!_isActivating) exitWith {};

private _stormType = _logic getVariable ["stormType", "thunderstorm"];
private _intensity = _logic getVariable ["intensity", 0.5];
private _durationMin = _logic getVariable ["durationMin", 5];

_intensity = _intensity max 0 min 1;
_durationMin = _durationMin max 0;

missionNamespace setVariable [QEGVAR(core,stormOverrideType), _stormType];
missionNamespace setVariable [QEGVAR(core,stormOverrideIntensity), _intensity];
missionNamespace setVariable [QEGVAR(core,stormOverrideUntil), time + (_durationMin * 60)];

deleteVehicle _logic;
