#include "..\script_component.hpp"

/*
Chemical/biological agent persistence (hours) — Arrhenius / Q10 hydrolysis.

Decay rate roughly doubles per 10 °C rise (Q10 = 2 rule of thumb for
hydrolysis). Persistence is the time constant of exponential decay:

  • Temperature   — Q10 scaling: decay rate ×2 per +10 °C
  • Humidity      — high humidity accelerates hydrolysis (shorter persistence)
  • Wind          — disperses the agent cloud (shorter persistence)

Base persistence is configurable at 15 °C, divided by the temperature rate
multiplier, the humidity factor and the wind factor. The stored value is
the per-tick exponential decay factor with that time constant.

Stored in QEGVAR(core,cbrnPersistence).
*/

// ─── Inputs ────────────────────────────────────────────────────────────────
private _temp_C  = EGVAR(core,currentTemperature);
private _humidity = EGVAR(core,currentHumidity);
private _windSpd  = vectorMagnitude wind;
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];

if (isNil "_temp_C")   then { _temp_C   = 15; };
if (isNil "_humidity") then { _humidity = 50; };

// ─── Temperature — Q10 scaling (rate doubles per 10 °C) ────────────────────
private _basePersistenceH = GVAR(CBRNBasePersistence);
private _rateMultiplier = 2 ^ ((_temp_C - 15) / 10);
private _persistenceH = _basePersistenceH / _rateMultiplier;

// ─── Humidity — high humidity accelerates hydrolysis ───────────────────────
// At 100 %RH persistence ×0.67, at 0 %RH ×2.0
private _humidityFactor = 1 / (1 + ((_humidity - 50) / 50) * 0.5);
_persistenceH = _persistenceH * _humidityFactor;

// ─── Wind — disperses the agent cloud ──────────────────────────────────────
private _windFactor = 1 / (1 + _windSpd * 0.05);
_persistenceH = _persistenceH * _windFactor;

// ─── Decay per tick — exponential decay with the scaled time constant ──────
private _modifier = exp (-(_interval / 3600) / _persistenceH);

missionNamespace setVariable [QEGVAR(core,cbrnPersistence), _modifier];

_modifier
