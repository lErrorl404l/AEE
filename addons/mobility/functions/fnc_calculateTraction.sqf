#include "..\script_component.hpp"

/*
Surface traction coefficients (0–1) for wheeled and tracked vehicles.

Ground state is mapped to a base traction pair; these are further reduced
by accumulated rainfall (which lubricates the surface).

Stored in GVAR(currentTractionWheeled) and GVAR(currentTractionTracked)
for consumption by vehicle mobility systems.
*/

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _rainAccum = missionNamespace getVariable [QEGVAR(core,rainAccum), 0];

// ─── Base values per ground state ────────────────────────────────────────
private _wheeled = switch (_groundState) do {
    case "Snow":   { 0.2  };
    case "Mud":    { 0.35 };
    case "Frozen": { 0.4  };
    case "Dusty":  { 0.5  };
    default        { 0.85 }; // Normal
};

private _tracked = switch (_groundState) do {
    case "Snow":   { 0.5  };
    case "Mud":    { 0.6  };
    case "Frozen": { 0.65 };
    case "Dusty":  { 0.7  };
    default        { 0.9  }; // Normal
};

// ─── Rain reduces wheeled traction (lubricated surface) ──────────────────
if (_rainAccum > 0) then {
    _wheeled = _wheeled * (1 - _rainAccum * 0.5);
};

_wheeled = _wheeled max 0.05 min 1.0;
_tracked = _tracked max 0.05 min 1.0;

missionNamespace setVariable [QGVAR(currentTractionWheeled), _wheeled];
missionNamespace setVariable [QGVAR(currentTractionTracked), _tracked];
