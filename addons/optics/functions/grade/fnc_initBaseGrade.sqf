#include "..\..\script_component.hpp"

/*
Start the base-grade PFH (image realism).

Client-only.  Idempotent: a second call does nothing while the PFH is live.
The 1.0 s tick refreshes the tune; the visionMode event applies the grade at
once on a mode change, so entering or leaving a sensor is not delayed.

Arguments: none.

Returns:
  Nothing.
*/

if (!hasInterface) exitWith {};
if (!isNil QGVAR(baseGradePFH)) exitWith {};

GVAR(baseGradePFH) = [FUNC(applyBaseGrade), 1.0] call CBA_fnc_addPerFrameHandler;

AEE_LOG_INFO("base grade PFH started")
