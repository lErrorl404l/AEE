#include "..\..\script_component.hpp"

/*
Environmental coupling for particle parameters (issue #150).

Takes the material's base parameters (fnc_particleMaterial) and overrides
them from AEE state — the engine solver then behaves like the real
physics:

  volume (drag)      <- air density: thin air drags less, particles
                        travel farther (test: rho 0.6 -> ~1.7x farther)
  bounceOnSurface    <- ground state: hardpack bounces, mud absorbs,
                        snow fluffs
  rubbing (wind)     <- wind strength (local-wind field is #136; the
                        global scalar is the current state available)
  weight (mass)      <- gas vs dust vs debris: plume is buoyant

Input:  [_material, [_posASL]]
Output: [weight, volume, rubbing, bounceOnSurface, colour]
*/

params [["_material", "smoke", [""]], ["_posASL", [], [[]]]];

private _base = [_material] call FUNC(particleMaterial);
_base params ["_weight", "_volume", "_rubbing", "_bounce", "_colour"];

// ─── Air density -> drag (volume) ────────────────────────────────────────
// Drag force ~ rho * v^2 * Cd * A.  At half density the same particle
// decelerates half as fast, so it travels ~1.7x farther (sqrt(2)) in the
// same time.  Scale volume inversely with the density ratio.
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
if !(_rho isEqualType 0) then { _rho = 1.225; };
_rho = _rho max 0.1 min 1.5;
private _dragScale = 1.225 / _rho;
_volume = _volume * _dragScale;

// ─── Ground state -> restitution ─────────────────────────────────────────
// Dust on hardpack bounces (0.4), on mud absorbs (0.1), on snow fluffs
// (0.05).  Only the dust material couples (smoke/spray have no bounce).
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
if (_material == "dust") then {
    _bounce = switch (_groundState) do {
        case "Frozen":     { 0.45 };
        case "Hardpack":   { 0.4 };
        case "Normal":     { 0.25 };
        case "Mud":        { 0.1 };
        case "Snow":       { 0.05 };
        default            { 0.25 };
    };
};

// ─── Wind -> advection (rubbing) ─────────────────────────────────────────
// Stronger wind couples the particle more (scalar proxy until the local
// wind field #136 lands).  Smoke is already fully advected; dust picks
// up with wind.
if (_material == "dust") then {
    private _wind = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
    if !(_wind isEqualType 0) then { _wind = 0; };
    _rubbing = (0.3 + (_wind min 15) / 15 * 0.4) min 0.7;
};

[_weight, _volume, _rubbing, _bounce, _colour]
