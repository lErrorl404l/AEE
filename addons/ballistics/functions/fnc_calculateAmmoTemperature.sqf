#include "..\script_component.hpp"

/*
Track per-weapon ammunition temperature (issue #94).

Ammunition is not at ambient temperature in the field:
  - Cold ammo at -30 C: reduced muzzle velocity, increased drop, hang-fire
    risk (artillery and small arms cold-weather doctrine).
  - Hot ammo (sun-baked magazines, sustained fire): increased velocity and
    pressure.
  - A round sits in a magazine in a pouch or in the sun; the magazine
    exchanges heat with the environment on a ~10 minute time constant.

Model (per-unit, per-weapon, lazy first-order):
  dT/dt = (T_ambient - T) / tau + solarSoak + shotHeat

  State: unit getVariable [QGVAR(ammoTemps)] = createHashMap keyed by
  weapon class -> [tempC, lastTickSec].  Lazy: the value is relaxed only
  when read (on Fired), using the elapsed real time, so there is no PFH
  cost and the physics is exact regardless of tick rate.

  solarSoak: a magazine in direct sun heats above air temperature
  (dark metal absorbs shortwave).  Scaled by sun elevation and clear sky.
  shotHeat: each shot adds propellant heat to the rounds still in the
  weapon, scaled by round energy (proportional to initSpeed^2).

ACE3 interop (Option C): when ACE3 advanced ballistics owns ammo
temperature (ammoTemperatureEnabled), AEE's MV correction no-ops to avoid
double-counting; instead the tracked temperature is written into ACE3's
per-weapon variable (ace_overheating_weapon_ammoTemp) so ACE3's own table
uses AEE's live value.  When ACE3 is absent, the tracked temperature feeds
AEE's correction directly.

Input:  [_unit, _weapon] - unit and weapon class
        [_unit, _weapon, _shotEnergyJ] - add shot heat (on Fired)
Output: ammo temperature in degC
Sets:   unit getVariable [QGVAR(ammoTemps)]  (per-weapon state)
*/

params [["_unit", objNull, [objNull]], ["_weapon", "", [""]], ["_shotEnergyJ", 0, [0]]];

if (isNull _unit || _weapon == "") exitWith { 21 };

private _ambient = missionNamespace getVariable [QEGVAR(core,currentTemperature), 21];
if !(_ambient isEqualType 0) then { _ambient = 21; };

// ─── Solar soak: sun-baked magazines ──────────────────────────────────────
// Dark magazine metal absorbs shortwave radiation.  Simple model: up to
// +8 C above air temperature in full sun (sun elevation > 30, clear sky),
// falling to 0 under overcast or at night.  Sun elevation comes from the
// shared solar model.
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _overcast = missionNamespace getVariable [QEGVAR(core,overcast), 0];
if !(_overcast isEqualType 0) then { _overcast = 0; };
private _sunFactor = (0 max (_sunElev / 45)) min 1;           // 0 night .. 1 high sun
private _skyFactor = (1 - _overcast) max 0.1;                 // 0.1 overcast .. 1 clear
private _solarSoak = 8 * _sunFactor * _skyFactor;

private _soakAmbient = _ambient + _solarSoak;

// ─── Lazy first-order relaxation toward ambient ───────────────────────────
// A fresh weapon (no stored state) starts AT the soak-adjusted ambient,
// not the raw air temperature: a magazine first read in full sun is
// already sun-warmed.
private _state = _unit getVariable [QGVAR(ammoTemps), createHashMap];
private _entry = _state getOrDefault [_weapon, [_soakAmbient, diag_tickTime]];
_entry params ["_prevTemp", "_lastTick"];
private _dt = (diag_tickTime - _lastTick) max 0;

private _tau = missionNamespace getVariable [QGVAR(ammoTempTimeConstant), 600];
if !(_tau isEqualType 0) then { _tau = 600; };
_tau = _tau max 30;

private _temp = _soakAmbient + (_prevTemp - _soakAmbient) * exp (-_dt / _tau);

// ─── Shot heat ─────────────────────────────────────────────────────────
// Propellant heat adds to the rounds remaining in the weapon.  Scale by
// round energy: E = 0.5*m*v^2, and the powder mass tracks muzzle energy,
// so a sensible proxy is (v / 905)^2 * 0.06 degC per shot (5.56 NATO
// baseline ~0.06 degC/shot at 905 m/s; a 9mm at 400 m/s heats ~0.012
// degC/shot).  The caller passes the round's energy in J.
if (_shotEnergyJ > 0) then {
    private _heatPerShot = missionNamespace getVariable [QGVAR(ammoHeatPerShotJ), 0.0001];
    if !(_heatPerShot isEqualType 0) then { _heatPerShot = 0.0001; };
    _temp = _temp + (_shotEnergyJ * _heatPerShot);
};

_state set [_weapon, [_temp, diag_tickTime]];
_unit setVariable [QGVAR(ammoTemps), _state];

_temp
