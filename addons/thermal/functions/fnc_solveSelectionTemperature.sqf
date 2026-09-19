#include "..\script_component.hpp"
/*
Per-selection lumped-capacity temperature solve (issue #124).

Solves the equilibrium surface temperature of one model selection and
returns it.  The physics is the standard single-node energy balance
(flat plate, lumped capacity - see Incropera DeWitt, "Fundamentals of
Heat and Mass Transfer", the same model the existing object solver
uses, extended per selection with the material registry):

  q_solar + q_conv + q_rad + q_internal = 0

  q_solar  = alpha * G * exposure             [W/m2]
    alpha   = camo-colour solar absorptance (NASA TP-2005-212792)
    G       = 1000 W/m2 hemispherical (ASTM G173-23, 1001.92 real)
    exposure = 0..1 shading factor (roof 1.0, undercarriage 0.1)
  q_conv   = h * (Ts - Tair)                  [W/m2]
    h       = 5.7 + 3.8 * w                   [W/m2K] McAdams forced+free
              (w = wind m/s; Energies 2022, IES VE)
  q_rad    = eps * sigma * (Ts^4 - MRT^4)     [W/m2]
    sigma   = 5.670374419e-8                  [W/m2K4] CODATA 2022
    MRT     = mean radiant temperature (ISO 7726) - the area-weighted
              temperature of the surrounding SURFACES (ground, sky,
              nearby objects), NOT the air temperature.  On a sunny
              day the ground and nearby vehicles sit far above air, so
              a surface keeps gaining radiation until it approaches
              MRT.  This is the black-globe correction (issue #124).
  q_internal = engine / friction contribution [W/m2] (per selection)

  Equilibrium (q_solar + q_internal balances losses):
    Ts,eq solves alpha*G + q_int = h*(Ts-Tair) + eps*sigma*(Ts^4-MRT^4)
    iterated to convergence (simple fixed-point, 8 iterations).

  Inertia (lumped capacity - the user's mass/insulation refinement):
    tau = m * c / (h * A)    [s]
      m = REAL object mass  (getMass, kg - no invented volume)
      c = material specific heat (registry, J/kgK)
      A = surface area from boundingBox (m2)
    Ts(t) = Ts,eq - (Ts,eq - Ts0) * exp(-dt/tau)

  A painted surface's LWIR emissivity is ~0.9 regardless of colour
  (FLIR T505002 paint table), so eps comes from the material registry
  and only alpha varies with camo.

Arguments:
  0: object (OBJECT)
  1: selection name (STRING) - "" for the whole-object fallback
  2: ambient temperature (NUMBER, Celsius)
  3: wind speed (NUMBER, m/s)
  4: solar flux (NUMBER, W/m2) - 0 at night
  5: shading exposure (NUMBER, 0..1)
  6: internal heat (NUMBER, W/m2) - engine/exhaust/friction, default 0
  7: current temperature (NUMBER, Celsius) - for the inertia term

Return Value:
  NUMBER new surface temperature (Celsius)
*/

params [
    ["_obj", objNull, [objNull]],
    ["_selection", "", [""]],
    ["_tAir", 15, [0]],
    ["_wind", 0, [0]],
    ["_solar", 0, [0]],
    ["_exposure", 1, [0]],
    ["_qInternal", 0, [0]],
    ["_tCurrent", 15, [0]],
    ["_fGround", 0.5, [0]]
];
if (isNull _obj) exitWith { _tAir };

// ─── Material properties ─────────────────────────────────────────────────
// Per-selection class: each selection has its own material (body metal,
// windows glass, tyres rubber, uniform cloth, vest ceramic).  The
// whole-object fallback only applies when the model has no named
// selections at all.
private _class = if (_selection == "") then {
    _obj call EFUNC(material,getObjectMaterial)
} else {
    [_obj, _selection] call FUNC(getSelectionMaterials)
};
private _mat = _class call FUNC(getMaterialThermal);
_mat params ["_eps", "_alpha", "_rho", "_cp", "_k"];

// ─── Solar absorptance: the selection's own colour (NASA) ────────────────
// Resolve the selection index for the texture read: a unit's textures
// ARE its worn clothing (uniform/vest/helmet/goggles), each with its own
// colour and therefore its own solar loading.
private _selIdx = -1;
if (_selection != "") then {
    _selIdx = (selectionNames _obj) find _selection;
};
_alpha = [_obj, _selIdx] call FUNC(getSolarAbsorptance);

// ─── Surface area from bounding box (m2) ─────────────────────────────────
private _bbox = boundingBoxReal _obj;
private _dims = [abs ((_bbox select 1) select 0), abs ((_bbox select 1) select 1), abs ((_bbox select 1) select 2)];
private _area = 2 * ((_dims select 0) * (_dims select 1) + (_dims select 0) * (_dims select 2) + (_dims select 1) * (_dims select 2));

// ─── Convection coefficient (McAdams) ────────────────────────────────────
private _h = 5.7 + 3.8 * (_wind max 0);

// ─── Mean radiant temperature (ISO 7726) ──────────────────────────────────
// The radiation term exchanges against MRT (the surrounding SURFACES),
// not the air temperature.  On a sunny day the ground and nearby
// vehicles sit far above air, so a surface keeps gaining radiation
// until it approaches MRT.  The ground view factor is per selection:
// a tyre/undercarriage sees mostly ground (0.7), a roof mostly sky
// (0.3), a standing soldier 0.5.
private _mrt = [getPosASL _obj, _fGround] call FUNC(calculateMRT);
private _tMrtAbs = _mrt + 273.15;

// ─── Equilibrium temperature (fixed-point iteration) ─────────────────────
private _sigma = 5.670374419e-8;
private _tAbs = _tAir + 273.15;
private _ts = _tCurrent + 273.15;
private _qTotal = _alpha * (_solar max 0) * (_exposure max 0 min 1) + (_qInternal max 0);

for "_i" from 1 to 8 do {
    private _conv = _h * (_ts - _tAbs);
    private _rad = _eps * _sigma * (_ts ^ 4 - _tMrtAbs ^ 4);
    private _f = _qTotal - _conv - _rad;   // residual: drive to 0
    private _df = -(_h + 4 * _eps * _sigma * _ts ^ 3);  // d(residual)/dTs
    if (_df == 0) then { break; };
    _ts = _ts - _f / _df;
    _ts = _ts max (_tAbs - 60) min (_tAbs + 500);  // guard: sane range
};

// ─── Inertia (lumped capacity) ───────────────────────────────────────────
// tau = m*c/(h*A).  Guard division by zero when h or A collapse.
private _mass = _obj call BIS_fnc_getMass;
if !(_mass isEqualType 0) then { _mass = 0; };
private _tau = if (_h > 0 && _area > 0 && _mass > 0) then {
    _mass * _cp / (_h * _area)
} else { 300 };
_tau = _tau max 30 min 3600;   // physical bounds: 30 s..1 h
private _dt = 5;                // solve cadence (s), matches the PFH tick
private _tNew = _ts - (_ts - (_tCurrent + 273.15)) * exp (-_dt / _tau);

(_tNew - 273.15)
