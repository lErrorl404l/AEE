#include "..\..\script_component.hpp"

/*
Human-vision limits: acuity, colour, quantum noise and disability glare.

  - Acuity.  The highest resolvable grating frequency against the adapting
    luminance, Ward Larson, Rushmeier & Piatko 1997 (IEEE TVCG 3(4):291),
    fitted to Shlaer 1937 (J Gen Physiol 21:165):
      R(L) = 17.25 atan(1.4 log10 L + 0.35) + 25.72   cycles/deg
    The acuity returned is R over its photopic asymptote, 52.82 c/deg.
  - Colour.  Rods carry one photopigment (rhodopsin), so the rod share of
    vision, 1 - m (CIE 191:2010 adaptation coefficient), carries no colour.
  - Quantum noise.  In the dark the eye is photon-limited: the threshold
    contrast follows the de Vries-Rose law, C ~ L^-1/2 (de Vries 1943; Rose
    1948), reaching 1 at the absolute threshold of the dark-adapted eye,
    about 1e-6 cd/m2 (Hood & Finkelstein 1986, Handbook of Perception and
    Human Performance, ch. 5).  The noise returned is that threshold contrast,
    sqrt(1e-6 / L), on the rod share.
  - Disability glare.  The CIE Age-adjusted Stiles-Holladay disability
    glare equation (CIE 146:2002; Vos 2003, Clin Exp Optom 86:363), valid
    for glare angles of 1 to 30 deg:
      L_veil / E = 10 (1 + (A/70)^4) / theta^2    (cd/m2 per lux)
    A the observer's age.  Angles below 1 deg are held at 1 deg and above
    30 deg the equation is extrapolated (the CIE general equation covers
    0.1 to 100 deg).  The veil lowers every retinal contrast by
    L / (L + L_veil); the glare returned is L_veil / (L + L_veil).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - adapting luminance, cd/m2
  1: Number - mesopic coefficient m, 0 scotopic to 1 photopic
  2: Number - illuminance at the eye from the glare source, lx
  3: Number - angle from the line of sight to the glare source, degrees
  4: Number - observer age, years

Returns:
  Array - [acuity, colourLoss, darkNoise, glare, acuityCpd, veilLuminance]:
  the first four 0 to 1, acuity in cycles/deg, veil in cd/m2.
*/

params [
    ["_lum", 1, [0]],
    ["_mesopic", 1, [0]],
    ["_glareLux", 0, [0]],
    ["_angleDeg", 90, [0]],
    ["_age", 25, [0]]
];

private _l = _lum max 1e-9;
private _rods = ((1 - _mesopic) max 0) min 1;

private _cpd = (17.25 * (atan ((1.4 * (log _l)) + 0.35)) * (pi / 180)) + 25.72;
_cpd = _cpd max 0;
private _acuity = (_cpd / 52.82) min 1;

private _colourLoss = _rods;

private _darkNoise = (_rods * (sqrt (1e-6 / _l))) min 1;

private _theta = ((abs _angleDeg) max 1) min 180;
private _k = 10 * (1 + (((_age max 0) / 70) ^ 4)) / (_theta * _theta);
private _veil = (_glareLux max 0) * _k;
private _glare = _veil / ((_l + _veil) max 1e-12);

[_acuity, _colourLoss, _darkNoise, _glare, _cpd, _veil]
