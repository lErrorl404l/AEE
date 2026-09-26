#include "..\script_component.hpp"

/*
Barrel thermal state per weapon: temperature and point-of-impact shift.

Physics (issue #130):
  Barrel thermal expansion bends the muzzle: the group centre shifts
  vertically (elevation only), not dispersion.  Bore diameter growth
  (6.7 um per 100 C) is negligible; the dominant term is the thermal
  gradient across the barrel wall curving the muzzle angle.

    dTheta_elev [mrad] = k * (T_barrel - T_ambient)

  k = 0.005-0.01 mrad/C for a rifle, 0.01-0.03 for a machine gun.
  Rule of thumb: rifle at +100 C = 0.5-1 mrad; MG at +300 C = 3-9 mrad.
  A 0.005 mrad/C rifle at +100 C gives 0.5 mrad = ~1.8 MOA.

  Per-round heat: .22LR 0.3 C/round, 5.56 0.8-1.5, 7.62 rifle 1-2,
  7.62 MG 2-4.  Saturation ~150 C rifle, ~500 C MG.  Cooling tau
  100-200 s rifle, 200-300 s MG (exponential to ambient).

  Cold-bore: the FIRST shot after a long cold soak lands HIGH by
  0.75-1 MOA (0.22-0.29 mrad), decaying by round 3-5.  This is a
  group-centre bias on top of the expansion term.

Input:  [_unit, _weapon] - unit and weapon class
        [_unit, _weapon, _shot, _roundsFired] - add heat on Fired
Output: barrel temperature in degC
Sets:   QGVAR(barrelTempC)         (degC, per last call)
        QGVAR(barrelPOIShiftMrad)  (elevation shift, positive = up)
        QGVAR(barrelColdBore)      (1 when the cold-bore bias applies)
State:  unit getVariable [QGVAR(barrelState)] = [tempC, roundsFired]
*/

params [["_unit", objNull, [objNull]], ["_weapon", "", [""]], ["_shot", false, [false]], ["_roundsFired", 0, [0]]];

if (isNull _unit || _weapon == "") exitWith { 21 };

private _ambient = missionNamespace getVariable [QEGVAR(core,currentTemperature), 21];
if !(_ambient isEqualType 0) then { _ambient = 21; };

// ─── Per-caliber parameters ───────────────────────────────────────────────
// Machine-gun class: rate of fire >= 600 rpm and belt-fed are MG signals;
// fall back to the weapon's mode list.  Heat per round and cooling tau
// follow the firearm class per the issue tables.  A weapon with no modes
// class is not an error: the engine warns when the read is attempted, so
// the class is tested first.
private _weaponCfg = configFile >> "CfgWeapons" >> _weapon;
private _mode = "";
if (isClass (_weaponCfg >> "modes")) then {
    _mode = getText (_weaponCfg >> "modes" >> "this");
};
private _isMG = (_weapon find "MMG" >= 0) || (_weapon find "LMG" >= 0) || {_mode find "fullauto" >= 0};
// ─── Cannon regime: the wear and heat coefficient is not held ─────────────
// No tier 1 to 4 source held here states a cannon barrel heating or erosion
// rate, for example degC per round at the service charge or mm of bore
// enlargement per round.  AMCP 706-150 (Interior Ballistics of Guns, US Army
// Materiel Command 1965, held) gives the heat-transfer and erosion model but
// not a per-gun coefficient.  The small-arms values below are fitted to
// cartridge barrels and are not transferred.  A cannon class therefore adds no
// per-round heat and takes no sourced point-of-impact coefficient, and the
// gap is recorded rather than filled with an invented number.
private _isCannon = (_weapon find "cannon" >= 0) || (_weapon find "howitzer" >= 0) || (_weapon find "mortar" >= 0);
private _heatPerRound = if (_isCannon) then { 0 } else { [1.0, 3.0] select _isMG };
private _tau = [150, 250] select _isMG;                // seconds

// ─── State ────────────────────────────────────────────────────────────────
private _state = _unit getVariable [QGVAR(barrelState), [_ambient, 0]];
_state params ["_tempC", "_rounds"];
if !(_tempC isEqualType 0) then { _tempC = _ambient; };
if !(_rounds isEqualType 0) then { _rounds = 0; };

// ─── Fired: add heat ─────────────────────────────────────────────────────
// _roundsFired defaults to 1 for the per-shot Fired call; a caller may
// pass the count of a burst/batch (docker test seeds 30 rounds at once).
if (_shot) then {
    private _n = (_roundsFired max 1);
    _tempC = _tempC + (_heatPerRound * _n);
    _rounds = _rounds + _n;
};

// ─── Cooling: exponential to ambient, rate-limited by frame time ────────
private _dt = diag_deltaTime;
if (_dt > 0) then {
    _tempC = _ambient + (_tempC - _ambient) * exp (-_dt / _tau);
};

// Persist state for the next call (only when the unit state is live).
_unit setVariable [QGVAR(barrelState), [_tempC, _rounds]];

// ─── POI shift (elevation only) ───────────────────────────────────────────
private _kMradPerC = if (_isCannon) then { 0 } else { [0.008, 0.02] select _isMG };
private _poiMrad = _kMradPerC * (_tempC - _ambient);

// ─── Cold-bore bias ──────────────────────────────────────────────────────
// First shot after a cold soak lands high; decays by round 3-5.  The
// bias applies while the barrel is still cold AND the round count is low.
private _coldBore = 0;
// The bias applies to shots 1-5 of a cold barrel.  An unfired barrel
// (_rounds == 0, a read-only call) has no first-shot bias.
if (_tempC - _ambient < 15 && _rounds >= 1 && _rounds <= 5) then {
    _coldBore = 1;
    _poiMrad = _poiMrad + (0.25 * (1 - (_rounds - 1) / 4) max 0);   // 0.25 mrad first, to 0 by round 5
};

missionNamespace setVariable [QGVAR(barrelTempC), _tempC];
missionNamespace setVariable [QGVAR(barrelPOIShiftMrad), _poiMrad];
missionNamespace setVariable [QGVAR(barrelColdBore), _coldBore];
missionNamespace setVariable [QGVAR(barrelWearModelled), !_isCannon];

_tempC
