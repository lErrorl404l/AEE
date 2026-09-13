#include "..\script_component.hpp"

/*
Smoke dispersal time modifier (0.2–3.0).

Computes how long smoke persists relative to baseline:
  1.0 = default
  <1.0 = disperses faster (wind, turbulence, heat, rain)
  >1.0 = persists longer (moist air, cold stable air)

The model chains five atmospheric processes:

  1. Advection — wind carries the plume away and dilutes it.
  2. Turbulent diffusion — the plume spreads as σ ∝ √(K·t) (Taylor
     diffusion); dispersal time shortens with turbulence intensity.
  3. Hygroscopic growth — smoke particles grow in moist air (Köhler
     theory); growth raises optical density and extends persistence.
  4. Buoyancy — hot ground air rises and mixes the plume upward; a cold
     stable layer (inversion) traps smoke near the ground.
  5. Rain scavenging — droplets collect particles with washout
     coefficient Λ = ∫K(R)·N(R)dR, proportional to rain rate.

The factors multiply. Stored in QGVAR(smokeDispersalModifier) for
consumption by smoke-effect duration systems.
*/

params [["_unit", objNull, [objNull]]];
if (isNull _unit) exitWith { 0 };  // no unit on dedicated server

// ─── Inputs ────────────────────────────────────────────────────────────
private _windSpeed = vectorMagnitude (missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0]]);
private _humidity  = EGVAR(core,currentHumidity);
private _temp      = EGVAR(core,currentTemperature);
private _rain      = rain;
private _turbulence = missionNamespace getVariable [QEGVAR(core,currentTurbulence), 0];

if (isNil "_humidity")  then { _humidity  = 0.5; };
if (isNil "_temp")      then { _temp      = 20;  };
if (isNil "_rain")      then { _rain      = 0;   };

// Wind implies mechanical turbulence; keep the diffusion term coherent
// even when the turbulence index has not been computed.
_turbulence = _turbulence max (_windSpeed / 15);

// ─── Advection (wind) ───────────────────────────────────────────────────
private _advection = 1 / (1 + _windSpeed * 0.12);

// ─── Turbulent diffusion (Taylor, σ ∝ √(K·t)) ──────────────────────────
private _diffusion = 1 / (1 + _turbulence * 0.5);

// ─── Hygroscopic growth (Köhler theory) ─────────────────────────────────
// Humidity is a 0..1 fraction in this file. RH >50 % grows particles.
private _humidityFactor = 1.0;
if (_humidity > 0.5) then {
    _humidityFactor = 1 + (_humidity - 0.5) * 0.4;
};

// ─── Buoyancy (temperature) ─────────────────────────────────────────────
private _buoyancy = 1.0;
if (_temp > 15) then {
    _buoyancy = 1 / (1 + ((_temp - 15) / 10) * 0.15);
} else {
    if (_temp < 5) then {
        _buoyancy = 1.3;  // inversion traps smoke (fog/smog)
    };
};

// ─── Rain scavenging (Λ = ∫K(R)·N(R)dR) ─────────────────────────────────
private _scavenge = 1 / (1 + _rain * 3);

// ─── Combine ────────────────────────────────────────────────────────────
private _modifier = _advection * _diffusion * _humidityFactor * _buoyancy * _scavenge;

// Global scale from settings
_modifier = _modifier * (missionNamespace getVariable [QGVAR(smokePersistenceScale), 1.0]);

// Clamp
_modifier = _modifier max 0.2 min 3.0;

// ─── Store ─────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(smokeDispersalModifier), _modifier];

_modifier
