#include "script_component.hpp"

AEE_MODULE_POST_INIT

// Emit the module state line once at INFO, then per second at DEBUG (see
// fnc_dumpState).  A new registration keeps the dump out of every other
// module's tick.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

// Underwater acoustics driver (issue #113).  One update per second.  It
// self-gates on the setting and reads the local unit's depth, so a dedicated
// server publishes the surface state and a client publishes the depth of the
// local diver.  The explicit empty argument keeps the CBA handler array out
// of the typed params.
[{
    if !(missionNamespace getVariable [QGVAR(underwaterAcousticsEnabled), true]) exitWith {};
    [] call FUNC(updateUnderwaterAcoustics);
}, 1] call CBA_fnc_addPerFrameHandler;
