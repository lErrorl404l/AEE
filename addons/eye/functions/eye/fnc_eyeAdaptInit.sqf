#include "..\..\script_component.hpp"

/*
Adaptation state at mission start.

The eye arrives ADAPTED, not neutral.  A mission that starts at night is
already dark-adapted and a mission that starts in daylight is light-adapted,
so the initial state is the scene's own log-luminance.  There is no warm-up
from a fixed default (the operator requirement: "If a mission starts at night,
safe to say eyes are already adjusted").

The state is a two-pool vector [coneLog, rodLog].  Setting both pools to the
scene log means the mesopic combine also starts at the scene, so the aperture
is correct on the first frame the model runs.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: Number - scene log10 luminance, cd/m2

Returns:
  Array - the initial [coneLog, rodLog].
*/

params [["_sceneLog", -3, [0]]];

// The operating range of human vision, 10^-6 cd/m2 (the absolute scotopic
// threshold) to 10^8 cd/m2 (the onset of retinal damage); Hood and
// Finkelstein 1986, Handbook of Perception and Human Performance, ch. 5.
private _x = (_sceneLog max -6) min 8;
[_x, _x]
