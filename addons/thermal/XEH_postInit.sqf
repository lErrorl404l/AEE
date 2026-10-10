#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

// The view side of the thermal pipeline (the post-process effects, the fusion
// overlay, the outline worker and the active-IR illuminator) lives in
// aee_thermal_display.  This addon keeps the physics and the object-thermal
// painting.

// Uniform per-module state dump, one line a second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;
