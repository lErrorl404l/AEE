#include "..\..\script_component.hpp"

/*
Dust suppression factor (0–1) for vehicle dust kickup.

Ground moisture and precipitation determine how much dust vehicles kick up:
  0.0 = fully suppressed (no dust)
  1.0 = no suppression (maximum dust)

Stored in GVAR(dustSuppression) and ace_weather_dustSuppression for
consumption by particle and dust-kickup systems.
*/

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _rain = rain;

// ─── Base suppression per ground state ──────────────────────────────────
private _suppression = switch (_groundState) do {
    case "Snow":   { 0.0 };
    case "Mud":    { 0.0 };
    case "Frozen": { 0.8 };
    case "Dusty":  { 1.0 };
    default        { 0.6 * (1 - (_rain min 1)) }; // Normal: lerp 0.6→0.0 with rain
};

// ─── Additional suppression — rain > 0.1 cuts further ───────────────────
if (_rain > 0.1) then {
    _suppression = (_suppression - _rain * 2) max 0;
};

_suppression = _suppression max 0 min 1;

missionNamespace setVariable [QEGVAR(core,dustSuppression), _suppression];
missionNamespace setVariable ["ace_weather_dustSuppression", _suppression];

_suppression
