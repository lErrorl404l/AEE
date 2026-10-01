#include "..\..\script_component.hpp"

/*
Tear down the vision-sensor session: one owner for the whole sequence.

The sensor pipeline is started by the "visionMode" player event and torn
down by this function.  It used to be torn down inline in that event, which
made the event the only code that could ever clean up.  A death is not a
vision-mode change, so the engine never fired the event and the per-frame
handler outlived the session: the handle, the sensor flags and every
overlay stayed live into the respawn (GAP-026).

Two callers now exist, and one of them runs without any event:

  1. the "visionMode" event, on a genuine return to normal vision, and
  2. the sensor per-frame handler itself, when the unit it belongs to
     changes or dies, which is the case the event cannot see.

Because both paths run the same sequence, the teardown cannot drift between
them.  The function is idempotent: a second call finds no handler and
returns.
*/

// Restore the engine exposure before the idempotency exit below.  The NVG
// and thermal modules set a FIXED setAperture 15, and this is the only place
// that clears it.  Gating the restore on a live sensor handler leaves the
// camera pinned to the night exposure whenever the session is already gone,
// which is exactly when it matters.  setAperture -1 is the engine default, so
// it is safe to call when no sensor ever ran.
setAperture -1;

if (isNil QGVAR(sensorPFH)) exitWith {};

[] call EFUNC(nightvision,applyNVGTubeModel);
[] call EFUNC(thermal,applyThermalVision);
["EXIT"] call EFUNC(thermal,applySecondSun);
["EXIT"] call EFUNC(thermal,applyClothingThermal);
["EXIT"] call EFUNC(thermal,applyBuildingThermal);
["EXIT"] call EFUNC(thermal,applyRainDroplets);
[GVAR(sensorPFH)] call CBA_fnc_removePerFrameHandler;
GVAR(sensorPFH) = nil;
GVAR(sensorUnit) = nil;
AEE_LOG_INFO("sensor PFH stopped")
