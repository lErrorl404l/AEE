#include "..\script_component.hpp"

/*
Compute the propellant-temperature muzzle-velocity correction for a shot.

Physics:
  The reloading-literature coefficient is absolute: fps per degree
  Fahrenheit (e.g. 1.5 fps/degF for military ball powder).  The RELATIVE
  effect on the round depends on its own muzzle velocity, so the
  coefficient is normalised to the ammo's real initSpeed (CfgMagazines):

      mpsPerDegC   = coeff_fpsPerF * 0.3048 * 1.8        (m/s per degC)
      pctPerDegC   = mpsPerDegC / initSpeed * 100
      correction   = 1 + pctPerDegC * (T_ammo - T_ref) / 100

  where T_ref = 21 degC (70 degF), the NATO EPVAT velocity-conditioning
  reference (AEP-97 / STANAG 4823).  A 5.56 at ~905 m/s with a 1.5
  fps/degF powder shifts ~0.091%/degC (+2.7% at +50 degC), while a 9mm
  at ~400 m/s with the same powder shifts ~0.206%/degC (+6.0%).  This is
  the physically correct, velocity-relative behaviour.

  Result is clamped to [0.85, 1.15] (a wider bound than the ±5% central
  range so sensitive powders at extreme temperatures stay modelled but
  cannot produce unphysical results).

Double-count guard:
  When ACE3 advanced ballistics is active (ammoTemperatureEnabled), ACE3
  applies its own per-ammo temperature table on Fired, fed by AEE's
  temperature through the compat layer.  Applying a second correction
  here would compound the effect.  This function returns 1.0 (no-op) in
  that case; the AEE correction is for the vanilla/no-ACE3 path and for
  third-party ballistics consumers reading aee_ballistics_muzzleVelocityCorrection.

  The projectile's velocity is NOT modified here: vanilla Arma offers no
  per-shot MV hook.  The correction factor is stored for ACE3-free
  ballistics consumers and for the advanced-ballistics compat layer.

Input:  [_ammo] - CfgAmmo classname (string)
        [_tempC] - propellant temperature in degC (default: AEE ambient)
Output: muzzle-velocity correction factor (1.0 = no change)
Sets:   QGVAR(muzzleVelocityCorrection)  (last computed factor)
*/

params [["_ammo", "", [""]], ["_tempC", -999, [0]]];

if (_ammo == "") exitWith { 1.0 };

// ─── ACE3 double-count guard ──────────────────────────────────────────────
if (isClass (configFile >> "CfgPatches" >> "ace_advanced_ballistics")) then {
    if (missionNamespace getVariable ["ace_advanced_ballistics_ammoTemperatureEnabled", false]) exitWith {
        missionNamespace setVariable [QGVAR(muzzleVelocityCorrection), 1.0];
        1.0
    };
};

// ─── Propellant temperature ───────────────────────────────────────────────
// Prefer the caller's value; fall back to the AEE ambient temperature.
if (_tempC <= -900) then {
    _tempC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 21];
    if !(_tempC isEqualType 0) then { _tempC = 21; };
};

// ─── Ammo muzzle velocity from CfgMagazines (initSpeed) ──────────────────
// initSpeed lives on the magazine; resolve the first magazine whose ammo
// class matches.  BIS_fnc_returnChildren yields config entries, so read
// the class name with configName before indexing.
private _initSpeed = 0;
{
    if (getText (configFile >> "CfgMagazines" >> configName _x >> "ammo") == _ammo) exitWith {
        _initSpeed = getNumber (configFile >> "CfgMagazines" >> configName _x >> "initSpeed");
    };
} forEach ((configFile >> "CfgMagazines") call BIS_fnc_returnChildren);
if (_initSpeed <= 0) exitWith { _initSpeed = 0; 1.0 };   // no MV data: no correction

// ─── Correction ───────────────────────────────────────────────────────────
private _coeff = [_ammo] call FUNC(calculatePropellantSensitivity);
private _mpsPerDegC = _coeff * 0.3048 * 1.8;
private _pctPerDegC = _mpsPerDegC / _initSpeed * 100;
private _correction = 1 + (_pctPerDegC * (_tempC - 21)) / 100;
_correction = _correction max 0.85 min 1.15;

missionNamespace setVariable [QGVAR(muzzleVelocityCorrection), _correction];

_correction
