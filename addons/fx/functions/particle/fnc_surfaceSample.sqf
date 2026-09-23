#include "..\..\script_component.hpp"

/*
Surface sample at a position.

Reads the engine surface under a world position and returns the kickup
material for it.  Thin wrapper over fnc_surfaceMaterial: the engine does
not expose a surface type for an arbitrary ASL position directly, so the
sample is taken at the ground below it.

Argument:
  0: position (ARRAY, PositionASL or PositionWorld, default [])

Returns [material, colourRGBA, density] - see fnc_surfaceMaterial.
*/

params [["_pos", [], [[]]]];
if (count _pos < 2) exitWith { ["dust", [0.55, 0.48, 0.38, 1], 0.6] };

[_pos] call FUNC(surfaceMaterial)
