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
// Release the eye driver's pin beside every aperture restore, so the eye
// model re-claims the aperture on the next normal-vision tick.  Without it the
// 0.02 change gate suppresses the re-write and the camera stays on the sensor's
// exposure (the operator report: dark view after NVG or thermal).  This is the
// DTV host exit path; teardownSensors covers the engine thermal and NVG exits.
EGVAR(eye,eyePinned) = nil;
