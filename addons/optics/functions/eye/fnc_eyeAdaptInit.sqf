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

// Guards around the physiological range, not sources: the dark floor is the
// starlight luminance (10^-3 cd/m2 class) and the ceiling is a bright
// daylight surface.  UNSOURCED clamps.
private _x = (_sceneLog max -6) min 8;
[_x, _x]
