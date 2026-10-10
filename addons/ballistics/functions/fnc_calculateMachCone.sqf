#include "..\script_component.hpp"
/*
Mach cone geometry for a supersonic projectile (issue #217 follow-on).

A slender body in supersonic flight carries a cone-shaped bow shock that
is attached at the nose.  The cone half-angle follows from the Mach number
alone:

    mu = asin (1 / M)          M = v / a,   a = SOUND_SPEED_COEFF * sqrt (T_C + KELVIN_OFFSET)

This is exact cone geometry for a slender body, not a fit.  The cone opens
linearly behind the nose, so the radius at an axial distance x behind the
nose is x * tan(mu).  Over a body L calibres long the radius at the base
is L * calibre * tan(mu), and the full width across the base is
2 * L * calibre * tan(mu).  The constant 2 * L is named _APERTURE below,
so the width expression reads as physical.

THE CONE NARROWS AS THE ROUND ACCELERATES, AND THAT IS THE SIGN ERROR THIS
WORK CORRECTS.  mu falls from 56.44 degrees at Mach 1.2 to 14.48 degrees
at Mach 4.0, so the cone shrinks as the round speeds up.  The superseded
legibility mapping in fnc_renderSupersonicTrace did the opposite: it
widened the sprite as contrast rose, and contrast rises with speed.  The
sign of the speed dependence was wrong in the old mapping.  A renderer
that sizes a sprite from this function gets the direction right.

THE TANGENT FORM.  tan(asin(1/M)) is exactly 1 / sqrt(M^2 - 1), so this
file uses that algebraic form rather than a degree round trip.  The value
diverges as M tends to 1 from above, which is why the renderer caps the
drawn size instead of trusting this number through the transonic band.

STANDOFF, AND WHY IT IS NOT THE WIDTH.  On a SLENDER ogive nose the bow
shock stays close to the body.  The standoff length scale is the NOSE
RADIUS, not the calibre and not the body length.  A 7.62 mm round with a
rounded nose of 1 to 2 mm radius stands the shock off by about 0.2 to
0.7 mm, a small fraction of one calibre.  The visible lateral extent is
therefore dominated by the CALIBRE, and the standoff is a second-order
correction that shrinks as the body lengthens.

An earlier claim in this file family, that the standoff is about one nose
radius and so about 26 mm at every Mach number, is WRONG.  It used a
SPHERICAL nose.  The published standoff correlations, for example
Billig, F. S., "Shock-Wave Shapes around Spherical- and Cylindrical-Nosed
Bodies", Journal of Spacecraft and Rockets, 4(6), 1967, pp. 822-823,
express the standoff against the shock density ratio, the same quantity
fnc_calculateSupersonicTrace computes.  Those correlations are DEFINED FOR
A SPHERE OR A CYLINDER and are NOT applicable to a slender ogive.  They
are cited here only to be excluded, and no number is taken from them.

This function models NO standoff at all, and it returns NO contrast floor.
fnc_calculateSupersonicTrace already explains why a standoff cannot give a
contrast floor, and that reasoning stands.

GEOMETRY ONLY.  This function never scales its result for rendering and it
never reads a setting.  The renderer owns the one visibility constant, and
the kernel never sees it.

Arguments:
  0: velocity (NUMBER, current velocity, m/s)
  1: airTempC (NUMBER, air temperature in Celsius, default 15)
  2: calibreMm (NUMBER, projectile calibre in millimetres, default 7.62)

Returns [muDeg, halfWidthM, fullWidthM]:
  muDeg      the Mach cone half-angle in degrees
  halfWidthM the cone radius at the body base, L * calibre * tan(mu)
  fullWidthM the cone width across the body base, 2 * L * calibre * tan(mu)
All three are 0 when the flow is not supersonic, where no attached cone
stands off.
*/
params [
    ["_velocity", 0, [0]],
    ["_airTempC", 15, [0]],
    ["_calibreMm", 7.62, [0]]
];

if (_velocity <= 0) exitWith { [0, 0, 0] };
if (_calibreMm <= 0) exitWith { [0, 0, 0] };

// Local speed of sound, the same convention as fnc_calculateSupersonicTrace
// and fnc_calculateBallisticDrag, so the cone follows the round down through
// the transonic band instead of holding the muzzle value.
private _sound = SOUND_SPEED_COEFF * sqrt (_airTempC + KELVIN_OFFSET);
if (_sound <= 0) exitWith { [0, 0, 0] };

private _mach = _velocity / _sound;
if (_mach <= 1) exitWith { [0, 0, 0] };

private _muDeg = asin (1 / _mach);

// tan(asin(1/M)) = 1 / sqrt(M^2 - 1), exactly.
private _tanMu = 1 / sqrt ((_mach * _mach) - 1);

// The body length in calibres.  A 5.56x45 and a 7.62x51 spitzer ogive are
// about four calibres long, so the aperture across the base is eight.
private _BODY_CALIBRES = 4;
private _APERTURE = 2 * _BODY_CALIBRES;

private _calibreM = _calibreMm / 1000;
private _fullWidth = _APERTURE * _calibreM * _tanMu;

[_muDeg, 0.5 * _fullWidth, _fullWidth]
