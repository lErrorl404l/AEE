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

THE RETURNED VALUE IS AN UPPER BOUND, NOT A PREDICTION.  The relation above
is a normal shock.  A real bullet has a blunted nose, so its bow shock
stands off the nose and is oblique over the forward face, and an oblique
shock gives a smaller density rise than a normal shock at the same Mach.
The normal shock value is reached only on the stagnation streamline, where
the shock is locally normal.  Every other point on the body refracts less.
Treat the output as the ceiling of the effect.

The freestream Mach uses the LOCAL speed of sound, the same convention as
fnc_calculateBallisticDrag, so the trace follows the round down through the
transonic drag band instead of holding the muzzle value.

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
// At M = 1 this returns exactly 1, so the contrast vanishes there.
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
