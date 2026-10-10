#include "script_component.hpp"

AEE_MODULE_POST_INIT

// ─── Blast injury channel (issue #132) ────────────────────────────────────
// Hooks the engine "Explosion" event, computes the Kingery-Bulmash
// incident overpressure at the victim's position from the explosion
// origin and charge mass estimate, then applies Bowen (1968) pressure-
// impulse injury probabilities and the tertiary blast-wind throw.
//
// The event arguments are [_vehicle, _damage, _source] (Arma 3 wiki):
// _vehicle is the damaged object, _source is the exploding object (may be
// objNull).  The handler is installed on CAManBase, so it fires on the
// machine that owns the damaged unit, and it records the blast origin for
// the corpse throw (issue #160).
//
// Charge mass: the engine exposes no TNT mass on the event.  We estimate
// it from the projectile's damage value: the explosive warhead of an
// 155 mm shell is ~6.8 kg TNT and Arma's default HE projectile damage
// is ~4.7-10 depending on class.  The estimate is scaled so a default
// shell lands near 6.8 kg, and is clamped to a plausible 0.1-250 kg band.
// This is a documented estimate - the engine gives us the source object
// and damage, not ordnance mass.

["CAManBase", "Explosion", {
    params ["_vehicle", "_damage", "_source"];
    if (isNil "_vehicle" || {isNull _vehicle}) exitWith {};

    // The explosion origin.  The engine gives the exploding object, not a
    // position; a null source falls back to the damaged object.
    private _origin = if (isNull _source) then { getPosATL _vehicle } else { getPosATL _source };

    // Charge mass estimate from the projectile's damage value.
    private _dmg = if (isNull _source) then { 0 } else { getNumber (configOf _source >> "hit") };
    private _massKg = ((_dmg max 0.1) / 5.0) * 6.8;   // ~6.8 kg at hit=5
    _massKg = _massKg max 0.1 min 250;

    // The blast record for the corpse throw (issue #160).  Machine-local:
    // the Killed handler on the same machine reads it.
    missionNamespace setVariable [QGVAR(lastBlast), [_origin, _massKg, CBA_missionTime]];

    // The injury channel is player-scoped: felt where it can be felt.
    if !(missionNamespace getVariable [QGVAR(blastInjuryEnabled), true]) exitWith {};
    if (_vehicle isNotEqualTo (call CBA_fnc_currentUnit)) exitWith {};

    private _dist = _vehicle distance _origin;
    if (_dist < 0.5) then { _dist = 0.5; };

    private _result = [_massKg, _dist] call FUNC(calculateBlastOverpressure);
    _result params ["_pSoKpa", "_tdMs"];
    if (_pSoKpa <= 0) exitWith {};

    private _inj = [_pSoKpa, _tdMs] call FUNC(calculateBlastInjury);
    _inj params ["_eardrum", "_lungThresh", "_lung1", "_lung50", "_lung99", "_throw"];

    // Diagnosable state for the docker/headless test and external consumers.
    missionNamespace setVariable [QGVAR(blastOverpressureKpa), _pSoKpa];
    missionNamespace setVariable [QGVAR(blastInjury), _inj];

    // ACE3 medical is optional for this addon.  The medical-log function
    // lives in ace_medical_treatment (not ace_medical), so the guard tests
    // the function itself: absent ACE leaves it nil and the call would
    // throw.
    if (_eardrum > 0.5 && {!isNil "ace_medical_treatment_fnc_addToLog"}) then {
        [_vehicle, "AEE_blastEardrum", 60] call ace_medical_treatment_fnc_addToLog;
    };
}, QGVAR(blast)] call EFUNC(lib,installObjectEngineHandler);

// ─── Corpse physics (issue #160) ─────────────────────────────────────────
// On the Killed event, for a locally owned body: the corpse mass
// (calculateCorpseMass), the blast throw and tumble (calculateBlastThrow
// via applyDeathMomentum).  One-shot, no per-frame cost.
["CAManBase", "Killed", {
    params ["_unit", "_killer", "_instigator", "_useEffects"];
    if (isNil "_unit" || {isNull _unit}) exitWith {};
    if !(local _unit) exitWith {};
    if !(missionNamespace getVariable [QGVAR(corpsePhysics), true]) exitWith {};
    [_unit] call FUNC(applyCorpsePhysics);
}, QGVAR(corpsePhysics)] call EFUNC(lib,installObjectEngineHandler);
