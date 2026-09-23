#include "..\..\script_component.hpp"

/*
Environmental coupling for particle parameters (issues #149, #150).

Takes a material's BASE parameters from fnc_particleMaterial (the one
source of truth) and overrides them from AEE state, so the engine solver
behaves like the real physics:

  volume (drag)      <- air density: thin air drags less, particles
                        travel farther (rho 0.6 -> ~2x the drag volume)
  bounceOnSurface    <- ground state: hardpack bounces, mud absorbs,
                        snow fluffs
  rubbing (wind)     <- wind strength
  keepOnSurface      <- water surface: spray rides the wave (issue #150)
  surfaceOffset      <- maritime wave height (aee_core_waveHeight_m), the
                        height the spray sits at above the flat sea plane

The engine exposes keepOnSurface/surfaceOffset as particle properties; the
runtime levers are onSurface (ParticleArray index 20) plus the emitter
height, which the pipeline applies from this output.

Input:  [_material, _posASL]
Output: [weight, volume, rubbing, bounceOnSurface, colour,
         keepOnSurface, surfaceOffset]
*/

params [["_material", "dust", [""]], ["_posASL", [], [[]]]];

private _base = [_material] call FUNC(particleMaterial);
_base params ["_weight", "_volume", "_rubbing", "_bounce", "_colour"];

// ─── Air density -> drag (volume) ────────────────────────────────────────
// Drag force ~ rho * v^2 * Cd * A.  At half density the same particle
// decelerates half as fast, so it travels ~1.7x farther (sqrt(2)) in the
// same time.  Scale volume inversely with the density ratio.
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
if !(_rho isEqualType 0) then { _rho = 1.225; };
_rho = _rho max 0.1 min 1.5;
_volume = _volume * (1.225 / _rho);

// ─── Ground state -> restitution ─────────────────────────────────────────
// Dust on hardpack bounces (0.4), on mud absorbs (0.1), on snow fluffs
// (0.05).  Only materials that collide with the ground are overridden:
// smoke, plume and rain carry bounce -1 and ignore the ground.  Hail is
// excluded: its restitution is the material's own 0.6 (issue #151), since
// ice elasticity dominates the surface.  The three values are the issue's;
// Frozen and Normal are the states the existing coupling already carried.
private _groundColliders = ["dust", "sand", "dirt", "snow", "mud", "gravel"];
if (_material in _groundColliders) then {
    private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
    _bounce = switch (_groundState) do {
        case "Frozen":   { 0.45 };
        case "Hardpack": { 0.4 };
        case "Normal":   { 0.25 };
        case "Mud":      { 0.1 };
        case "Snow":     { 0.05 };
        default          { 0.25 };
    };
};

// ─── Wind -> advection (rubbing) ─────────────────────────────────────────
// A fine dry particle follows the wind more closely than a wet one; the
// base rubbing encodes that, and the wind strength scales it.
private _wind = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
if !(_wind isEqualType 0) then { _wind = 0; };
_rubbing = (_rubbing * (1 + ((_wind min 15) / 15) * 0.6)) min 0.9;

// ─── Water surface -> keepOnSurface + surfaceOffset ──────────────────────
// Spray is thrown at the sea and must ride the wave, not a flat plane.
// The offset is the current significant wave height.  The variable is
// owned by core and written by the maritime sea-state model; read it with
// the core owner, as fnc_calculateWeatherReport does.
private _keepOnSurface = (_material == "spray");
private _surfaceOffset = 0;
if (_keepOnSurface) then {
    private _waveH = missionNamespace getVariable [QEGVAR(core,waveHeight_m), 0];
    if !(_waveH isEqualType 0) then { _waveH = 0; };
    _surfaceOffset = _waveH max 0;
};

[_weight, _volume, _rubbing, _bounce, _colour, _keepOnSurface, _surfaceOffset]
