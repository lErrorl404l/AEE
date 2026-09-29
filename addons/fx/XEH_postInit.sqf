#include "script_component.hpp"

AEE_MODULE_POST_INIT

// ─── Blast injury channel (issue #132) ────────────────────────────────────
// Hooks the engine "explosion" event, computes the Kingery-Bulmash
// incident overpressure at the victim's position from the explosion
// origin and charge mass estimate, then applies Bowen (1968) pressure-
// impulse injury probabilities and the tertiary blast-wind throw.
//
// Client-side (hasInterface): the victim is the local player's unit, so
// the injury model runs where it can be felt.  The event fires on every
// machine; the guards keep the per-machine work minimal.
//
// Charge mass: the engine exposes no TNT mass on the event.  We estimate
// it from the projectile's damage value: the explosive warhead of an
// 155 mm shell is ~6.8 kg TNT and Arma's default HE projectile damage
// is ~4.7-10 depending on class.  The estimate is scaled so a default
// shell lands near 6.8 kg, and is clamped to a plausible 0.1-250 kg band.
// This is a documented estimate — the engine gives us position and
// damage, not ordnance mass.

private _fnBlastOverpressure = missionNamespace getVariable [QGVAR(fnc_calculateBlastOverpressure), nil];
private _fnBlastInjury = missionNamespace getVariable [QGVAR(fnc_calculateBlastInjury), nil];
if (isNil "_fnBlastOverpressure" || isNil "_fnBlastInjury") exitWith {};

["Explosion", {
    params ["_unit", "_explosion"];
    if (_unit isNotEqualTo (call CBA_fnc_currentUnit)) exitWith {};
    if !(missionNamespace getVariable [QGVAR(blastInjuryEnabled), true]) exitWith {};

    private _dist = _unit distance _explosion;
    if (_dist < 0.5) then { _dist = 0.5; };

    // Charge mass estimate from the projectile's damage value.
    private _dmg = getNumber (configOf _explosion >> "hit");
    private _massKg = ((_dmg max 0.1) / 5.0) * 6.8;   // ~6.8 kg at hit=5
    _massKg = _massKg max 0.1 min 250;

    // Overpressure at the victim, and the injury probabilities.
    private _result = [_massKg, _dist] call _fnBlastOverpressure;
    _result params ["_pSoKpa", "_tdMs"];
    if (_pSoKpa <= 0) exitWith {};

    private _inj = [_pSoKpa, _tdMs] call _fnBlastInjury;
    _inj params ["_eardrum", "_lungThresh", "_lung1", "_lung50", "_lung99", "_throw"];

    // Diagnosable state for the docker/headless test and external consumers.
    missionNamespace setVariable [QGVAR(blastOverpressureKpa), _pSoKpa];
    missionNamespace setVariable [QGVAR(blastInjury), _inj];

    // The engine already applies kinetic damage from the explosion itself;
    // AEE adds the pressure-channel damage (eardrum, lung) and the
    // tertiary throw.  The player's own ACE pain/hearing integration is
    // the intended consumer; without ACE the values are still published.
    if (_eardrum > 0.5) then {
        [_unit, "AEE_blastEardrum", 60] call ace_medical_fnc_addToLog;  // no-op without ACE
    };
}, QGVAR(blast)] call EFUNC(core,installPlayerEngineHandler);

// ─── Refractive shock trace renderer (issue #217 follow-on) ──────────────
// Draws the bow-shock refractive contrast on the local player's own
// round.  Local-only, so the particle source the renderer attaches is
// always local and a dedicated server creates nothing.  The renderer
// re-reads the ballistics kernel each tick with the round's CURRENT
// velocity, so the trace fades as the round slows out of the supersonic
// regime instead of holding the muzzle value.
//
// THE ROUND AND ITS AMMUNITION ARE FOUND BY SCANNING, NOT BY POSITION.
// A raw BIS "Fired" event carries the BIS order natively, but CBA's
// backwards-compatibility path swaps two of its string slots, so an
// argument index is not a contract.  The ammunition is the first STRING
// that names a CfgAmmo class.  The round is the first OBJECT that is not
// the shooter, NOT the first object, because the first object in a Fired
// event IS the shooter.  A miss leaves the class empty, and the renderer
// refuses rather than draws an invented calibre.
["Fired", {
    params ["_unit"];
    if (_unit isNotEqualTo (call CBA_fnc_currentUnit)) exitWith {};

    private _projectile = objNull;
    private _ammo = "";
    {
        if ((_ammo isEqualTo "") && (_x isEqualType "")) then {
            if (isClass (configFile >> "CfgAmmo" >> _x)) then { _ammo = _x };
        };
        if ((_projectile isEqualTo objNull) && (_x isEqualType "OBJECT") && (_x isNotEqualTo _unit)) then {
            _projectile = _x;
        };
    } forEach _this;

    if (isNull _projectile) exitWith {};
    [_projectile, _ammo] call FUNC(renderSupersonicTrace);
}, QGVAR(supersonicTrace)] call EFUNC(core,installPlayerEngineHandler);
