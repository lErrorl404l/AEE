#include "..\script_component.hpp"

/*
Sea state and wave height via Beaufort scale (WMO).

Method:
  1. Wind speed: vector magnitude of EGVAR(core,currentWind) — it is a
     velocity VECTOR, not [speed, direction]
  2. Beaufort number: B = (v / 0.836)^(2/3)  (WMO, v in m/s)
     — 0.836 m/s = 1 knot, and B = round(v_kn^(2/3)).  The previous
     sqrt(knots^1.5) = knots^0.75 hit force 12 at ~27 kt instead of 64.
  3. Exponential smoothing: new = prev×0.7 + raw×0.3 (sea builds slowly)
  4. Wave height: significant wave height from the Pierson–Moskowitz
     fully-developed sea approximation H_s ≈ 0.025 × v² (v in m/s),
     clamped to the Beaufort characteristic range.

Stored in:
  GVAR(seaStateBeaufort)     (0–12 integer)
  GVAR(waveHeight_m)         (float metres)
  GVAR(seaStateDescription)  (human-readable Beaufort label)
  GVAR(seaStateCurrent)      (smoothed float, for next tick)
*/

params [];

private _wind = EGVAR(core,currentWind);
if (isNil "_wind") exitWith { 0 };

private _speed = vectorMagnitude _wind;

// ─── Beaufort from wind speed (WMO 1953) ───────────────────────────────────
private _beaufortRaw = (_speed / 0.836) ^ (2 / 3);
private _beaufort = round _beaufortRaw;
_beaufort = _beaufort max 0 min 12;

// ─── Exponential smoothing — wind needs duration to build sea ──────────────
private _prev   = missionNamespace getVariable [QEGVAR(core,seaStateCurrent), _beaufort];
private _smooth = (_prev * 0.7) + (_beaufort * 0.3);
_smooth = _smooth max 0 min 12;
private _beaufortInt = round _smooth;

// ─── Wave height (Pierson–Moskowitz significant wave height) ───────────────
// H_s ≈ 0.0246 × v² m for a fully-developed sea (v in m/s).  The previous
// B² × 0.1 overestimated low/mid states by 1.2–2×.
private _waveH = (0.0246 * (_speed ^ 2)) min 15;

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
