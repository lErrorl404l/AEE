#include "..\script_component.hpp"

/*
Stimulus decay kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The
disturbance field stores each cell's strongest recent stimulus as a
magnitude and a timestamp.  This kernel gives the magnitude that remains
after an age, using the exponential half-life form
magnitude * 0.5 ^ (age / halfLife).  A negative age is a clock error and is
clamped to the full magnitude.

The 45 s half-life is a modelling choice, UNSOURCED.  See the per-constant
register in the wildlife-ambience dossier.

Arguments:
  0: Number - initial stimulus magnitude, 0 to 1
  1: Number - age, seconds
  2: Number - half-life, seconds

Returns:
  Number - the decayed magnitude, clamped 0 to 1
*/

params [
    ["_magnitude", 0, [0]],
    ["_ageSeconds", 0, [0]],
    ["_halfLifeSeconds", 45, [0]]
];

private _halfLife = (_halfLifeSeconds max 0.000001);
private _remaining = _magnitude * (0.5 ^ (_ageSeconds / _halfLife));

((_remaining max 0) min 1)
