#include "..\script_component.hpp"

/*
Install the native engine-AI hearing handler.

Server-side only: the engine simulates AI on the server and the reveal command
only updates knowledge on the machine it runs on.  The handler attaches to
every man through the shared lib class installer, so it covers the units
present at load and the ones created later.

The handler is installed unconditionally and the setting is read per shot, so
toggling aee_ai_nativeHearing takes effect without a mission restart.  With the
setting off the feature is inert.

Arguments: none.

Returns:
  Nothing.
*/

if (!isServer) exitWith {};

["CAManBase", "Fired", {
    params ["_unit"];
    if (isNull _unit) exitWith {};
    if !(missionNamespace getVariable [QGVAR(nativeHearing), false]) exitWith {};
    [_unit] call FUNC(revealSound);
}, QGVAR(nativeHearingFired)] call EFUNC(lib,installObjectEngineHandler);

AEE_LOG_INFO("native AI hearing handler installed")
