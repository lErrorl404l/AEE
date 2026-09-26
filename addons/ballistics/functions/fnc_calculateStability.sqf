#include "..\script_component.hpp"
/*
Gyroscopic stability factor from the bullet geometry (issue #167).

The Miller twist rule, computed from measured geometry rather than a
table. A bullet that no source lists still has a real stability
requirement, and the rule derives it from the bullet's own mass,
diameter, length and the barrel twist:

    s = 30 m / (T^2 L (1 + (L/d)^2)) * (v / 853)^(1/3) * exp(3.158e-5 h)

where m is the bullet mass in grains, T the twist in inches per turn, L
the bullet length in inches and d the diameter in inches. The constant
30 embeds the Army Standard Metro reference (853 m/s, 15 C, 1000 hPa),
so the velocity and altitude terms correct for the firing condition.

The rule is shape-blind: its denominator assumes a boat tail, so a flat
base bullet needs a slightly faster twist than the result states.

A stability factor of 1.5 or more is stable, 1.0 to 1.5 is marginal, and
below 1.0 the bullet does not stabilise.

Arguments:
  0: lengthM (NUMBER, bullet length, metres)
  1: massG (NUMBER, bullet mass, grams)
  2: diameterM (NUMBER, bullet diameter, metres)
  3: twistM (NUMBER, twist, metres per turn)
  4: velocity (NUMBER, muzzle velocity, m/s, default 853)
  5: altitudeFt (NUMBER, altitude, feet, default 0)

Returns the stability factor. Returns 0 when an input is missing.
Returns -1 (FIN_STABILISED) when the twist is 0, which is a fin-stabilised
projectile: the Miller rule needs a spin, so it does not apply and the
caller treats -1 as "not assessed", never as unstable.
*/
params [
    ["_lengthM", 0, [0]],
    ["_massG", 0, [0]],
    ["_diameterM", 0, [0]],
    ["_twistM", 0, [0]],
    ["_velocity", 853, [0]],
    ["_altitudeFt", 0, [0]]
];

if (_lengthM <= 0 || _massG <= 0 || _diameterM <= 0) exitWith { 0 };

// The fin-stabilised path. A smoothbore sets the twist to 0, so the
// projectile has no spin and the Miller rule cannot apply. A fin-stabilised
// round is stabilised by its tail fins. The database does not yet hold the
// fin area or the centre of pressure, so the cross-check is not computed
// here. The documented sentinel FIN_STABILISED (-1) marks the case, and the
// caller never reads it as an unstable value.
if (_twistM <= 0) exitWith { -1 };

private _massGr = _massG / 0.06479891;
private _diameterIn = _diameterM / 0.0254;
private _lengthIn = _lengthM / 0.0254;
private _twistIn = _twistM / 0.0254;
private _calibers = _lengthIn / _diameterIn;

private _stability = (30 * _massGr) /
    (_twistIn * _twistIn * _lengthIn * (1 + _calibers * _calibers));

// The velocity and altitude corrections from the same rule.
_stability = _stability * ((_velocity / 853) ^ (1 / 3));
_stability = _stability * (exp (3.158e-5 * _altitudeFt));

_stability
