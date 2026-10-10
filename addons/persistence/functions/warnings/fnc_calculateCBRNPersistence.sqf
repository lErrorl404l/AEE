#include "..\..\script_component.hpp"

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
private _temp_C  = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _windSpd  = vectorMagnitude wind;
private _interval = EGVAR(core,updateInterval);

if (isNil "_temp_C")   then { _temp_C   = 15; };
if (isNil "_humidity") then { _humidity = 50; };

// ─── Temperature — Q10 scaling (rate doubles per 10 °C) ────────────────────
// Base persistence lives in compat_acm (ACM loaded) with a 24 h fallback
// when ACM is absent.
private _basePersistenceH = missionNamespace getVariable [QEGVAR(compat_acm,CBRNBasePersistence), 24];
private _rateMultiplier = 2 ^ ((_temp_C - 15) / 10);
private _persistenceH = _basePersistenceH / _rateMultiplier;

// ─── Humidity — high humidity accelerates hydrolysis ───────────────────────
// At 100 %RH persistence ×0.67, at 0 %RH ×2.0
private _humidityFactor = 1 / (1 + ((_humidity - 50) / 50) * 0.5);
_persistenceH = _persistenceH * _humidityFactor;

// ─── Wind — disperses the agent cloud ──────────────────────────────────────
private _windFactor = 1 / (1 + _windSpd * 0.05);
_persistenceH = _persistenceH * _windFactor;

// ─── Rain washout — the scent model's one non-overlapping factor ───────────
// The scent dispersion model (aee_weather) publishes its rain washout factor
// separately.  Rain scavenges the airborne agent, the washout term of the
// Gaussian plume (concentration falls with exp(-lambda x / u); Turner,
// "Workbook of Atmospheric Dispersion Estimates", 2nd ed, CRC, 1994), so it
// shortens persistence.  Only rain is reused.  Temperature, humidity and wind
// are NOT reused: this model already scales persistence by all three, so a
// second application would double-count.  The scent ground factor is NOT
// reused: it encodes scent detectability and its sign (snow and frozen ground
// suppress scent) inverts the surface-persistence physics.
// The 0.2-in-rain magnitude is the scent model's own constant
// (fnc_calculateScentDispersion) and is UNSOURCED as a CBRN scavenging
// coefficient.  The read is a soft sibling read by name, defaulting to 1 (no
// washout) when the scent model has not run.
private _scentRainFactor = missionNamespace getVariable ["aee_weather_scentRainFactor", 1];
if !(_scentRainFactor isEqualType 0) then { _scentRainFactor = 1; };
_persistenceH = _persistenceH * _scentRainFactor;

// ─── Decay per tick — exponential decay with the scaled time constant ──────
private _modifier = exp (-(_interval / 3600) / _persistenceH);

missionNamespace setVariable [QEGVAR(core,cbrnPersistence), _modifier];

_modifier
