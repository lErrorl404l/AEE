#include "..\..\script_component.hpp"

/*
Thermal sensor session ENTER.

Runs the one-time setup for a thermal session, on whichever host channel
starts it: the engine thermal channel (visionMode 2) or the DTV day channel.
Called by the visionMode player event and by the DTV host manager
(fnc_updateThermalHost), so the two hosts cannot drift.
*/

// Rain droplets on the objective: particle source, engine assets.
// Mode-independent: rain lands on the lens whether NVG or thermal.
["ENTER"] call EFUNC(thermal,applyRainDroplets);
// Second sun: physics-driven fake sun for the engine's thermal sun term
// (buildings/terrain can only be sun-heated, not driven per-object).
["ENTER"] call EFUNC(thermal,applySecondSun);
// Clothing thermal: per-item TI overrides on nearby units.
["ENTER"] call EFUNC(thermal,applyClothingThermal);
// Building thermal: swap building materials to a cold TI rvmat so buildings
// read cold at night.
["ENTER"] call EFUNC(thermal,applyBuildingThermal);
