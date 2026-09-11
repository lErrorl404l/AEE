#include "..\script_component.hpp"

/*
Soil bearing strength (0.1–1.0) for engineering and vehicle recovery.

A simple multiplier reflecting how well the ground supports heavy loads:
  1.0 = firm, load-bearing ground
  0.1 = near-zero support (deep mud, soft snow)

Reduced by wet/muddy conditions that soften the surface and by deep
snow that compresses under load. Frozen ground remains firm but is
brittle (slightly derated). Dusty surfaces lose some bearing from
loose unconsolidated material.

ponytail: a simple multiplier, not a civil-engineering bearing capacity model.
Stored in QGVAR(soilBearing). Also written to ace_terrain_soilBearing for
compat with ACE3 vehicle recovery systems.
*/

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _rainAccum   = missionNamespace getVariable [QEGVAR(core,rainAccum), 0];
private _snowDepth   = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];

private _bearing = switch (_groundState) do {
    case "Mud":    { 0.4 - ((_rainAccum * 0.2) min 0.4) };
    case "Frozen": { 0.9 };
    case "Dusty":  { 0.7 };
    case "Snow":   { 0.3 min (_snowDepth / 10) };
    default        { 1.0 }; // Normal
};

_bearing = _bearing max 0.1 min 1.0;

missionNamespace setVariable [QGVAR(soilBearing), _bearing];

// Write ACE3 compat variable if its namespace is available
if (!isNil "ace_terrain") then {
    missionNamespace setVariable ["ace_terrain_soilBearing", _bearing];
};

_bearing
