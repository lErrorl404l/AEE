#include "..\script_component.hpp"

/*
Refractive trace of a supersonic projectile (issue #217).

A supersonic round steps the air density across its bow shock, and the
refractive index of air tracks density (Gladstone-Dale, n - 1 = K * rho).
That index step bends light, and the bend is the refractive component of
the trace.  This function computes the refractive component only.  A
condensation mist may form on a humid day.  This function neither models
that mist nor excludes it.

  shock density ratio  rho2/rho1 = ((g + 1) * M^2) / ((g - 1) * M^2 + 2)
  index contrast       d(n - 1)   = K * rho_ambient * (rho2/rho1 - 1)

g is 1.4.  K is the Gladstone-Dale coefficient for air, 2.26e-4 m^3/kg at
sea level, from Stone and Zimmerman, "Index of Refraction of Air", in the
NIST Engineering Metrology Toolbox, which publishes the Edlen and Ciddor
equations.  The repository holds a second refractive constant, in
fnc_calculateRefraction, but that is the ITU-R P.453 RADIO refractivity.  Its
wavelength is not the visible one, so its constant must not be read as K.

THE RETURNED VALUE IS A CEILING, NOT AN ESTIMATE.  The relation above is a
normal shock.  NACA Report 1135, "Equations, Tables, and Charts for
Compressible Flow", Ames Research Staff 1953, p. 621, states that an oblique
shock acts as a normal shock to the flow perpendicular to it.  That reduction
rule concerns the local jump, so it holds for a planar shock and for a
conical shock alike.  The density ratio therefore rises with the normal Mach
number M1 sin(beta) alone, and no shape term enters.  That number is largest
at beta = 90 degrees, where the stagnation streamline meets the bow shock.  So
the value here is the exact upper bound for ANY nose shape.  It is the
attained maximum for any round with a finite tip radius, and every real
bullet has one.  A hypothetical perfectly sharp body does not attain it.  The
ceiling is tight and it cannot be lowered.

NO FLOOR IS RETURNED, AND THAT IS DELIBERATE.  A lower bound would come from
the oblique shock at the nose shoulder, using the theta-beta-M relation of
NACA Report 1135 Eq (139a) p. 622.  That relation holds only for an ATTACHED
shock.  A real bullet has a meplat, a flat tip that demands a local flow turn
of about 90 degrees.  NACA Report 1135 p. 624 gives the largest turn an
attached shock accepts.  For a wedge the limit is 45.6 degrees.  For a
circular cone the limit is 57.5 degrees.  Both are limits at infinite Mach, so
a finite Mach accepts less.  The meplat exceeds both limits, and the bow
shock therefore detaches.  Theta-beta-M does not describe a detached shock.  A
floor computed that way would be false.

A STANDOFF WOULD NOT GIVE A FLOOR.  On the axis a detached shock is normal, so
the contrast there is the ceiling this function returns.  The contrast falls as
the shock turns away from the axis, because the normal Mach number falls with
the shock angle.  A floor is therefore set where the shock meets the body, and
that needs the shock shape rather than the standoff distance alone.  The
published standoff correlations are defined for a sphere or a cylinder.  None
defines an effective diameter for a meplat-tipped ogive, and the per-cartridge
meplat and ogive radius are not held.  The floor therefore stays not
computable, and this function refuses rather than returns one.

A bullet is a body of revolution, so the exact attached-shock solution is
conical Taylor-Maccoll rather than the wedge relation above.  That difference
changes the shock angle at a given surface turn, so it would change a point
value or a floor.  At a fixed shock angle, it does not change the density
ratio.  The ceiling is the value at beta = 90 degrees, where the planar and
the conical case coincide.  The difference is therefore irrelevant to the
returned value.  The wedge form is not used to produce the number.

The freestream Mach uses the LOCAL speed of sound, the same convention as
fnc_calculateBallisticDrag, so the trace follows the round down through the
transonic drag band instead of holding the muzzle value.

THE PUBLISHED VALUE IS A SINGLE MUZZLE VALUE.  The Fired handler calls this
function once, at the muzzle, and publishes the result.  Nothing in this
repository reads that variable, so the kernel does not track it at range.  A
per-frame tracker would cost every machine for a variable with no reader
here.  A caller that wants the contrast at range calls this function again.
The round's current velocity is argument 0.

NO STRENGTH OVERRIDE.  The contrast is returned as measured.  A caller may
scale it for rendering, but this function never does, because an override
would let a trace appear where the air does not support one.

Arguments:
  0: velocity (NUMBER, current velocity, m/s)
  1: rhoRel (NUMBER, air density relative to ISA sea level, default 1.0)
  2: airTempC (NUMBER, air temperature in Celsius, default 15)

Returns the refractive index contrast across the bow shock, in units of
1e-4, as an upper bound.  Returns 0 when the flow is not supersonic, where
no bow shock stands off and so no density step forms.
*/
params [
    ["_velocity", 0, [0]],
    ["_rhoRel", 1.0, [0]],
    ["_airTempC", 15, [0]]
];

if (_velocity <= 0) exitWith { 0 };
if (_rhoRel <= 0) exitWith { 0 };

// Local speed of sound, matching fnc_calculateBallisticDrag.
private _sound = 20.05 * sqrt (_airTempC + 273.15);
if (_sound <= 0) exitWith { 0 };

private _mach = _velocity / _sound;

// No shock below Mach 1, so no density step and no trace.
if (_mach <= 1) exitWith { 0 };

// Rankine-Hugoniot density ratio across a normal shock, gamma = 1.4.
// At M = 1 this returns exactly 1, so the contrast vanishes there.  The bow
// shock meets the stagnation streamline normally, so this is the ceiling over
// the whole body, and a round with a finite tip radius attains it.
private _gamma = 1.4;
private _m2 = _mach * _mach;
private _densityRatio = ((_gamma + 1) * _m2) / ((_gamma - 1) * _m2 + 2);
private _step = _densityRatio - 1;
if (_step <= 0) exitWith { 0 };

// Gladstone-Dale: d(n-1) = K * rho * (rho2/rho1 - 1), K = 2.26e-4 m^3/kg.
private _rhoAmbient = 1.225 * _rhoRel;
private _k = 0.000226;
private _contrast = _k * _rhoAmbient * _step;

// Report in 1e-4 units so the caller reads a small number, not 1e-4.
_contrast / 0.0001
