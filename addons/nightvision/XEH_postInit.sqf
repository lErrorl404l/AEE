#include "script_component.hpp"

AEE_MODULE_POST_INIT

// Uniform per-module state dump, one line a second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;
