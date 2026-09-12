#include "..\script_component.hpp"

/*
Surface traction coefficients (0–1) for wheeled and tracked vehicles.

Ground state is mapped to a base traction pair; these are further reduced
by accumulated rainfall (which lubricates the surface) and shaped by a
tyre/terrain slip curve (F = mu * W * (1 - exp(-k * s))).

Stored in GVAR(currentTractionWheeled) and GVAR(currentTractionTracked)
for consumption by vehicle mobility systems, plus GVAR(tractionForce)
and GVAR(wheelSlip) for the slip-curve state.
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

// ─── Slip-curve model ────────────────────────────────────────────────────
// F = mu * W * (1 - exp(-k * s));  k ~ 10 for dry surfaces.
private _veh = vehicle (call CBA_fnc_currentUnit);
private _groundSpeed = (speed _veh) / 3.6; // km/h to m/s
private _wheelSpeed = (velocity _veh) vectorDotProduct (vectorDir _veh);
private _slip = 0;
if (_wheelSpeed > 0.1) then {
    _slip = ((_wheelSpeed - _groundSpeed) / _wheelSpeed) max 0 min 1;
};

private _k = 10;
private _slipFactor = 1 - exp(-_k * _slip);

_wheeled = _wheeled * _slipFactor;
_tracked = _tracked * _slipFactor;

private _mu = [_wheeled, _tracked] select (_veh isKindOf "Tank");
private _tractionForce = _mu * (getMass _veh);

missionNamespace setVariable [QGVAR(currentTractionWheeled), _wheeled];
missionNamespace setVariable [QGVAR(currentTractionTracked), _tracked];
missionNamespace setVariable [QGVAR(tractionForce), _tractionForce];
missionNamespace setVariable [QGVAR(wheelSlip), _slip];
