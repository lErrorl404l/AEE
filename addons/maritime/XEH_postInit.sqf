#include "script_component.hpp"

AEE_MODULE_POST_INIT

// Emit the module state line once at INFO, then per second at DEBUG (see
// fnc_dumpState).  A new registration keeps the dump out of every other
// module's tick.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

// Internal waves and thermocline (issue #17).  One update per second; it
// self-gates on the setting.  The model is a deterministic function of the
// mission time, the map latitude and the sea-surface temperature, so a
// dedicated server computes the same state as a client.
[{
    if !(missionNamespace getVariable [QGVAR(internalWaveEnabled), true]) exitWith {};
    [] call FUNC(updateInternalWaves);
}, 1] call CBA_fnc_addPerFrameHandler;
