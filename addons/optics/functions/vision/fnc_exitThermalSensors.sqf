#include "..\..\script_component.hpp"

/*
Thermal sensor session EXIT.

The mirror of fnc_enterThermalSensors, shared by the engine thermal channel
and the DTV day channel.  fnc_applyThermalVision owns the ppEffect teardown;
it destroys the handles because isThermalHostActive now reports false.  The
per-module EXIT calls then restore every swapped material.
*/
[] call EFUNC(thermal,applyThermalVision);
["EXIT"] call EFUNC(thermal,applySecondSun);
["EXIT"] call EFUNC(thermal,applyClothingThermal);
["EXIT"] call EFUNC(thermal,applyBuildingThermal);
["EXIT"] call EFUNC(thermal,applyRainDroplets);
setAperture -1;
