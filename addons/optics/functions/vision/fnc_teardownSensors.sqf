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
// Fusion teardown: destroy the fusion PP handles so the overlay does not
// leak into normal vision.  The forced 0 is here for its
// side effect, it destroys those handles.  It must not LATCH, and the value
// restored is the READER'S OWN DEFAULT, read from the reader rather than
// restated here, so the two cannot drift apart.  The default is I2-only
// (0): the operator switches fusion on, and a teardown puts the mode back
// to the state the operator did not ask to change.  Restoring 1 here would
// fight that default and turn fusion on with no opt-in, which is the fault
// this replaces.
private _fusionModeVar = QEGVAR(thermal,fusionMode);
[0] call EFUNC(thermal,cycleFusionMode);
missionNamespace setVariable [_fusionModeVar, 0];
// Restore the fusion emissive materials.  cycleFusionMode destroys the two
// fusion post-process handles only, so without this the swapped materials
// survive into normal vision.
// The mode is the SECOND parameter. Passing only ["EXIT"] bound the string to
// _player, whose [objNull] spec rejected it, so the restore below never ran
// and the fusion emissive materials leaked. fnc_applyFusionOverlay is the
// only one of these that takes the player first.
[call CBA_fnc_currentUnit, "EXIT"] call EFUNC(thermal,applyFusionOverlay);
[GVAR(sensorPFH)] call CBA_fnc_removePerFrameHandler;
GVAR(sensorPFH) = nil;
GVAR(sensorUnit) = nil;
AEE_LOG_INFO("sensor PFH stopped")
