#include "..\script_component.hpp"

/*
Exhaust plume gas temperature and depth from engine power.

This kernel is the sibling of fnc_calculateThermalRefraction.  The two
functions answer different questions.  The refraction kernel returns the
optical contrast of a gas at a given temperature.  This kernel returns the
gas temperature and the plume depth for an engine power fraction.

WHY POWER DRIVES THE PLUME SIZE AND NOT THE CONTRAST.  The refractive
contrast is a weak function of gas temperature.  At an ambient of 15 C a
400 C gas gives a contrast magnitude of 1.58, a 600 C gas gives 1.85, a
900 C gas gives 2.09, and a 1200 C gas gives 2.23.  The whole range spans a
factor of 1.4.  The plume depth spans 0.35 m to 2.5 m, a factor of 7.  So a
renderer that ramps alpha or contrast with power would move the image by
40 percent at most.  The power ramp drives the plume DEPTH, and the
contrast stays on the real gas-temperature curve.  The four contrast
figures above come from fnc_calculateThermalRefraction with its K, the
Gladstone-Dale coefficient of 2.26e-4 m^3/kg from Stone and Zimmerman,
"Index of Refraction of Air", NIST Engineering Metrology Toolbox.

THE INTERPOLATION IS LINEAR AND IT IS A DECLARED APPROXIMATION.  No
published exhaust-temperature-versus-power curve was found for these
engine classes.  The idle and full endpoints are declared defaults and not
measurements.  A linear ramp between two declared endpoints is the
simplest curve consistent with the endpoints.  This header states that the
curve is an approximation rather than a measurement.

THE RESULT IS A BULK PROPERTY, NOT A NOZZLE MEASUREMENT.  The gas
temperature is the plume bulk temperature at the nozzle exit.  A real
plume cools from the nozzle to the free stream, so its local contrast is
at most the value computed here.  The depth is the declared plume size,
not a measured jet diameter.

THE READER IS REAL, AND IT IS GATED ON THE FLIGHT MODEL.  The RotorLib
real-time data interface publishes a numeric collective and throttle:
collectiveRTD for a helicopter and throttleRTD for fixed wing, both unary
with a scalar return.  The group reports meaningful values only when the
advanced helicopter flight model is on, which the renderer checks with
difficultyEnabledRTD.  When the model is off the RTD numbers are not
evidence of engine power, so the renderer falls through to the next source
rather than draw a plume from a meaningless zero.  A land vehicle has no
RTD throttle and never reads.  The reader lives in the renderer, not in
this kernel, because this kernel takes a power fraction as an argument and
returns a pair.

Guards, each explicit:
  - The power fraction is clamped to 0..1, because a caller may pass a
    value outside it and the two declared endpoints define the curve.
  - The gas temperatures must each be positive.  A Celsius value at or
    below zero is near or below absolute zero and is unphysical, and the
    interpolation would read nonsense.
  - The plume depths must each be positive.  A zero or negative depth is
    not a plume.
  - The full-power value must not be below the idle value, for the gas
    temperature and for the depth.  An inverted pair interpolates
    backwards.  The plume would then shrink as the engine works harder,
    which is the exact defect this function exists to remove.

Arguments:
  0: power (NUMBER, engine power fraction 0 idle to 1 full, default 0)
  1: idleTempC (NUMBER, declared idle gas temperature, default 300)
  2: fullTempC (NUMBER, declared full-power gas temperature, default 480)
  3: idleDepthM (NUMBER, declared idle plume depth in metres, default 0.35)
  4: fullDepthM (NUMBER, declared full-power plume depth, default 0.60)

Returns [gasTempC, depthM], both linearly interpolated on the power
fraction.  Returns [0, 0] when a declaration is unusable.
*/

params [
    ["_power", 0, [0]],
    ["_idleTempC", 300, [0]],
    ["_fullTempC", 480, [0]],
    ["_idleDepthM", 0.35, [0]],
    ["_fullDepthM", 0.60, [0]]
];

// A caller may pass a value outside the two declared endpoints.
private _fraction = _power max 0 min 1;

if (_idleTempC <= 0 || _fullTempC <= 0) exitWith { [0, 0] };
if (_idleDepthM <= 0 || _fullDepthM <= 0) exitWith { [0, 0] };
if (_fullTempC < _idleTempC) exitWith { [0, 0] };
if (_fullDepthM < _idleDepthM) exitWith { [0, 0] };

private _gasTempC = _idleTempC + ((_fullTempC - _idleTempC) * _fraction);
private _depthM = _idleDepthM + ((_fullDepthM - _idleDepthM) * _fraction);

[_gasTempC, _depthM]
