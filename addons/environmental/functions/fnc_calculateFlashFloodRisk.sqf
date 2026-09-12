#include "..\script_component.hpp"

/*
Flash-flood risk index (0–1) driven by rainfall intensity (mm/h).

Intensity uses the same rain-to-mm/h mapping as the optics module:
1.0 engine rain = 25 mm/h. 50 mm/h is flash-flood-producing rain.

Antecedent moisture (accumulated rain) amplifies the response.
Arid soils have low infiltration — steep catchment response (1.0).
Non-arid terrain responds more slowly (0.5).

Risk recedes as intensity falls once rain stops.

Stored in QGVAR(flashFloodRisk).
*/



private _rainRate  = rain;
private _rainAccum = missionNamespace getVariable [QGVAR(rainAccum), 0];
private _biome     = EGVAR(core,biome);

if (isNil "_rainRate") then { _rainRate = 0; };

// ─── Intensity (mm/h) — same mapping as the optics module ─────────────────
private _intensity = _rainRate * 25;

// ─── Antecedent moisture — existing accumulated-rain state ────────────────
private _antecedent = _rainAccum;

// ─── Catchment response — arid = steep (1.0), other = flat (0.5) ──────────
private _isArid = false;
if (!isNil "_biome") then { _isArid = _biome in ["BWh","BWk","BSh","BSk"]; };
private _terrainFactor = [0.5, 1.0] select _isArid;

// ─── Risk — 50 mm/h ~ flash-flood-producing rain ──────────────────────────
private _risk = (_intensity / 50) * (1 + _antecedent) * _terrainFactor;

_risk = _risk max 0 min 1;

missionNamespace setVariable [QGVAR(flashFloodRisk), _risk];

if (_risk > 0.6 && (EGVAR(core,diagnostic))) then {
    diag_log text "[AEE] HIGH FLASH FLOOD RISK — reduce vehicle movement, monitor low-lying areas";
};

_risk
