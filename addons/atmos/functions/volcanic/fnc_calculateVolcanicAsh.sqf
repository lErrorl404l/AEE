#include "..\..\script_component.hpp"

/*
Volcanic ash ground concentration, deposition and visibility (model).

The ash disperses with the Gaussian plume kernel and settles with the Stokes
kernel.  The ground-level concentration sets the dry deposition flux
(C * vs).  The visibility comes from the shared dust-visibility model
(addons/weather), because airborne ash and dust attenuate light by the same
concentration-to-visibility power law (Baddock et al. 2014); no second
extinction model is added.

Sources: Briggs (1973) dispersion; Stokes (1851) settling; Baddock, M.C.
et al. (2014) "Dust source identification..." via the weather dust model;
Casadevall, T.J. (ed.) (1994) USGS Bulletin 2047.

Arguments:
  0: Downwind distance (NUMBER, m)
  1: Crosswind distance (NUMBER, m)
  2: Ash emission rate (NUMBER, kg/s)
  3: Wind speed (NUMBER, m/s)
  4: Pasquill stability class (STRING, "A".."F")
  5: Effective plume height (NUMBER, m)
  6: Ash particle diameter (NUMBER, m, default 20 um fine ash)
  7: Air density (NUMBER, kg/m3)

Return Value: HashMap
  concentrationKgM3  ground-level concentration, kg/m3
  concentrationMgM3  ground-level concentration, mg/m3
  settlingVelocity   Stokes settling velocity, m/s
  depositionRate     dry deposition flux, kg/(m2 s)
  visibilityKm       visibility, km
  state              "none" / "moderate" / "severe" / "extreme"
  intensity          0..1 for the FX layer
Example: [3000, 0, 5e7, 10, "D", 5000, 2e-5, 1.225] call aee_atmos_fnc_calculateVolcanicAsh
Public: No
*/

params [
    ["_downwind", 0, [0]],
    ["_crosswind", 0, [0]],
    ["_emissionRate", 0, [0]],
    ["_windSpeed", 5, [0]],
    ["_stability", "D", [""]],
    ["_plumeHeight", 0, [0]],
    ["_particleDiameter", 2.0e-5, [0]],
    ["_airDensity", 1.225, [0]]
];

// ─── Settling (Stokes) ──────────────────────────────────────────────────────
private _vs = [_particleDiameter, 2500, _airDensity] call FUNC(calculateAshSettling);

// ─── Settling tilt ──────────────────────────────────────────────────────────
// The plume centreline descends by vs*x/u as the particles settle.  This is
// the mechanism by which ash reaches the ground, so the Gaussian is evaluated
// at the tilted source height, floored at ground level.
private _tilt = if (_windSpeed > 0) then { _vs * _downwind / _windSpeed } else { 0 };
private _effectiveHeight = (_plumeHeight - _tilt) max 0;

// ─── Ground-level concentration (Gaussian, z = 0) ───────────────────────────
private _cKg = [_emissionRate, _windSpeed, _stability, _effectiveHeight, _downwind, _crosswind, 0]
    call FUNC(calculateGaussianPlume);
private _cMg = _cKg * 1.0e6;

// ─── Dry deposition flux ────────────────────────────────────────────────────
private _deposition = _cKg * _vs;

// ─── Visibility (shared dust model; no second extinction model) ─────────────
private _vis = [_cMg] call EFUNC(weather,calculateDustVisibility);

createHashMapFromArray [
    ["concentrationKgM3", _cKg],
    ["concentrationMgM3", _cMg],
    ["settlingVelocity", _vs],
    ["depositionRate", _deposition],
    ["visibilityKm", _vis get "visibilityKm"],
    ["state", _vis get "state"],
    ["intensity", _vis get "intensity"]
]
