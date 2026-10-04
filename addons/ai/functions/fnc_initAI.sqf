#include "..\script_component.hpp"

/*
Start the reusable substrate client tick.

Client-only and idempotent: a second call does nothing while the PFH is live.

Arguments: none.

Returns:
  Nothing.
*/

if (!hasInterface) exitWith {};
if (!isNil QGVAR(aiPFH)) exitWith {};

GVAR(aiPFH) = [FUNC(aiTick), AI_TICK] call CBA_fnc_addPerFrameHandler;

AEE_LOG_INFO("ai substrate PFH started")
