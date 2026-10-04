#include "..\..\script_component.hpp"

/*
Start the eye adaptation PFH (issue #141).

Client-only. Idempotent: a second call does nothing while the PFH is live.
The 0.1 s tick matches the sensor PFH, so the fast pupil branch has the
sub-second resolution it needs.

Arguments: none.

Returns:
  Nothing.
*/

if (!hasInterface) exitWith {};
if (!isNil QGVAR(eyePFH)) exitWith {};

GVAR(eyePFH) = [FUNC(updateEyeAdaptation), 0.1] call CBA_fnc_addPerFrameHandler;

AEE_LOG_INFO("eye adaptation PFH started")
