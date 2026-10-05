#include "..\script_component.hpp"

/*
Per-frame handler entry for the reusable substrate client tick.

The CBA per-frame handler calls the registered function as
`[_args, _handle] call _function` (CBA_A3 addons/common/init_perFrameHandler.sqf),
and `_args` defaults to [].  This entry therefore declares NO params and
discards the handler array, then runs the live tick.  The parameterised entry
for the tests and the on-demand monitor is fnc_aiTick.

Arguments: none.  The CBA per-frame handler passes [_args, _handle], which
this entry ignores.

Returns:
  Number - the number of agents ticked
*/

[false] call FUNC(aiTick)
