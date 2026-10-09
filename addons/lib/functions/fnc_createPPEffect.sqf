#include "..\script_component.hpp"

/*
 * Create a post-process effect and take ownership of it.
 *
 * CBA 3.19.0 has no resource registry, no RAII and no teardown manager.
 * CBA_fnc_createPerFrameHandlerObject is the only start/end lifecycle object
 * in the framework and it does not cover engine handles.  AEE keeps its own,
 * because an effect created outside it cannot be found in order to be
 * destroyed.  The four optics base effects were exactly that: created once,
 * read by four files, destroyable by nothing.
 *
 * OWNERSHIP IS IDEMPOTENT.  A second call for the same scope and key returns
 * the live handle instead of creating another effect.  This is the fix for the
 * triple-init stacking: ppEffectCreate at an occupied priority bumps and
 * returns a NEW handle, orphaning the old one, so a repeat init used to log
 * "created" on every pass.
 *
 * A HANDLE IS NEVER SHARED ACROSS SCOPES.  Idempotence is keyed on scope and
 * key, so two different keys pass the check above even when they ask for the
 * SAME effect at the SAME priority.  Measured in game: the night grain fix
 * created a FilmGrain at priority 2000 while the optics base set already held
 * FilmGrain at 2000, and the log shows both scopes handed handle 32:
 *
 *   ppEffect created optics/FilmGrain      handle=32 priority=2000
 *   ppEffect created nightvision/FilmGrain handle=32 priority=2000
 *
 * Two owners of one engine effect means the first teardown destroys the second
 * one's effect, which is the cross-module damage this registry exists to stop.
 * ppEffectCreate returned a POSITIVE handle for the occupied priority, so the
 * failure check below only ever sees a negative, and the bump loop below was
 * dead code for this case.  So the registry compares every candidate handle
 * against every handle it already owns and bumps the priority until it gets
 * one of its own.  That closes the class, not the instance: any two keys
 * anywhere in the mod are now safe.
 *
 * The handle is written to three places so existing readers keep working:
 *   - the registry entry, which is what makes teardown possible
 *   - aee_core_ppHandle_<scope>_<key>, the owner record
 *   - _legacyVar, the addon's own historic name, so no reader has to change
 *
 * Params:
 *   0: _scope     <STRING> owning addon, e.g. "optics"
 *   1: _key       <STRING> unique within the scope, e.g. "ChromAberration"
 *   2: _effect    <STRING> engine effect name
 *   3: _priority  <NUMBER> base priority, bumped until creation succeeds
 *   4: _legacyVar <STRING> historic variable name to mirror, "" for none
 *   5: _maxBump   <NUMBER> priority bumps before giving up (default 100)
 *
 * Returns: <NUMBER> the handle, or -1.
 */
params [
    ["_scope", "", [""]],
    ["_key", "", [""]],
    ["_effect", "", [""]],
    ["_priority", 0, [0]],
    ["_legacyVar", "", [""]],
    ["_maxBump", 100, [0]]
];

if (_scope == "" || _key == "" || _effect == "") exitWith {
    AEE_LOG_ERROR("createPPEffect called without a scope, key or effect name");
    -1
};

// Eager-default allocation removed; the registry is written back below, so a
// locally-created map still persists.
private _registry = missionNamespace getVariable [QEGVAR(lib,ppRegistry), -1];
if (_registry isEqualType 0) then { _registry = createHashMap; };
private _id = format ["%1|%2", _scope, _key];
private _entry = _registry getOrDefault [_id, [-1, ""]];
_entry params ["_existing", "_legacy"];
if (_existing >= 0) exitWith {
    private _logMsg = format ["ppEffect %1/%2 already owned, handle=%3", _scope, _key, _existing];
    AEE_LOG_DEBUG(_logMsg);
    _existing
};

// The engine returns a POSITIVE handle for an occupied priority, so the return
// value cannot detect a shared handle and a negative-only check is dead code for
// that case.  Compare every candidate against every handle the registry already
// owns, and bump the priority until the engine hands back one of our own.
private _ownedIds = keys _registry;
private _handle = -1;
private _guard = 0;
private _collidedWith = "";
private _usedPriority = _priority;
while {_handle < 0 && _guard <= _maxBump} do {
    private _candidate = ppEffectCreate [_effect, _usedPriority];
    _collidedWith = "";
    if (_candidate >= 0) then {
        {
            private _otherEntry = _registry getOrDefault [_x, [-1, ""]];
            private _heldHandle = _otherEntry select 0;
            if (_heldHandle == _candidate) then { _collidedWith = _x; };
        } forEach _ownedIds;
        if (_collidedWith == "") then { _handle = _candidate; };
    };
    if (_handle < 0) then {
        if (_collidedWith != "") then {
            private _logMsg = format ["ppEffect %1/%2 asked for handle=%3, already owned by %4, so the priority is bumped", _scope, _key, _candidate, _collidedWith];
            AEE_LOG_WARN(_logMsg);
        };
        _usedPriority = _usedPriority + 1;
        _guard = _guard + 1;
    };
};
if (_handle < 0) exitWith {
    private _logMsg = format ["ppEffect %1/%2 (%3) failed to create after %4 priority bumps, last shared with %5", _scope, _key, _effect, _guard, _collidedWith];
    AEE_LOG_ERROR(_logMsg);
    -1
};

_registry set [_id, [_handle, _legacy]];
missionNamespace setVariable [QEGVAR(lib,ppRegistry), _registry];
missionNamespace setVariable [format [QEGVAR(core,ppHandle_%1_%2), _scope, _key], _handle];
if (_legacy != "") then { missionNamespace setVariable [_legacy, _handle] };
private _logMsg = format ["ppEffect created %1/%2 %3 handle=%4 priority=%5", _scope, _key, _effect, _handle, _usedPriority];
AEE_LOG_INFO(_logMsg);

_handle
