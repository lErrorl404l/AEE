#include "script_component.hpp"

AEE_MODULE_POST_INIT

// ── Laser target marker (LTM) ──────────────────────────────────────────────
// Ported from workshop 2041057379 A3TI/LTM.  Registers the Draw3D beam
// worker, the vision-mode trigger and the two keybinds.  See functions/ltm/.
[] call FUNC(ltmInit);

["AEE", "LTMToggle", [LLSTRING(ltmToggle), "Toggle the laser target marker"], {
    [call CBA_fnc_currentUnit] call FUNC(ltmToggle);
}, {}, [38, [false, false, false]]] call CBA_fnc_addKeybind;

["AEE", "LTMToggleMode", [LLSTRING(ltmToggleMode), "Cycle the laser target marker blink and steady"], {
    [call CBA_fnc_currentUnit] call FUNC(ltmToggleMode);
}, {}, [38, [false, true, false]]] call CBA_fnc_addKeybind;

// Uniform per-module state dump, one line a second.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;
