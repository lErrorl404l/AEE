#include "..\script_component.hpp"

/*
Starts the ballistics state dump tick.

fnc_dumpState reads only.  The per-frame registration lives here, not in
XEH_postInit.sqf, because test_supersonic_trace asserts that the ballistics
post-init holds no per-frame tracker: the supersonic trace kernel is called
exactly once, on the Fired path.  This handler calls only the dump.
*/

[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;
