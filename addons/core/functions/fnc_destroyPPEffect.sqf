#include "..\script_component.hpp"

/*
 * Release post-process effects held in the shared registry.
 *
 * The counterpart to fnc_createPPEffect.  An effect is only destroyable if it
 * was registered, which is the entire point of the registry: the four optics
 * base effects were created by a function that stored one handle in
 * missionNamespace, read by four other files, and destroyable by nothing.
 *
 * _key may be "", which releases a WHOLE SCOPE.  That is the teardown case: a
 * module owning several effects releases all of them in one call instead of
 * repeating a destroy list by hand, where one name typo silently leaks the
 * rest.  The four optics base effects existed for exactly that reason.
 *
 * Mirrored historic names are reset to -1 as well, so a reader holding the old
 * variable sees an invalid handle rather than a stale positive number that
 * fails every later call with "Invalid post process handle".
 *
 * Params:
 *   0: _scope <STRING> owning addon, e.g. "optics"
 *   1: _key   <STRING> unique within the scope, or "" for the whole scope
 *
 * Returns: <NUMBER> how many handles were released.
 */
params [["_scope", "", [""]], ["_key", "", [""]]];

if (_scope == "") exitWith {
    AEE_LOG_ERROR("destroyPPEffect called without a scope");
    0
};

// Eager-default allocation removed; an absent registry yields an empty map,
// which the next line already treats as nothing to do.
private _registry = missionNamespace getVariable [QEGVAR(core,ppRegistry), -1];
if (_registry isEqualType 0) then { _registry = createHashMap; };
if (count _registry == 0) exitWith { 0 };

// Collect ids first.  Deleting while iterating a HashMap invalidates the
// iteration, so the doomed list is built before anything is destroyed.
private _wanted = [];
if (_key == "") then {
    private _prefix = format ["%1|", _scope];
    {
        private _id = _x;
        if ((_id select [0, (count _prefix)]) == _prefix) then { _wanted pushBack _id };
    } forEach (keys _registry);
} else {
    _wanted pushBack (format ["%1|%2", _scope, _key])
};

private _released = 0;
{
    private _id = _x;
    private _entry = _registry getOrDefault [_id, [-1, ""]];
    _entry params ["_handle", "_legacy"];
    if (_handle >= 0) then {
        ppEffectDestroy _handle;
        _released = _released + 1;
    };
    if (_legacy != "") then { missionNamespace setVariable [_legacy, -1] };
    private _parts = _id splitString "|";
    if ((count _parts) >= 2) then {
        missionNamespace setVariable [format [QEGVAR(core,ppHandle_%1_%2), _parts select 0, _parts select 1], -1];
    };
    _registry deleteAt _id;
} forEach _wanted;

missionNamespace setVariable [QEGVAR(core,ppRegistry), _registry];
private _logMsg = format ["ppEffect released %1 handle(s) for scope %2%3", _released, _scope, if (_key == "") then {" (all keys)"} else {format [" key=%1", _key]}];
AEE_LOG_INFO(_logMsg);

_released
