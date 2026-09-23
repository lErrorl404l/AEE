#include "..\..\script_component.hpp"

/*
Kickup parameters for the ground a unit is standing on.

Builds the engine particle parameters from two real inputs: the SURFACE
material (fnc_surfaceMaterial) and the environmental state (air density,
wind, moisture). The engine IS the solver (gravity from weight, drag from
volume, wind coupling from rubbing, ground collision from bounce), so the
job here is to give it the right numbers for the material.

Physical basis per material:
  weight  kg   - the particle's gravity response.  A dense mineral grain
                 settles fast, dry organic fluff drifts.  The engine
                 treats weight as an acceleration scalar, so the numbers
                 are relative between materials, anchored on the vanilla
                 dust particle (1.0) and the observed settling of sand
                 versus snow.
  volume  m3   - drag cross-section.  Drag force is 0.5*rho*v^2*Cd*A, so
                 the aerodynamic cross-section decides how far a grain of
                 a given mass travels.  A fine dust grain has a large
                 area per unit mass (high volume), a wet clod has little.
  rubbing 0..1 - how completely the wind advects the particle.  A fine
                 dry particle follows the wind; a wet clod does not.
  bounce 0..1  - restitution against the ground.  Dry sand hardly bounces
                 (it is inelastic at these speeds), a frozen surface
                 throws grains back.

Air density then scales drag, exactly as a real particle in thinner air
travels farther: at half density the deceleration halves.

Arguments:
  0: material (STRING, default "dust")
  1: density (NUMBER 0..1, the surface lift coefficient, default 0.6)
  2: colour (ARRAY RGBA, optional) - the surface colour when the caller
     holds it.  When empty, the position is sampled so the colour comes
     from the ground the emitter is actually on.
  3: position (ARRAY, PositionASL or PositionWorld, optional)

Returns [weight, volume, rubbing, bounce, colour].
*/

params [
    ["_material", "dust", [""]],
    ["_density", 0.6, [0]],
    ["_colour", [], [[]]],
    ["_pos", [], [[]]]
];

// Base behaviour per material.  Values are relative to the engine's own
// dust particle (weight 1.0, volume 0.6, rubbing 0.5) and ordered by the
// real settling and transport of each material.
private _base = switch (_material) do {
    // Fine mineral dust: slow settling, high drag, wind-following.
    case "dust":   { [1.00, 0.60, 0.50, 0.25] };
    // Sand grains: heavier, settle quickly, still wind-driven.
    case "sand":   { [1.45, 0.45, 0.42, 0.20] };
    // Dry organic soil: light and fluttery, travels far.
    case "dirt":   { [1.10, 0.70, 0.55, 0.15] };
    // Snow crystals: very light, large area per mass, long drift.
    case "snow":   { [0.55, 1.10, 0.75, 0.05] };
    // Wet clods: heavy, low drag, little transport, no bounce.
    case "mud":    { [1.60, 0.30, 0.20, 0.05] };
    // Gravel and scree: dense, settles at once.
    case "gravel": { [1.80, 0.25, 0.15, 0.35] };
    // Water spray: atomised, high drag.
    case "spray":  { [0.80, 1.40, 0.35, 0.60] };
    default        { [1.00, 0.60, 0.50, 0.25] };
};
_base params ["_weight", "_volume", "_rubbing", "_bounce"];

// ─── Air density -> drag ──────────────────────────────────────────────────
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
if !(_rho isEqualType 0) then { _rho = 1.225; };
_rho = _rho max 0.1 min 1.5;
_volume = _volume * (1.225 / _rho);

// ─── Wind -> advection ────────────────────────────────────────────────────
// A fine dry particle follows the wind more closely than a wet one.  The
// rub coefficient already encodes that; the wind strength scales it.
private _wind = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
if !(_wind isEqualType 0) then { _wind = 0; };
_rubbing = (_rubbing * (1 + ((_wind min 15) / 15) * 0.6)) min 0.9;

// ─── Moisture -> cohesion ─────────────────────────────────────────────────
// Wet ground holds its particles: the visible plume is smaller and the
// grains clump.  The dust-suppression state is the moisture proxy.
private _suppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0.6];
if !(_suppression isEqualType 0) then { _suppression = 0.6; };

// ─── Lift coefficient -> the weight/drag balance ──────────────────────────
// A surface that lifts readily throws more, lighter particles into the
// air; a hard-packing surface throws few, heavy ones.
_weight = _weight * (1.15 - (_density * 0.35));
_volume = _volume * (0.80 + (_density * 0.45));

// Colour: the ground the emitter is on decides it.  The surface sample is
// the authoritative source (a map with unusual soil gets its own hue); a
// per-material table is the last resort for a caller with no position.
if (_colour isEqualTo []) then {
    if (count _pos >= 2) then {
        private _sampled = [_pos] call FUNC(surfaceSample);
        _colour = _sampled select 1;
    };
};
if (_colour isEqualTo []) then {
    _colour = switch (_material) do {
        case "sand":   { [0.85, 0.76, 0.55] };
        case "snow":   { [1.00, 1.00, 1.00] };
        case "dirt":   { [0.44, 0.34, 0.23] };
        case "mud":    { [0.30, 0.24, 0.17] };
        case "gravel": { [0.54, 0.52, 0.49] };
        case "spray":  { [0.72, 0.78, 0.82] };
        default        { [0.62, 0.58, 0.48] };
    };
};
if ((count _colour) == 3) then { _colour pushBack 1; };

[_weight, _volume, _rubbing, _bounce, _colour]
