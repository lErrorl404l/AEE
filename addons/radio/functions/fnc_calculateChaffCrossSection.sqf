#include "..\script_component.hpp"

/*
Chaff cloud radar cross section (pure).

    sigma_cloud = N * 0.17 * lambda^2

    N      number of resonant dipoles
    lambda radar wavelength, m

A half-wave dipole presents a peak broadside RCS of about 0.86 lambda^2;
averaged over random orientation it is about 0.15 to 0.17 lambda^2.  The
value 0.17 lambda^2 is the figure used throughout the electronic-warfare
literature, and the issue #131 uses it.  The exact decimal is taken as 0.17;
a primary re-derivation was not obtainable this session, so the coefficient
is recorded as the common EW figure rather than a freshly verified constant.

The dipoles are cut to resonate at the threat wavelength.  The ideal length
is lambda/2; a real foil is cut shorter (about 0.47 lambda) to allow for the
finite conductor diameter.  The cut length is a construction detail and does
not enter this RCS formula, which depends only on the count and the
wavelength.

SOURCE.  Van Vleck, Bloch and Hamermesh, "Theory of Radar Reflection from
Wires or Thin Metallic Strips", J. Appl. Phys. 18(3):274-294, 1947, DOI
10.1063/1.1697649 (the dipole backscatter theory); Tavis, "Van Vleck
Revisited: The RCS of Thin Wires", 1973, DTIC AD0768336 (the standard
follow-up).  Worked values at X-band (10 GHz, lambda = 0.03 m, lambda^2 =
9e-4 m2): one dipole 1.53e-4 m2; a 6 m2 fighter return needs about 39,000
dipoles.  The 6 m2 fighter RCS is Skolnik, "Introduction to Radar Systems",
Table 2.2 (large fighter).  The issue #131 figures RR-188 = 835 m2 and
Chemring CCM216 > 10,000 m2 are not published figures, so they are UNSOURCED
and are not used by this kernel.

Arguments:
  0: _dipoleCount (NUMBER) N, >= 0
  1: _wavelengthM (NUMBER) lambda, m, > 0

Return Value: NUMBER - cloud radar cross section in m2.  Returns 0 when the
count is zero or the wavelength is not positive.
Public: No
*/

params [
    ["_dipoleCount", 0, [0]],
    ["_wavelengthM", 0, [0]]
];

private _count = _dipoleCount max 0;
if (_count <= 0) exitWith { 0 };
if (_wavelengthM <= 0) exitWith { 0 };

private _dipoleCoefficient = 0.17;

_count * _dipoleCoefficient * _wavelengthM * _wavelengthM
