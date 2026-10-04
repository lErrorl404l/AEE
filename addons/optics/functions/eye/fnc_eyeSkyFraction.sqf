#include "..\..\script_component.hpp"

/*
Fraction of the sampled sky directions that reach open sky.

The driver casts one ray per direction and passes an array of booleans here.
A true value means the ray reached open sky. The returned fraction scales
the ambient term: standing in a building or on the shaded side of a street
lets the eye see less sky, so the ambient light drops.

An empty sample means no information, so the function returns 1 (assume open
sky) rather than darkening the scene.

Arguments:
  0: Array - per-direction results, true when the ray reached open sky

Returns:
  Number - clear fraction in [0, 1]; 1 when the sample is empty.
*/

params [["_hits", [], [[]]]];

private _total = count _hits;
if (_total == 0) exitWith { 1 };

private _clear = 0;
for "_i" from 0 to (_total - 1) do {
    if (_hits select _i) then { _clear = _clear + 1; };
};

_clear / _total
