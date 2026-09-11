#include "..\script_component.hpp"

/*
Altitude acclimatization and Acute Mountain Sickness (AMS) risk (0–1).

Tracks cumulative time spent in altitude zones and detects rapid ascents
(>500 m/tick or helicopter-drop scenarios) for AMS onset modelling.

Per-player state stored in QGVAR(altitudeState) hashmap keyed by player UID.
Each entry: [acclimatizedTime_min, lastAltitude_m, lastUpdateTime, amsRisk, timeAbove3000m_min]
*/

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };

private _uid = getPlayerUID _player;
private _altState = missionNamespace getVariable [QGVAR(altitudeState), createHashMap];
private _myState = _altState getOrDefault [_uid, [0, 0, diag_tickTime, 0, 0]];
_myState params ["_acclimTime", "_lastAlt", "_lastUpdate", "_lastAMS", "_timeAbove3000"];
private _now = diag_tickTime;
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];

private _currentAlt = (getPosASL _player) select 2;
if (_currentAlt < 0) then { _currentAlt = 0; };

// ─── Altitude zones ──────────────────────────────────────────────────────
// Tick progression (minutes of simulated time per tick at 5s nominal)
private _tickMinutes = _interval / 60;

private _acclimDelta = 0;
private _above3000 = false;

switch (true) do {
    // Safe zone — below 2000m: decay acclimatization
    case (_currentAlt < 2000): {
        _acclimDelta = -1 * _tickMinutes;
    };
    // Mild zone — 2000–3000m: slow adaptation
    case (_currentAlt < 3000): {
        _acclimDelta = 0.5 * _tickMinutes;
    };
    // Moderate zone — 3000–4000m: slower adaptation
    case (_currentAlt < 4000): {
        _acclimDelta = 0.25 * _tickMinutes;
        _above3000 = true;
    };
    // High zone — >4000m: no adaptation, fastest AMS onset
    default {
        _acclimDelta = 0;
        _above3000 = true;
    };
};

// Update acclimatized time (floor at 0)
_acclimTime = (_acclimTime + _acclimDelta) max 0;

// Track cumulative time above 3000m
if (_above3000) then {
    _timeAbove3000 = _timeAbove3000 + _tickMinutes;
};

// ─── Ascent rate detection ───────────────────────────────────────────────
private _rapidAscent = 0;
private _ascentRate = _currentAlt - _lastAlt;

if (_ascentRate > 500) then {
    _rapidAscent = (_ascentRate / 500) * 0.2;
};

// Helicopter drop: from below 1000m to above 2500m in one tick
if (_lastAlt < 1000 && (_currentAlt > 2500)) then {
    _rapidAscent = _rapidAscent + 0.3;
};

// ─── AMS risk formula ────────────────────────────────────────────────────
private _baseAMS = 0;

if (_currentAlt > 2500) then {
    // Altitude-scaled base risk: 0 at 2500m, 0.375 at 4000m
    _baseAMS = (_currentAlt - 2500) / 4000;

    // Unacclimatised penalty — risk scales inversely with acclimatization
    if (_acclimTime < 60) then {
        _baseAMS = _baseAMS * (1 - _acclimTime / 60);
    };

    // Some protection after prolonged exposure above 3000m
    if (_timeAbove3000 > 180) then {
        _baseAMS = _baseAMS * 0.5;
    };
};

private _amsRisk = _baseAMS + _rapidAscent;
_amsRisk = _amsRisk min 1 max 0;

// ─── Acclimatization percent (0–100%, 240 min = fully adapted) ───────────
private _acclimPercent = (_acclimTime / 240) min 1;

// ─── Persist state ───────────────────────────────────────────────────────
_altState set [_uid, [_acclimTime, _currentAlt, _now, _amsRisk, _timeAbove3000]];
missionNamespace setVariable [QGVAR(altitudeState), _altState];
missionNamespace setVariable [QGVAR(amsRisk), _amsRisk];
missionNamespace setVariable [QGVAR(acclimatizationPercent), _acclimPercent];

_amsRisk
