#include "..\script_component.hpp"

/*
Wildlife ambient response to scent (predator / unknown presence).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, no random.

It maps the scent dispersion intensity to an ambient-sound multiplier.  A
predator or an unknown presence leaves scent; wildlife detect it by scent above
an odour detection threshold and reduce activity, so a high scent intensity
quietens the ambient bed.  The direction is Amo et al (2008), "Predator odour
recognition and avoidance in a songbird", Functional Ecology 22(2):289-293,
DOI 10.1111/j.1365-2435.2007.01361.x.  The intensity is the repo's own scent
model output (fnc_calculateScentDispersion).

The detection threshold and the floor are UNSOURCED modelling choices: the
study reports the avoidance direction, not a magnitude, and the scent intensity
is dimensionless (a detectability proxy), so the odour detection threshold
cannot be transferred from a concentration unit (van Gemert 2003, "Odour
Thresholds", ISBN 90-810295-1-X).

Arguments:
  0: Number - the scent dispersion intensity, 0 to 1

Returns:
  Number - the ambient multiplier, 0 to 1
*/

params [
    ["_intensity", 0, [0]]
];

private _i = (_intensity max 0) min 1;

// Below the detection threshold the scent is not noticed: no effect.  Above it
// the ambient falls linearly to the floor at full intensity.
private _threshold = 0.15;
private _floor = 0.4;

linearConversion [_threshold, 1, _i, 1, _floor, true]
