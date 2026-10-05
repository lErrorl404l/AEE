#include "..\script_component.hpp"

/*
Per-frame handler entry for the single wildlife client tick.

The CBA per-frame handler calls the registered function as
`[_args, _handle] call _function` (CBA_A3 addons/common/init_perFrameHandler.sqf),
and `_args` defaults to [].  This entry therefore declares NO params and
discards the handler array, then runs the live tick with the local unit as
the anchor.  The parameterised entry for the Docker dry-run probe and the
on-demand monitor is fnc_wildlifeTick.

Arguments: none.  The CBA per-frame handler passes [_args, _handle], which
this entry ignores.

Returns:
  Array - [bedKey, gain, disturbance, spook, spookRange]
*/

[[], false] call FUNC(wildlifeTick)
