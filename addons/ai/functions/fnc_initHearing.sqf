#include "..\script_component.hpp"

/*
Install the native engine-AI hearing handler.

Server-side: the engine simulates AI on the server and the reveal command only
updates knowledge on the machine it runs on.  The handler attaches to every man
through the shared lib class installer, so it covers the units present at load
and the ones created later.

A Fired event is raised on the machine that owns the firing unit, so the class
handler never sees a client-owned player's shot and a dedicated server hears
only its own AI fire.  A client therefore installs the same handler on its own
player and sends the reveal to the server, where the AI is simulated.  On the
host the class handler already covers the local player, so the player path is
client-only and one shot is still revealed once.

Both handlers are installed unconditionally and the setting is read per shot, so
toggling aee_ai_nativeHearing takes effect without a mission restart.  With the
setting off the feature is inert.

Arguments: none.

Returns:
  Nothing.
*/

private _onFired = {
    params ["_unit"];
    if (isNull _unit) exitWith {};
    if !(missionNamespace getVariable [QGVAR(nativeHearing), false]) exitWith {};
    if (isServer) then {
        [_unit] call FUNC(revealSound);
    } else {
        // The machine that simulates the AI owns the knowledge.
        [_unit] remoteExecCall [QFUNC(revealSound), 2];
    };
};

if (isServer) then {
    ["CAManBase", "Fired", _onFired, QGVAR(nativeHearingFired)] call EFUNC(lib,installObjectEngineHandler);
};

if (hasInterface && {!isServer}) then {
    ["Fired", _onFired, QGVAR(nativeHearingFired)] call EFUNC(lib,installPlayerEngineHandler);
};

AEE_LOG_INFO("native AI hearing handler installed")
