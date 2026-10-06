#include "..\..\script_component.hpp"

/*
Human-vision limits and imperfections.

A clean aperture map sees perfectly at every level.  A real eye does not.
This kernel quantifies the limits the render and the perception monitor
consume, so the image degrades the way a real eye degrades.

  - Acuity falls as vision goes scotopic.  Rod acuity is far below cone
    acuity: the rod mosaic is coarser than the cone mosaic and the rod signal
    is spatially pooled (Curcio et al. 1990, J Comp Neurol 292:497, human
    photoreceptor topography).  SOURCED direction, UNSOURCED floor.
  - Colour is lost below the photopic range.  Rods carry a single photopigment
    (rhodopsin), so scotopic vision is achromatic (rod monochromacy).  SOURCED.
  - Scotopic noise (visual grain) rises as the light falls: rod vision is
    photon-limited, so the relative noise follows the Poisson shot statistics.
    The display shape is UNSOURCED.
  - Veiling glare rises when a source much brighter than the adapting level is
    in view: scattering lowers the retinal contrast (Vos 1984, CIE 146).  The
    display shape is UNSOURCED.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - adapted scene luminance, lx
  1: Number - mesopic photopic fraction, 0 scotopic to 1 photopic
  2: Number - local (point-light) illuminance at the eye, lx
  3: Number - angle from the view to the bright source, degrees
  4: Number - fog/atmosphere amount, 0 to 1

Returns:
  Array - [acuity, colourLoss, darkNoise, glare], each 0 to 1.  Acuity is 1
  in daylight and falls to a floor in the dark.  The other three rise from 0.
*/

params [
    ["_adaptedLux", 1, [0]],
    ["_mesopic", 1, [0]],
    ["_localLux", 0, [0]],
    ["_angleDeg", 0, [0]],
    ["_fog", 0, [0]]
];

private _scotopic = ((1 - _mesopic) max 0) min 1;

// Acuity: daylight 1 down to a 0.15 floor when fully scotopic.  UNSOURCED
// floor: the rod mosaic resolves about 1/5 to 1/10 of the cone acuity.
private _acuity = (1 - (0.85 * _scotopic)) max 0.15;

// Colour: rods are monochromatic, so the scotopic image has no colour.
private _colourLoss = _scotopic;

// Scotopic noise: the photon rate falls with the adapted level, and the
// relative shot noise rises as its inverse square root.  UNSOURCED display
// exponent (0.25 softens the square root for a smooth, bounded grain).
private _darkNoise = (_scotopic * (0.3 / ((_adaptedLux max 1e-4) ^ 0.25))) max 0 min 1;

// Scattered light from a bright source.  A source is NOT on-axis-or-nothing:
//   - its photometric lobe spills off-axis, decaying with the angle but never
//     reaching zero (a real lamp, headlight or the sun is not a laser);
//   - fog, dust and haze scatter the beam into the line of sight, so the beam
//     and its haze are visible from the side.
// The lobe is a Lorentzian in the angle, L = 1 / (1 + (theta/theta0)^2).  The
// 10 degree half-width and the 0.02 lobe floor are UNSOURCED display shapes
// (a bright source is still visible well off-axis).  The 0.5 in-scatter scale
// on the fog state is also UNSOURCED.
private _theta0 = 10;
private _lobe = (1 / (1 + ((_angleDeg / _theta0) ^ 2))) max 0.02;
private _inScatter = 0.5 * ((_fog max 0) min 1);
private _share = _localLux / ((_localLux + _adaptedLux) max 1e-6);
private _glare = (_share * (_lobe + _inScatter)) max 0 min 1;

[_acuity, _colourLoss, _darkNoise, _glare]
