#include "script_component.hpp"

AEE_MODULE_POST_INIT

// weather has no per-tick work of its own: it is a pure kernel set driven by
// the core environment tick.  The module still runs postInit so its
// aee_weather_postInit health flag is set, which the module-health contract
// requires of every non-compat module.

// ─── Smoke emitter for the scalar-field engine (issue #116) ───────────────
// A real emitter that feeds the unified transport engine: a vehicle damaged
// by an explosion is a smoke source.  The source is registered through the
// public engine API FUNC(scalarAddSource), the same call a fire, grenade or
// CBRN emitter uses, so smoke is one field on one grid rather than a model
// of its own.
//
// The engine "Explosion" event (triggered when a vehicle is damaged by a
// nearby explosion) is attached to the ground-vehicle and aircraft classes by
// EFUNC(lib,installObjectEngineHandler), which covers the objects that exist
// and the ones created later.  The class is named in the handler registration
// rather than tested with isKindOf, so the vehicle class inventory is
// unchanged.  Only a substantial hit emits smoke (damage >= 0.5): this
// threshold is a STATED modelling choice, not a measured constant
// (UNSOURCED).
private _fnAddSource = missionNamespace getVariable [QGVAR(fnc_scalarAddSource), nil];
if (!isNil "_fnAddSource") then {
    private _emitSmoke = {
        params ["_vehicle", "_damage", "_source"];
        if !(missionNamespace getVariable [QGVAR(scalarFieldsEnabled), true]) exitWith {};
        if (_damage < 0.5) exitWith {};
        // Strength scales with the inflicted damage, radius with the hit.
        ["smoke", getPosASL _vehicle, _damage min 1, 250, 6] call FUNC(scalarAddSource);
    };
    ["LandVehicle", "Explosion", _emitSmoke, QGVAR(scalarSmokeEmitterLand)]
        call EFUNC(lib,installObjectEngineHandler);
    ["Air", "Explosion", _emitSmoke, QGVAR(scalarSmokeEmitterAir)]
        call EFUNC(lib,installObjectEngineHandler);
};
