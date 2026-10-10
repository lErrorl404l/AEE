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
    case "Snow":   { 0.3 - ((_snowDepth / 10) min 0.25) };
    default        { 1.0 }; // Normal
};

// Saturated ground below a footing loses bearing capacity (issue #26). The
// water table sets the pore-water pressure, which reduces the effective
// stress at the foundation depth (Terzaghi 1943, the effective-stress
// principle). A water table at the surface takes the bearing to half; one at
// or below the foundation depth leaves it intact. The foundation depth is a
// representative shallow footing, 1 m, and the surface reduction is the
// issue's 0.5 end of its 0.5 to 0.7 range. The producer is
// aee_hydrology's river tick; on the first tick, or with hydrology off, the
// read falls back deep and the factor is 1.
private _waterTableDepth = missionNamespace getVariable [QEGVAR(core,waterTableDepth_m), 30];
if !(_waterTableDepth isEqualType 0) then { _waterTableDepth = 30; };
private _foundationDepth = 1.0;
if (_waterTableDepth < _foundationDepth) then {
    _bearing = _bearing * (0.5 + (0.5 * (_waterTableDepth / _foundationDepth)));
};

_bearing = _bearing max 0.1 min 1.0;

missionNamespace setVariable [QGVAR(soilBearing), _bearing];

// Write ACE3 compat variable if its namespace is available
if (!isNil "ace_terrain") then {
    missionNamespace setVariable ["ace_terrain_soilBearing", _bearing];
};

_bearing
