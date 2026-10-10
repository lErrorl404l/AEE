#include "script_component.hpp"

AEE_MODULE_POST_INIT

// Emit the module state line once at INFO, then per second at DEBUG (see
// fnc_dumpState).  A new registration keeps the dump out of every other
// module's tick.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

// Underwater light model (issue #14).  One update per second; it self-gates
// on the setting and on a live local unit, so a dedicated server publishes
// nothing.  The explicit argument keeps the CBA handler array out of the
// typed params.
[{
    if !(missionNamespace getVariable [QGVAR(underwaterLightEnabled), true]) exitWith {};
    [objNull] call FUNC(updateUnderwaterLight);
}, 1] call CBA_fnc_addPerFrameHandler;
