#include "..\..\script_component.hpp"

/*
Colour-temperature kernel (human-vision model, colour slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The base-grade
driver calls this; the kernel maps the atmospheric state to the correlated
colour temperature (CCT) of the scene illuminant, in kelvin.  The result is the
SOURCE for the existing white-balance stage, not a second colour stage: the
driver feeds it to fnc_perceptionIlluminantFromCct and then the existing
fnc_perceptionIlluminant and fnc_perceptionChromaticAdaptation run unchanged.

Model.  The colour of daylight is set by two physical paths: the DIRECT solar
beam, reddened by the air mass it crosses (Rayleigh scattering removes blue as
the path lengthens), and the SKY, whose blue is the scattered light of the
whole dome.  The kernel computes both and blends them by the cloud cover, which
is what removes the direct beam.

  Direct term - air mass (SOURCED).  Kasten and Young 1989, Applied Optics
  28(22):4735-4738:
    m = 1 / (sin(theta) + 0.50572 * (theta + 6.07995)^-1.6364)
  theta is the apparent solar elevation in degrees.  At the zenith m is 1, at
  the horizon m is about 38.  The CCT anchors on the air mass are SOURCED
  (CIE 15:2004): D55 at the zenith, 5503 K, and a blackbody near 2000 K at the
  horizon.  The interpolation between them is UNSOURCED (the exact spectral
  integration is not available to the engine).

  Sky term - overcast (SOURCED anchors).  A clear blue sky is a high-CCT
  daylight (about 10000 K, the upper CIE daylight locus); full overcast is the
  CIE standard overcast daylight D65, 6504 K (CIE 15:2004).  The interpolation
  is UNSOURCED.

  Blend.  Cloud cover removes the direct beam, so the blend weight is the
  overcast fraction.  Below the horizon the direct beam is gone, so the sky
  term takes the whole weight across the first 6 degrees of civil twilight.

Per-constant source register (UNSOURCED values are marked beside the clamp):
  Kasten and Young air mass  SOURCED: Kasten and Young 1989.
  air-mass zenith anchor     5503 K, D55.  SOURCED: CIE 15:2004.
  air-mass horizon anchor    2000 K.  SOURCED: the blackbody regime (CIE
                             15:2004); the exact 2000 K value is UNSOURCED.
  sky clear anchor           10000 K.  SOURCED: the CIE daylight locus upper
                             band (CIE 15:2004, valid 4000 to 25000 K).
  sky overcast anchor        6504 K, D65.  SOURCED: CIE 15:2004.
  air-mass range 1 to 38     SOURCED: Kasten and Young 1989 (zenith to
                             horizon).
  twilight blend band 0 to -6 deg  UNSOURCED: the civil-twilight convention.
  CCT band 2000 to 25000 K   SOURCED: CIE 15:2004 (daylight locus band).

Arguments:
  0: Number - apparent solar elevation, degrees (negative below the horizon)
  1: Number - overcast fraction, 0 to 1

Returns:
  Number - correlated colour temperature of the scene illuminant, kelvin, in
           2000 to 25000.
*/

params [
    ["_sunElevation", 0, [0]],
    ["_overcast", 0, [0]]
];

if !(_sunElevation isEqualType 0) then { _sunElevation = 0; };
if !(_overcast isEqualType 0) then { _overcast = 0; };
_overcast = (_overcast max 0) min 1;

// The air-mass formula needs theta + 6.07995 > 0, so clamp the elevation to
// the formula floor.  Deep below the horizon the direct term is irrelevant
// anyway (the twilight blend below gives the sky term the whole weight).
private _theta = _sunElevation max -6;

// Kasten and Young 1989 air mass.
private _airMass = 1 / ((sin _theta) + (0.50572 * ((_theta + 6.07995) ^ -1.6364)));

// Direct solar CCT: D55 at the zenith (m 1), a blackbody near 2000 K at the
// horizon (m 38).
private _sunCct = linearConversion [1, 38, _airMass, 5503, 2000, true];

// Sky CCT: clear blue sky 10000 K to the CIE overcast daylight D65 6504 K.
private _skyCct = linearConversion [0, 1, _overcast, 10000, 6504, true];

// Cloud cover removes the direct beam; below the horizon the sky term takes
// the whole weight across the first 6 degrees of civil twilight.
private _twilight = linearConversion [0, -6, _sunElevation, 0, 1, true];
private _weight = _overcast max _twilight;

private _cct = linearConversion [0, 1, _weight, _sunCct, _skyCct, true];

(_cct max 2000) min 25000
