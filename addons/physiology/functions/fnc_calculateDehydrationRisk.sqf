#include "..\script_component.hpp"

/*
Dehydration risk index (0–1) for ACE3 medical integration.
  0.0 = well hydrated
  1.0 = critical dehydration

Driven by two branches:
  HEAT  (WBGT >= 18): ISO 7243 WBGT-band sweat rate with per-player water
        deficit accumulation.  Clothing (uniform/vest) adds metabolic load.
  COLD  (WBGT < 18): no heat-stress sweat, but real cold exposure still
        causes fluid loss through two mechanisms (issue #92):
          - Respiratory water loss: cold air is dry; humidifying it to
            body conditions costs water each breath.  Model = the
            water-vapour deficit between saturated lung air (6.28 kPa at
            37 C) and ambient air, anchored to the verified rest rate of
            0.010 L/h at 25 C (deficit 3.1 kPa) / 0.020 L/h at -20 C
            (Freund & Sawka 1996 Table 9-2; Zielinski & Przybylski 2012),
            scaled by exertion (minute ventilation: rest 1x, walking 2x,
            running 3x).
          - Cold diuresis: vasoconstriction shifts blood centrally and
            the kidneys excrete.  The magnitude is debated and
            self-limiting (O'Brien 2005, Lennquist 1974), so the model
            uses a CONSERVATIVE term of up to 0.01 L/h (0.24 L/day) below
            10 C - well under the unverified 0.5-1.5 L/day figure, which
            no primary study supports as a constant.
        Both sum into the same deficit accumulator and risk map as the
        heat path; natural rehydration applies to both.

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
private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_T isEqualType 0) then { _T = 15; };

private _sweatAmount = 0;
private _coldLoss = 0;

if (_WBGT >= 18) then {
    // ─── HEAT branch: ISO 7243 sweat rate ──────────────────────────────
    // <18 safe, 18-23 caution, 23-28 extreme caution, 28-32 danger,
    // >32 very dangerous (heat stroke risk).
    private _sweatRate = switch (true) do {
        case (_WBGT < 23): { 0.3 };   // caution — light sweating
        case (_WBGT < 28): { 0.6 };   // extreme caution — moderate sweating
        case (_WBGT < 32): { 1.0 };   // danger — heavy sweating
        default            { 1.5 };   // very dangerous — profuse sweating
    };
    _sweatAmount = _sweatRate * _tickHours * GVAR(SweatRateScale);

    // Clothing modifier — uniform/vest impairs evaporative cooling
    if (!isNull uniformContainer _player) then { _sweatAmount = _sweatAmount + 0.2 * _tickHours; };
    if (!isNull vestContainer _player)        then { _sweatAmount = _sweatAmount + 0.2 * _tickHours; };
} else {
    // ─── COLD branch: respiratory loss + diuresis (issue #92) ─────────
    // Exertion from player speed (km/h): rest, walking, running.
    private _spd = speed _player;
    private _exertion = switch (true) do {
        case (_spd >= 12): { 3 };   // running / heavy work
        case (_spd >= 4):  { 2 };   // walking / light work
        default           { 1 };    // rest
    };

    // Buck saturation vapour pressure (kPa) at ambient temperature.
    private _esatAmb = 0.61094 * exp ((17.625 * _T) / (243.04 + _T));

    // Water-vapour deficit of inspired air: saturated lung air (6.28 kPa
    // at 37 C) minus ambient.  At 25 C that is ~3.1 kPa, at -20 C ~6.2 kPa.
    private _deficitKPa = (6.28 - _esatAmb) max 0;

    // Anchor to the verified rest rate: 0.010 L/h at 25 C (deficit 3.1).
    private _respRest = 0.010 * (_deficitKPa / 3.1);
    _coldLoss = _coldLoss + (_respRest * _exertion * _tickHours);

    // Cold diuresis — conservative, below 10 C, max 0.01 L/h at -10 C.
    if (_T < 10) then {
        _coldLoss = _coldLoss + (0.01 * ((10 - _T) / 20) * _tickHours);
    };
};

// ─── Natural decay — baseline rehydration (drinking, food water) ─────────
private _naturalDecay = GVAR(RehydrationRate) * _tickHours;      // L/hour

// ─── Accumulate deficit ──────────────────────────────────────────────────
_deficit = _deficit + _sweatAmount + _coldLoss - _naturalDecay;
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
if (_WBGT > 32 && (_deficit > 1.5)) then {
    _risk = _risk + (_WBGT - 32) * GVAR(HeatStrokeSensitivity);
};

_risk = _risk min 1 max 0;

// ─── Persist state ───────────────────────────────────────────────────────
_dehydAccum set [_uid, [_deficit, _now, _risk]];
missionNamespace setVariable [QGVAR(dehydrationAccum), _dehydAccum];
missionNamespace setVariable [QGVAR(dehydrationRisk), _risk];

_risk
