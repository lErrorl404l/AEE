#include "..\..\script_component.hpp"

/*
Star brightness coefficient (aee-workshop-copy item 3, part 1).

The coefficient form is re-derived from fn_starNightTweaks.sqf in the Workshop
mod Star Light (Workshop 3749362906).  The mod ships no licence, so this is a
re-derived numeric form, not copied code.  The constants are UNSOURCED
aesthetic proxies: the mod publishes no physical curve.

Model:
  coef2 = (1.5 - moonPhase)^2 * min(ambientBrightness, 1000)^4
  coef  = max( (10 / coef2) / max(houseCount, 1), 0.1 )^0.8 / 2

A darker sky (low ambientBrightness) and few nearby houses raise the
coefficient.  A fuller moon (moonPhase to 1) and more houses lower it.  The
result is a dimensionless render-scale multiplier in (0, 100].  The cap 100
returns when the denominator is zero (a black sky).

Arguments:
  0: Number - moon phase, 0 new to 1 full (moonPhase date)
  1: Number - ambient brightness (getLighting element 1)
  2: Number - nearby house count

Returns:
  Number - coefficient in (0, 100]
*/

params [
    ["_moonPhase", 0.5, [0]],
    ["_ambientBrightness", 0, [0]],
    ["_houseCount", 0, [0]]
];

// UNVERIFIED RANGE.  getLighting element 1 (ambientLightBrightness) has no
// documented range: BIKI lists it as "Number" with no bounds, and its own
// example reads 28526.2 in daylight, so the value is not a 0..1 fraction and
// the old 1000 ceiling was not the engine's scale.  The bounds below are a
// defensive saturation of the fourth power, NOT a range claim: the floor is 0
// because a negative brightness would otherwise read as a lit sky.  Settle
// the real range with an in-engine getLighting read before changing either
// bound.
private _coef2 = ((1.5 - _moonPhase) ^ 2) * (((_ambientBrightness max 0) min 1000) ^ 4);
if (_coef2 <= 0) exitWith { 100 };

// Parenthesise the final min: some SQF precedence readings bind min tighter
// than the divide, which would drop the cap.  The plan's intent is the cap.
(((((10 / _coef2) / (_houseCount max 1)) max 0.1) ^ 0.8) / 2) min 100
