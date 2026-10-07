#include "..\script_component.hpp"

/*
material state line.

One grep of "material state" answers the module's state.  Read only: the only
write is the stateLogStarted flag.  AEE_LOG_INFO on the first call, then
AEE_LOG_DEBUG each tick, so it is readable without the trace switch and cheap
with it off.

The line carries the surface-hook publication, the preloaded bisurf cache
size, the count of object classes learned on impact, and the local unit's
hook identifier.  Every value carries a safe default so the first line is
valid before the cache is built or a unit has fired.

Nothing here changes state and nothing broadcasts.
*/

if (!(AEE_TRACE_ON) && {missionNamespace getVariable [QGVAR(stateLogStarted), false]}) exitWith {};

// The published player-attach hook (a code value, set in XEH_preInit).
private _hook = missionNamespace getVariable [QGVAR(attachSurfaceHook), {}];
private _hookPresent = _hook isNotEqualTo {};

// The preloaded vanilla bisurf cache and the per-class learned cache.
private _materialCache = missionNamespace getVariable [QGVAR(materialCache), createHashMap];
if !(_materialCache isEqualType createHashMap) then { _materialCache = createHashMap; };
private _classCache = missionNamespace getVariable [QGVAR(classCache), createHashMap];
if !(_classCache isEqualType createHashMap) then { _classCache = createHashMap; };

// The local unit's Fired-handler id, or -1 when the hook is not attached.
private _playerHook = -1;
private _unit = call CBA_fnc_currentUnit;
if (!isNull _unit) then {
    _playerHook = _unit getVariable [QGVAR(surfaceHook), -1];
    if !(_playerHook isEqualType 0) then { _playerHook = -1; };
};

private _logMsg = format [
    "material state | hook=%1 | cache=%2 learned=%3 | playerHook=%4",
    _hookPresent, count _materialCache, count _classCache, _playerHook
];

if (missionNamespace getVariable [QGVAR(stateLogStarted), false]) then {
    AEE_LOG_DEBUG(_logMsg);
} else {
    missionNamespace setVariable [QGVAR(stateLogStarted), true];
    AEE_LOG_INFO(_logMsg);
};
