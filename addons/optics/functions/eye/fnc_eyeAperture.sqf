#include "..\..\script_component.hpp"

/*
Camera aperture from the adapted scene luminance (issue #141).

The aperture is the eye's light intake, so it follows the PUPIL DIAMETER, and
the pupil is a physiological formula of the scene luminance.  The aperture is
therefore a CONTINUOUS DYNAMIC TRANSFER of the adapted luminance, not a
two-point anchor table.  The BI wiki setAperture calibration points (50 =
daylight outdoor, 8 = the night standard, below 20 a very bright scene, closer
to 0 lets in more light) are the two ends of the pupil range the curve runs
across.

Pupil: the Moon and Spencer (1944) tanh, quoted by de Groot and Gebhard
(1952) JOSA 42(7):492, the same formula as fnc_eyePupilSteady, inlined here
so this kernel stays pure and sqf_lite-executable:

  d = 4.9 - 3.0 * tanh(0.4 * (log10(B_mL) + 0.5)),  B_mL = (rho * E / pi) / 3.183

1 mL = 10/pi cd/m2 = 3.1831 cd/m2 (a millilambert is a thousandth of a
lambert, which is 10000/pi cd/m2).  The /3.183 and the +0.5 are coupled:
change both together or neither.

The luminance is the driver's rho * E / pi conversion (rho = the driver
eyeReflectance default, kept in step).

The aperture then runs the pupil range [1.9, 8.0] mm onto the BIKI scale
[50, 8].  The 1.9 and 8.0 mm guards are UNSOURCED (the physiological pupil
range); the fit itself is valid from about 2 mm to above 8 mm.

Two engine facts from the retired bridge carry forward. (1) setApertureNew has
effect only when HDR is enabled. (2) The engine resets the aperture at mission
start, so the driver must run after mission start.

Arguments:
  0: Number - adapted scene luminance, lx

Returns:
  Number - camera aperture; higher is narrower (less light).
*/

params [["_adaptedLux", 0, [0]]];

private _rho = 0.18;   // mirrors the driver eyeReflectance default

// de Groot pupil diameter for the adapted illuminance, mm.
private _b = ((_rho * (_adaptedLux max 1e-9)) / pi) / 3.183;
private _x = 0.4 * ((log _b) + 0.5);
private _e = exp (2 * _x);
private _d = ((4.9 - (3.0 * ((_e - 1) / (_e + 1)))) max 1.9) min 8.0;

private _nightStandard = 8;      // BI wiki setApertureNew night example, the [2, 8, 14] standard
private _dayStandard = 50;       // BI wiki setAperture Namikaze calibration: 50 = daylight outdoor

linearConversion [1.9, 8.0, _d, _dayStandard, _nightStandard, true]
