#include "..\..\script_component.hpp"

/*
Kickup parameters for the ground a unit is standing on.

The surface-lift term on top of the shared material physics.  The BASE
material numbers come from fnc_particleMaterial and the environmental
coupling from fnc_particleState, so there is ONE material table (issues
#149, #150); this function only adds what is specific to a surface being
struck:

  - a surface that lifts readily throws more, lighter particles into the
    air; a hard-packing surface throws few, heavy ones (the lift
    coefficient, _density)
  - the colour comes from the ground the emitter is actually on
    (fnc_surfaceSample), with the material table as the last resort

Arguments:
  0: material (STRING, default "dust")
  1: lift (NUMBER 0..1, the surface lift coefficient, default 0.6)
  2: colour (ARRAY RGBA, optional) - the surface colour when the caller
     holds it.  When empty, the position is sampled so the colour comes
     from the ground the emitter is actually on.
  3: position (ARRAY, PositionASL or PositionWorld, optional)

Returns [weight, volume, rubbing, bounce, colour, keepOnSurface, surfaceOffset].
*/

params [
    ["_material", "dust", [""]],
    ["_density", 0.6, [0]],
    ["_colour", [], [[]]],
    ["_pos", [], [[]]]
];

private _params = [_material, _pos] call FUNC(particleState);
_params params ["_weight", "_volume", "_rubbing", "_bounce", "_fallbackColour", "_keepOnSurface", "_surfaceOffset"];

// ─── Lift coefficient -> the weight/drag balance ──────────────────────────
// A surface that lifts readily throws more, lighter particles into the
// air; a hard-packing surface throws few, heavy ones.
_weight = _weight * (1.15 - (_density * 0.35));
_volume = _volume * (0.80 + (_density * 0.45));

// Colour: the ground the emitter is on decides it.  The surface sample is
// the authoritative source (a map with unusual soil gets its own hue); the
// material table is the last resort for a caller with no position.
if (_colour isEqualTo [] && {count _pos >= 2}) then {
    private _sampled = [_pos] call FUNC(surfaceSample);
    _colour = _sampled select 1;
};
if (_colour isEqualTo []) then {
    _colour = _fallbackColour;
};
if ((count _colour) == 3) then { _colour pushBack 1; };

[_weight, _volume, _rubbing, _bounce, _colour, _keepOnSurface, _surfaceOffset]
