#include "script_component.hpp"

AEE_MODULE_POST_INIT

// Emit the module state line once at INFO, then per second at DEBUG (see
// fnc_dumpState).  A new registration keeps the dump out of every other
// module's tick.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;

// Ship motion follows the sea state (issue #33).  One tick per second; the
// driver reads the published sea state and writes the per-vessel motion.
[FUNC(calculateShipMotion), 1] call CBA_fnc_addPerFrameHandler;
