#include "..\script_component.hpp"

/*
Stimulus decay kernel (reusable AI substrate).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The
disturbance field stores each cell's strongest recent stimulus as a
magnitude and a timestamp.  This kernel gives the magnitude that remains
after an age, using the exponential half-life form
magnitude * 0.5 ^ (age / halfLife).  A negative age is a clock error and is
clamped to the full magnitude.

The half-life is the caller's.  Wildlife passes the measured animal recovery
(WILDLIFE_ENVIRONMENT_HALF_LIFE, Griffin et al. 2020).  The engine-AI field
passes AI_STIMULUS_HALF_LIFE, 45 s, a gameplay memory: no published value
gives how long a soldier keeps a heard shot in mind.

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
