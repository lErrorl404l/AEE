#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

// ─── Fired EH: propellant-temperature MV correction per shot ──────────────
// Computes the correction for the actual ammo just fired and stores it for
// ballistics consumers.  Local to the shooter; no remote side effects.
// Skips thrown items and the ACE3-advanced-ballistics double-count guard
// inside the correction function.
["fired", {
    params ["_unit", "_weapon", "", "", "_ammo", "_magazine", "_projectile"];
    if (_unit != call CBA_fnc_currentUnit) exitWith {};
    if (_weapon == "throw" || _weapon == "put") exitWith {};
    if (_projectile isEqualTo objNull) exitWith {};

    [_ammo] call FUNC(calculateMuzzleVelocityCorrection);
}] call CBA_fnc_addEventHandler;

AEE_LOG_INFO("ballistics module post-init complete");

ADDON = true;
