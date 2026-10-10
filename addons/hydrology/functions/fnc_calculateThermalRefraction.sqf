#include "..\script_component.hpp"

/*
Refractive contrast of hot exhaust gas against ambient air.

A hot gas plume is less dense than the air around it, and the refractive
index of a gas tracks its density (Gladstone-Dale, n - 1 = K * rho).  The
density step at the plume boundary therefore bends light, and that bend is
the shimmer seen over an exhaust.  This function computes the refractive
contrast of the plume against the air it sits in.

  density ratio   rho_hot / rho_ambient = T_ambient_K / T_hot_K
  index contrast  d(n - 1)              = K * rho_ambient * (ratio - 1)

THE SIGN IS NEGATIVE AND IT MUST STAY NEGATIVE.  Hot gas is LESS dense than
the ambient air, so its index is LOWER and the contrast d(n - 1) is below
zero.  A caller that takes a magnitude uses abs, and a caller that renders
reads the magnitude as strength.  The sign is the physical direction of the
step and the function never drops it.

THE RETURNED VALUE IS A CEILING OVER THE REAL PLUME, NOT A POINT
MEASUREMENT.  The result is a function of the gas temperature alone.  A real
plume has a temperature field that falls from the nozzle to the free stream,
so its local contrast is at most the value computed at the hottest point,
which is the nozzle exit.  The value here is that maximum.  It is the
physical maximum for the stated gas temperature and it cannot be raised.

  K is the Gladstone-Dale coefficient for air, 2.26e-4 m^3/kg at sea level,
  from Stone and Zimmerman, "Index of Refraction of Air", in the NIST
  Engineering Metrology Toolbox, which publishes the Edlen and Ciddor
  equations.  It is the same constant as fnc_calculateSupersonicTrace, which
  cites the same source.  The repository holds a second refractive constant,
  in fnc_calculateRefraction, but that is the ITU-R P.453 RADIO
  refractivity.  Its wavelength is not the visible one, so its constant must
  not be read as K.

THIS FUNCTION MODELS THE REFRACTIVE COMPONENT ONLY.  It does not model the
condensation of water vapour into droplets, and it does not model soot,
which scatters light by absorption rather than by refraction.  A real
exhaust may show both.  This function neither models them nor excludes them.

Guards, each explicit:
  - The gas must be HOTTER than the ambient air.  A gas at or below ambient
    carries no density step, so no gradient stands and no refraction occurs.
    The equality case returns exactly 0.  A colder gas returns exactly 0 as
    a boundary guard, because a caller may pass the temperature of a cold
    object by mistake.
  - The gas Kelvin temperature and the ambient Kelvin temperature must each
    be positive.  A non-positive absolute temperature is unphysical, and the
    ratio would divide by zero or invert a sign.
  - rhoRel must be positive.  It scales the ambient density, so a
    non-positive value would invert or remove the contrast.

Arguments:
  0: gasTempC (NUMBER, exhaust gas temperature in Celsius, default 0)
  1: ambientTempC (NUMBER, ambient air temperature in Celsius, default 15)
  2: rhoRel (NUMBER, air density relative to ISA sea level, default 1.0)

Returns the refractive index contrast d(n - 1) in units of 1e-4, as a
NEGATIVE number for hot gas.  Returns exactly 0 when no gradient stands.
*/
params [
    ["_gasTempC", 0, [0]],
    ["_ambientTempC", 15, [0]],
    ["_rhoRel", 1.0, [0]]
];

if (_rhoRel <= 0) exitWith { 0 };

// Hot gas must exceed the ambient air, or no density step stands.
if (_gasTempC <= _ambientTempC) exitWith { 0 };

private _gasK = _gasTempC + KELVIN_OFFSET;
private _ambientK = _ambientTempC + KELVIN_OFFSET;
if (_gasK <= 0) exitWith { 0 };
if (_ambientK <= 0) exitWith { 0 };

// Density is inversely proportional to absolute temperature at uniform
// pressure, so rho_hot / rho_ambient = T_ambientK / T_gasK.
private _ratio = _ambientK / _gasK;
private _rhoAmbient = AERO_ISA_SEA_LEVEL_DENSITY * _rhoRel;
private _k = 0.000226;
private _contrast = _k * _rhoAmbient * (_ratio - 1);

// Report in 1e-4 units so the caller reads a small number, not 1e-4.
_contrast / EPSILON
