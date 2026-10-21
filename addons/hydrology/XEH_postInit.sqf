#include "script_component.hpp"

AEE_MODULE_POST_INIT

// hydrology has no postInit work of its own: it is a pure kernel set driven by
// the core environment tick.  The module still runs postInit so its
// aee_hydrology_postInit health flag is set, which the module-health contract
// requires of every non-compat module.
//
// THE ONE EXCEPTION: the D8 runoff grid (issue #284).  The first river tick
// built the whole ceil(worldSize/100)^2 grid synchronously - 308 squared,
// or 94,864 getTerrainHeightASL calls, on Altis - which stalled the frame in
// which the environment tick reached the river chain.  The grid is cached by
// its key, so the pre-warm below moves that cost into postInit, off the
// playable timeline, and the first tick finds a cache hit.
if (missionNamespace getVariable [QEGVAR(core,enabled), true]) then {
    private _d8Step = 100;   // metres; must match fnc_calculateRiverWaterLevel
    private _d8Side = (ceil (worldSize / _d8Step)) max 1;
    [[0, 0], _d8Side, _d8Side, _d8Step] call FUNC(routeRunoffD8);
};
