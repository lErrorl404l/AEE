#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

// Preload the vanilla bisurf cache (layer 2/3).
call FUNC(initMaterialCache);

// Register HitPart learning on every projectile as it is fired (the
// ACE3 frag pattern).  Each fired round gets a HitPart handler that
// classifies the surface it hits and caches the result per object
// class (layer 3).  Any object from any mod is covered on FIRST
// impact - no per-mod config, no pre-ship knowledge.
["CBA_fired", {
    params ["_unit", "_weapon", "_muzzle", "_mode", "_ammo", "_magazine", "_projectile", "_vehicle"];
    if (isNull _projectile) exitWith {};
    _projectile addEventHandler ["HitPart", {
        _this call FUNC(handleHitPart);
    }];
}] call CBA_fnc_addEventHandler;
