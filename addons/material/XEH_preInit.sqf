#include "script_component.hpp"

AEE_MODULE_PRE_INIT

ADDON = false;

#include "XEH_PREP.hpp"

// Preload the vanilla bisurf cache (layer 2/3).
call FUNC(initMaterialCache);

// Register HitPart learning on every projectile as it is fired (the
// ACE3 frag pattern).  Each fired round gets a HitPart handler that
// classifies the surface it hits and caches the result per object
// class (layer 3).  Any object from any mod is covered on FIRST
// impact - no per-mod config, no pre-ship knowledge.
// material is a LEAF addon on purpose. tools/tests/test_addon_dependencies.py
// fails the build if material gains a cross-addon edge, because a shared
// owner that also reaches into core is how a dependency cycle returns through
// the back door. So the local-unit attach is inlined here rather than calling
// the shared core installer. It is a player-scoped raw BIS handler because
// CBA's bus carries no engine events at all, measured 2026-09-29.
private _fnAttachSurface = {
    params ["_unit"];
    if (isNull _unit) exitWith {};
    if (_unit getVariable [QGVAR(surfaceHook), -1] >= 0) exitWith {};
    _unit setVariable [QGVAR(surfaceHook), _unit addEventHandler ["Fired", {
        params ["_shooter", "_weapon", "_muzzle", "_mode", "_ammo", "_magazine", "_projectile"];
        if (_shooter isNotEqualTo (call CBA_fnc_currentUnit)) exitWith {};
        if (isNull _projectile) exitWith {};
        _projectile addEventHandler ["HitPart", {
            _this call FUNC(handleHitPart);
        }];
    }]];
};
// Published rather than captured: the player event below runs later, from
// CBA's scope, where a private of this file is not visible.
missionNamespace setVariable [QGVAR(attachSurfaceHook), _fnAttachSurface];
private _localUnit = call CBA_fnc_currentUnit;
if (!isNull _localUnit) then { [_localUnit] call _fnAttachSurface };
// CBA's "unit" player event covers respawn, so a new body is covered without
// a per-frame poll.
["unit", {
    private _fn = missionNamespace getVariable [QGVAR(attachSurfaceHook), {}];
    if (_fn isEqualTo {}) exitWith {};
    [call CBA_fnc_currentUnit] call _fn;
}] call CBA_fnc_addPlayerEventHandler;
