#include "script_component.hpp"

AEE_MODULE_POST_INIT

if (is3DEN) exitWith {};

[] call FUNC(init);

// ─── Collision-damage response (issue #172) ───────────────────────────────
// The #159 "random explosion on light tap" complaint: the engine's
// collision thresholds are a binary explosion.  Intercept vehicle-
// vehicle collision damage and scale it by the real impact energy
// (0.5*m*v^2).  The global HandleDamage listener fires for every
// damage event; fnc_handleCollisionDamage returns the ORIGINAL value
// for non-collision events (projectile impacts pass through to the
// ballistic model untouched - no double-count).
["AllVehicles", "HandleDamage", {
    params ["_unit", "_selection", "_damage", "_source", "_projectile",
            "_hitIndex", "_instigator", "_hitPoint"];
    // Only vehicles; the handler is a cheap gate for everything else.
    if (!(_unit isKindOf "LandVehicle") && {!(_unit isKindOf "Air")}) exitWith { _damage };
    [_unit, _selection, _damage, _source, _projectile, _hitIndex,
     _instigator, _hitPoint] call FUNC(handleCollisionDamage);
}, QGVAR(collisionDamage)] call EFUNC(core,installObjectEngineHandler);

// Emit the core state line once at INFO, then per second at DEBUG (see
// fnc_dumpState).  A new registration keeps the dump out of the environment
// tick.
[FUNC(dumpState), 1] call CBA_fnc_addPerFrameHandler;
