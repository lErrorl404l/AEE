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

private _registry = missionNamespace getVariable [QEGVAR(core,ppRegistry), createHashMap];
private _id = format ["%1|%2", _scope, _key];
private _entry = _registry getOrDefault [_id, [-1, ""]];
_entry params ["_existing", "_legacy"];
if (_existing >= 0) exitWith {
    private _logMsg = format ["ppEffect %1/%2 already owned, handle=%3", _scope, _key, _existing];
    AEE_LOG_DEBUG(_logMsg);
    _existing
};

private _handle = ppEffectCreate [_effect, _priority];
private _guard = 0;
while {_handle < 0 && _guard < _maxBump} do {
    _priority = _priority + 1;
    _handle = ppEffectCreate [_effect, _priority];
    _guard = _guard + 1;
};
if (_handle < 0) exitWith {
    private _logMsg = format ["ppEffect %1/%2 (%3) failed to create after %4 priority bumps", _scope, _key, _effect, _guard];
    AEE_LOG_ERROR(_logMsg);
    -1
};

_registry set [_id, [_handle, _legacy]];
missionNamespace setVariable [QEGVAR(core,ppRegistry), _registry];
missionNamespace setVariable [format [QEGVAR(core,ppHandle_%1_%2), _scope, _key], _handle];
if (_legacy != "") then { missionNamespace setVariable [_legacy, _handle] };
private _logMsg = format ["ppEffect created %1/%2 %3 handle=%4 priority=%5", _scope, _key, _effect, _handle, _priority];
AEE_LOG_INFO(_logMsg);

_handle
