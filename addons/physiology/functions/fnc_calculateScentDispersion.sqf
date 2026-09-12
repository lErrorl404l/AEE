#include "..\script_component.hpp"

/*
Scent/olfactory dispersion intensity and direction for wildlife, AI
scent-tracking, and olfactory detection models.

Factors — each multiplies into the final 0–1 intensity:
  • Temperature — volatility bell curve peaking at 22 °C
  • Humidity    — >70 % traps scent particles against the ground
  • Rain        — washes scent to near-zero
  • Ground type — surface absorbency / reflectivity
  • Wind speed  — calm pools scent, moderate spreads, strong overpowers

All factors multiply (not sum) so any single near-zero factor suppresses
the whole signal — realistic scent chemistry.

Stored in GVAR(scentDispersionIntensity) (0–1) and
GVAR(scentDispersionDir) (degrees, downwind direction).
*/

params [];

// ─── Inputs ────────────────────────────────────────────────────────────────
private _wind = EGVAR(core,currentWind);
if (isNil "_wind") exitWith { 0 };

// currentWind is a velocity VECTOR, not [speed, direction].  Speed is the
// vector magnitude; direction comes from the separate currentWindDir state.
private _windSpeed = vectorMagnitude _wind;
private _windDir   = missionNamespace getVariable [QEGVAR(core,currentWindDir), 0];

private _temp       = EGVAR(core,currentTemperature);
private _humidity   = EGVAR(core,currentHumidity);

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];

// ─── Temperature — volatility bell curve ───────────────────────────────────
// Scent molecules volatilise most at moderate warmth; extreme cold or heat
// reduces detectable concentration.
private _tempFactor = 1;
if (!isNil "_temp") then {
    _tempFactor = 1 - (abs (_temp - 22) / 22) max 0;
};

// ─── Humidity — moisture traps scent ───────────────────────────────────────
// Above 70 %RH water films capture polar scent molecules, reducing airborne
// concentration.  currentHumidity is 0..100 percent, not a fraction.
private _humFactor = 1;
if (!isNil "_humidity") then {
    _humFactor = 1 - (0 max (_humidity - 70) * 0.015);
};

// ─── Rain — washout ────────────────────────────────────────────────────────
// Rain physically scours scent particles from air and surfaces.
private _rainFactor = 1;
if (rain > 0) then { _rainFactor = 0.2; };

// ─── Ground state — surface interaction ────────────────────────────────────
// Different surfaces retain or release scent differently.
private _groundFactor = switch (_groundState) do {
    case "Mud"   : { 0.4 };   // wet ground traps scent
    case "Dusty" : { 0.7 };   // loose particles carry scent
    case "Snow"  : { 0.2 };   // cold blanket suppresses
    case "Frozen": { 0.3 };   // frozen surface, minimal release
    default      { 0.6 };     // Normal / dry ground
};

// ─── Wind speed — advection ────────────────────────────────────────────────
private _windFactor = 1;
if (_windSpeed < 1) then {
    _windFactor = 0.8;              // calm — scent pools, low dispersion
} else {
    if (_windSpeed > 5) then {
        _windFactor = 0 max (1 - (_windSpeed - 5) * 0.05);  // strong — overpowers
    };
    // 1–5 m/s: factor stays 1.0 — ideal advection
};

// ─── Final intensity ───────────────────────────────────────────────────────
private _intensity = _tempFactor * _humFactor * _rainFactor * _groundFactor * _windFactor;
_intensity = _intensity max 0 min 1;

missionNamespace setVariable [QGVAR(scentDispersionIntensity), _intensity];
// currentWindDir is the direction the wind comes FROM; scent travels downwind
missionNamespace setVariable [QGVAR(scentDispersionDir), ((_windDir + 180) mod 360)];

_intensity
