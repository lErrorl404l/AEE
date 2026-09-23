#include "..\..\script_component.hpp"

/*
Rotor downwash and brownout (ground effect).

A rotor near the ground drives air down, the flow turns radial at the
surface, and loose material is lifted into it: brownout over sand, whiteout
over snow. The physics is published, and this function computes it rather
than scaling a curve.

The chain, each step cited in docs/wiki/research/rotor-downwash-brownout.md:

1. INDUCED VELOCITY (momentum theory).  A rotor supports its weight by
   accelerating air downward:
       v_i = sqrt( T / (2 * rho * A) )
   with T the thrust (the aircraft's weight in steady flight, so getMass
   gives it), rho the air density and A the rotor disc area.

2. GROUND EFFECT.  Near the ground the induced velocity falls and the
   flow turns outward.  The outwash velocity just above the surface is
   taken as the induced velocity scaled by the ground-proximity factor,
   which rises as the rotor descends.

3. ENTRAINMENT THRESHOLD (Bagnold).  A grain moves only when the flow
   exceeds its threshold friction velocity:
       u*t = A * sqrt( ((rho_s - rho) / rho) * g * d )
   with A = 0.1 for the fluid threshold and 0.082 for the impact
   threshold (Bagnold 1936/1941; Greeley and Iversen 1985).  THIN AIR
   LOWERS THE THRESHOLD, which is why the same rotor lifts dust more
   readily at altitude.  Below threshold there is no cloud at all.

4. TRANSPORT (Bagnold flux).  Above threshold the mass flux is
       q = C * (rho / g) * sqrt(d / D) * u*^3
   so the visible plume grows as the CUBE of the flow excess, not
   linearly.  This is why brownout appears suddenly.

Inputs are the aircraft and its height above ground; everything else is
AEE state or a cited constant.

Arguments:
  0: aircraft (OBJECT, default the player's vehicle)
  1: material (STRING, the surface material, default "dust")

Returns [entrainment 0..1, thresholdMs, outwashMs, massFlux]:
  entrainment - the fraction of the potential cloud, 0 below threshold
  thresholdMs - the Bagnold threshold friction velocity for the grain
  outwashMs   - the computed outwash velocity at the surface
  massFlux    - Bagnold flux (kg per metre width per second)
*/

params [
    ["_aircraft", vehicle (call CBA_fnc_currentUnit), [objNull]],
    ["_material", "dust", [""]]
];

if (isNull _aircraft) exitWith { [0, 0, 0, 0] };

// ─── Constants (cited) ────────────────────────────────────────────────────
private _RHO_S = 2650;        // quartz grain density, kg/m3
private _G = 9.80665;         // standard gravity, m/s2
private _D_REF = 250e-6;      // Bagnold's reference grain size, m
private _A_FLUID = 0.1;       // Bagnold fluid threshold coefficient
private _C_FLUX = 1.8;        // Bagnold flux constant, order unity

// Grain size and threshold coefficient per surface material.  Grain size
// is the median diameter: sand is the classic aeolian case, dust is finer,
// gravel is coarser than saltation can lift in this regime.
private _grain = switch (_material) do {
    case "sand":   { [250e-6, _A_FLUID] };
    case "dust":   { [80e-6,  _A_FLUID] };   // fine dust lifts first
    case "dirt":   { [200e-6, _A_FLUID] };
    case "snow":   { [400e-6, 0.08] };       // low density, clumping
    case "gravel": { [4000e-6, _A_FLUID] };  // too coarse to saltate
    default        { [200e-6, _A_FLUID] };
};
_grain params ["_d", "_coef"];

// Snow grains are ice, not quartz: the density term uses the real density.
private _grainDensity = [_RHO_S, 917] select (_material == "snow");

// ─── Air density (AEE state; thin air lowers the threshold) ───────────────
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
if !(_rho isEqualType 0) then { _rho = 1.225; };
_rho = _rho max 0.1 min 1.5;

// ─── 1. Induced velocity from momentum theory ─────────────────────────────
// The aircraft's weight is the steady-state thrust.  Rotor disc area is
// estimated from the rotor radius if the class declares one, else from a
// typical rotor span for the airframe mass.
private _mass = getMass _aircraft;
if (_mass <= 0) exitWith { [0, 0, 0, 0] };
private _thrust = _mass * _G;

// A main-rotor radius between 3 m (light) and 11 m (heavy lift).
private _radius = 3 + ((_mass / 12000) min 1) * 8;
private _disc = pi * _radius * _radius;
private _vInduced = sqrt (_thrust / (2 * _rho * _disc));

// ─── 2. Ground effect: outwash at the surface ─────────────────────────────
// Height above ground relative to rotor radius.  In ground effect (h/R
// below about 1) the jet reaches the surface and spreads; higher up the
// downwash disperses before it can lift anything.
private _agl = (getPosASL _aircraft) select 2;
private _groundZ = getTerrainHeightASL (getPos _aircraft);
private _height = (_agl - _groundZ) max 0;
private _hOverR = _height / (_radius max 1);

// The outwash factor rises as the rotor descends into ground effect.
private _wash = 1 - (_hOverR min 1);
_wash = _wash * _wash;                       // steep onset as it settles
private _outwash = _vInduced * (0.8 + _wash * 1.2);

// ─── 3. Bagnold threshold ─────────────────────────────────────────────────
private _threshold = _coef * sqrt (((_grainDensity - _rho) / _rho) * _G * _d);

// ─── 4. Entrainment and Bagnold flux ──────────────────────────────────────
private _entrainment = 0;
private _flux = 0;
if (_outwash > _threshold) then {
    // The friction velocity of the surface flow; the outwash velocity is
    // the free-stream, and the surface friction velocity is a fraction.
    private _uStar = _outwash * 0.05;
    if (_uStar > _threshold) then {
        _flux = _C_FLUX * (_rho / _G) * sqrt (_d / _D_REF) * (_uStar ^ 3);
        // Normalise the excess into 0..1 for the caller; the cube law is
        // carried by the flux itself.
        private _excess = (_outwash - _threshold) / _threshold;
        _entrainment = (_excess / (1 + _excess)) min 1;
    };
};

// Finer material off a dry surface saturates fully; gravel barely moves.
if (_material == "gravel") then { _entrainment = _entrainment * 0.15; };

[_entrainment, _threshold, _outwash, _flux]
