#include "script_component.hpp"

AEE_MODULE_POST_INIT

// The client tick and the stimulus broadcast start here.  The whole layer is
// client-local cosmetic ecology, so a machine with no player runs nothing.
if (hasInterface) then {
    [] call FUNC(initAI);
};

// Native engine-AI hearing (issue #74).  Server-side and inert until
// aee_ai_nativeHearing is enabled; the function guards isServer.
[] call FUNC(initHearing);

// Uniform per-module state dump (plan T3): one state line per second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;
