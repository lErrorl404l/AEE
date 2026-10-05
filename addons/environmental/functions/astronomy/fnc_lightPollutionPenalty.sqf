#include "..\..\script_component.hpp"

/*
Light-pollution magnitude penalty (aee-workshop-copy item 3, part 1).

Part of the Star Light brightness model.  The coefficient family is re-derived
from fn_starNightTweaks.sqf in the Workshop mod Star Light (Workshop
3749362906); the mod ships no licence, so no code is copied.

Skyglow from nearby settlement raises the sky background and hides faint
stars, so it subtracts magnitudes from the naked-eye limiting magnitude.  The
bounded log form is an UNSOURCED aesthetic proxy.  The concept is SOURCED to
Garstang (2000) and the Bortle scale; the exact curve is UNSOURCED.

  penalty = 2.0 * log10(1 + houses) / log10(1 + 1000)

The constants beside the values below are the reference house count (1000,
where the penalty reaches its 2.0 cap) and the cap itself.  The result is
clamped to 0..2.0.

Arguments:
  0: Number - nearby house count

Returns:
  Number - magnitude penalty in 0..2.0
*/

params [["_houseCount", 0, [0]]];

private _houseReference = 1000; // houses at which the penalty caps
private _penaltyMax = 2.0;      // magnitude cap
private _houses = _houseCount max 0;

private _penalty = _penaltyMax * (log (1 + _houses) / log (1 + _houseReference));
(_penalty max 0) min _penaltyMax
