#include "..\script_component.hpp"

/*
Chemical/biological persistence decay modifier (≈0.5–2.0).

A single aggregate multiplier describing how quickly chemical or biological
agents break down or disperse in the current environment.

  >1.0 = faster decay (warm, windy, sunny)
  <1.0 = slower decay (cool, humid, calm, overcast)

Four factors are combined:
  • Temperature   — warm accelerates evaporation/volatilisation
  • Humidity      — moisture absorbs agents, slowing decay
  • Wind          — disperses agent cloud, increases effective decay
  • Solar (UV)    — photochemical breakdown; reduced by overcast

ponytail: a simple aggregate decay modifier, not a full chemical agent
transport model.
Stored in QEGVAR(core,cbrnPersistence).
*/

// ─── Inputs ────────────────────────────────────────────────────────────────
private _temp_C  = EGVAR(core,currentTemperature);
private _humidity = EGVAR(core,currentHumidity);
private _windSpd  = vectorMagnitude wind;
private _overcast = overcast;

if (isNil "_temp_C")   then { _temp_C   = 15; };
if (isNil "_humidity") then { _humidity = 50; };

// ─── Temperature factor ────────────────────────────────────────────────────
// Warmer → faster decay (volatilisation, evaporation)
private _tempFactor = 0.3 + (_temp_C + 10) * 0.015;
_tempFactor = _tempFactor max 0.2 min 1.5;

// ─── Humidity factor ───────────────────────────────────────────────────────
// Moisture absorbs agent, slowing atmospheric decay
private _humidityFactor = 0.7 + (_humidity / 100) * 0.6;
_humidityFactor = _humidityFactor max 0.7 min 1.3;

// ─── Wind factor ───────────────────────────────────────────────────────────
// Wind disperses agent, increasing effective decay
private _windFactor = 1.0 + (_windSpd / 20);
_windFactor = _windFactor max 1.0 min 2.0;

// ─── Solar (UV) factor ─────────────────────────────────────────────────────
// UV breaks down agents; overcast reduces the effect
private _solarFactor = 1.0 + (1 - _overcast) * 0.5;
_solarFactor = _solarFactor max 1.0 min 1.5;

// ─── Combined ──────────────────────────────────────────────────────────────
private _modifier = ((_tempFactor + _humidityFactor) / 2) * _windFactor * (_solarFactor / 2);

missionNamespace setVariable [QEGVAR(core,cbrnPersistence), _modifier];

_modifier
