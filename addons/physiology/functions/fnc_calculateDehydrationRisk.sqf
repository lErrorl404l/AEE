#include "..\script_component.hpp"

/*
Dehydration risk index (0–1) for ACE3 medical integration.
  0.0 = well hydrated
  1.0 = critical dehydration

Driven by WBGT-derived sweat rate with per-player water deficit accumulation.
Clothing (uniform/vest) adds metabolic load in hot conditions.

Per-player state stored in QGVAR(dehydrationAccum) hashmap keyed by player UID.
Each entry: [waterDeficit_L, lastUpdateTime, currentRisk]
*/

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };

private _uid = getPlayerUID _player;
private _dehydAccum = missionNamespace getVariable [QGVAR(dehydrationAccum), createHashMap];
private _myState = _dehydAccum getOrDefault [_uid, [0, 0, 0]];
_myState params ["_deficit", "_lastTime", "_lastRisk"];
private _now = diag_tickTime;
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _tickHours = _interval / 3600;

private _WBGT = missionNamespace getVariable [QEGVAR(core,currentWBGT), 15];

// ─── Below thermoneutral zone: no heat stress, decay deficit ──────────────
if (_WBGT < 18) exitWith {
    _deficit = (_deficit - _deficit * 0.1) max 0;
    _dehydAccum set [_uid, [_deficit, _now, 0]];
    missionNamespace setVariable [QGVAR(dehydrationAccum), _dehydAccum];
    missionNamespace setVariable [QGVAR(dehydrationRisk), 0];
    0
};

// ─── Sweat rate (L/hour, linear with WBGT above threshold) ───────────────
private _sweatRate = 0.3 + (_WBGT - 18) * 0.05;   // 0.3 at 18°C, ~1.15 at 35°C
private _sweatAmount = _sweatRate * _tickHours;

// Clothing modifier — uniform/vest impairs evaporative cooling
if (!isNull uniformContainer _player) then { _sweatAmount = _sweatAmount + 0.2 * _tickHours; };
if (!isNull vestContainer _player)        then { _sweatAmount = _sweatAmount + 0.2 * _tickHours; };

// ─── Natural decay — baseline rehydration (drinking, food water) ─────────
private _naturalDecay = 0.05 * _tickHours;      // 0.05 L/hour

// ─── Accumulate deficit ──────────────────────────────────────────────────
_deficit = _deficit + _sweatAmount - _naturalDecay;
_deficit = _deficit max 0;

// ─── Risk calculation (0–1) ──────────────────────────────────────────────
private _risk = switch (true) do {
    case (_deficit < 0.5): { 0 };
    case (_deficit < 1.0): { (_deficit - 0.5) * 0.5 };                    // mild
    case (_deficit < 2.0): { 0.25 + (_deficit - 1.0) * 0.25 };            // moderate
    case (_deficit < 3.0): { 0.5  + (_deficit - 2.0) * 0.25 };            // severe
    default                { 0.75 };                                        // critical
};

// ─── Heat stroke overlay — dangerous combination of heat + fluid loss ───
if (_WBGT > 32 && _deficit > 1.5) then {
    _risk = _risk + (_WBGT - 32) * 0.03;
};

_risk = _risk min 1 max 0;

// ─── Persist state ───────────────────────────────────────────────────────
_dehydAccum set [_uid, [_deficit, _now, _risk]];
missionNamespace setVariable [QGVAR(dehydrationAccum), _dehydAccum];
missionNamespace setVariable [QGVAR(dehydrationRisk), _risk];
missionNamespace setVariable ["ace_medical_dehydrationRisk", _risk];

_risk
