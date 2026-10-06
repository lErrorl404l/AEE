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

// The runtime module-health report reads every module's init flags once the
// mission has had 10 s to bring the modules up.  It runs once, never per tick.
[{
    [] call FUNC(reportModuleHealth);
}, [], 10] call CBA_fnc_waitAndExecute;

// The throttled cross-module consistency monitor.  A separate per-frame
// handler, independent of the environment tick and of the module-health
// report.  It gates on the setting and on the interval, so the check itself
// runs at the configured cadence, never per frame.
[{
    if !(missionNamespace getVariable [QGVAR(consistencyCheck), true]) exitWith {};
    private _interval = missionNamespace getVariable [QGVAR(consistencyInterval), 10];
    if !(_interval isEqualType 0) then { _interval = 10; };
    private _last = missionNamespace getVariable [QGVAR(consistencyLast), -1];
    if !(_last isEqualType 0) then { _last = -1; };
    if ((_last < 0) || {CBA_missionTime - _last >= _interval}) then {
        missionNamespace setVariable [QGVAR(consistencyLast), CBA_missionTime];
        [] call FUNC(runConsistencyCheck);
    };
}, 1] call CBA_fnc_addPerFrameHandler;

// ─── Positional consistency monitor (task 14) ─────────────────────────────
// Throttled to the environment tick.  Read-only: it reads the published
// anchor and world location, never the player or another module.  The
// monitor is geometry-only, so it runs on every machine.  Placed last so
// the vehicle-class token above keeps its line number and the derived
// vehicle inventory does not churn.
GVAR(consistencyPFH) = [{
    // CBA calls a per-frame handler as [_args, _handle] call {code}.  A bare
    // `call FUNC(runGeoConsistency)` inherits that array as _this, so the
    // typed params would read an array for _force and error every tick.  Pass
    // the argument explicitly (the P82 lesson: a registered entry must accept
    // the handler array).
    [false] call FUNC(runGeoConsistency);
}, GVAR(updateInterval)] call CBA_fnc_addPerFrameHandler;
