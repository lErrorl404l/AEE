#include "..\script_component.hpp"

/*
Sea state and wave height via Beaufort scale approximation.

Method:
  1. Convert ACE wind speed (m/s) → knots (×1.944)
  2. Beaufort number: B = round(sqrt(knots^1.5)), clipped 0–12
  3. Exponential smoothing: new = prev×0.7 + raw×0.3
  4. Wave height: ~B² × 0.1 (rough empirical proxy)

Stored in:
  GVAR(seaStateBeaufort)     (0–12 integer)
  GVAR(waveHeight_m)         (float metres)
  GVAR(seaStateDescription)  (human-readable Beaufort label)
  GVAR(seaStateCurrent)      (smoothed float, for next tick)
*/

params [];

private _wind = EGVAR(core,currentWind);
if (isNil "_wind") exitWith { 0 };

private _speed = _wind select 0;

// ─── Beaufort from wind speed ──────────────────────────────────────────────
private _knots    = _speed * 1.944;
private _beaufort = round (sqrt ((_knots ^ 1.5) max 0));
_beaufort = _beaufort max 0 min 12;

// ─── Exponential smoothing — wind needs duration to build sea ──────────────
private _prev   = missionNamespace getVariable [QEGVAR(core,seaStateCurrent), _beaufort];
private _smooth = (_prev * 0.7) + (_beaufort * 0.3);
_smooth = _smooth max 0 min 12;
private _beaufortInt = round _smooth;

// ─── Wave height (rough Beaufort-based approximation) ──────────────────────
private _waveH = (_beaufortInt ^ 2) * 0.1;

// ─── Beaufort description ──────────────────────────────────────────────────
private _descriptions = [
    "Calm", "Glassy", "Light", "Gentle", "Moderate", "Fresh",
    "Strong", "High", "Gale", "Strong Gale", "Storm", "Violent", "Hurricane"
];
private _desc = _descriptions select _beaufortInt;

// ─── Store ─────────────────────────────────────────────────────────────────
missionNamespace setVariable [QEGVAR(core,seaStateCurrent),     _smooth];
missionNamespace setVariable [QEGVAR(core,seaStateBeaufort),    _beaufortInt];
missionNamespace setVariable [QEGVAR(core,waveHeight_m),        _waveH];
missionNamespace setVariable [QEGVAR(core,seaStateDescription), _desc];

_beaufortInt
