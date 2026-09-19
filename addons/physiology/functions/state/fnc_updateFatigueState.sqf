#include "..\..\script_component.hpp"

/*
Sleep/fatigue state tracker: accumulates wakefulness and sleep time,
computes the Borbely sleep pressure and the fatigue performance factor.

State (persisted in missionNamespace, per player):
  QGVAR(wakefulnessHours)   - cumulative hours awake since last sleep bout
  QGVAR(sleepHours)         - cumulative hours asleep in the current bout
  QGVAR(sleepiness)         - Borbely sleepiness (processS - processC)
  QGVAR(fatigueFactor)      - performance factor 0.30..1.0
  QGVAR(sleepState)         - 1 = awake, 2 = sleeping (ACE3 isUnconscious
                              or the ACE/vanilla fatigue system marks it)

Sleep detection:
  A player is "asleep" when ACE3 marks them unconscious OR when the
  vanilla fatigue system reports low stamina for a sustained period
  (ACE_medical_isUnconscious).  Without ACE3, the mod uses the engine's
  unit state: a non-moving, prone unit at night with a relaxed weapon is
  treated as resting, which drives a slow recovery.  This is a
  conservative approximation — the mod does not force sleep, it tracks
  the state the mission/medical system already produces.

  sleepState persistence uses ACE3's variable when present, falling back
  to the engine state.  The recovery rate is scaled by sleep quality:
  a unit resting prone at night recovers at ~70% of the ideal rate.

Input:  [_unit, _deltaHours]
Output: [wakefulnessHours, sleepHours, sleepiness, fatigueFactor]
Sets:   QGVAR(wakefulnessHours), QGVAR(sleepHours), QGVAR(sleepiness),
        QGVAR(fatigueFactor), QGVAR(sleepState)
*/

params [["_unit", objNull, [objNull]], ["_deltaHours", 0, [0]]];

// Resolve the local unit and tick duration if not given.  The core PFH
// runs on the update interval (default 5 s), so the state accumulates
// in ~5 s steps of real mission time.
if (isNull _unit) then {
    _unit = call CBA_fnc_currentUnit;
};
if (_deltaHours <= 0) then {
    private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
    _deltaHours = _interval / 3600;
    if !(_deltaHours isEqualType 0) then { _deltaHours = 5 / 3600; };
};

// Headless / no local unit: still accumulate wakefulness so the shared
// state stays consistent across machines (deterministic mission time).
// Sleep detection needs a unit, so without one we assume awake.
private _hasUnit = !isNull _unit;

// ─── Load state ───────────────────────────────────────────────────────────
private _wakeH = missionNamespace getVariable [QGVAR(wakefulnessHours), 0];
private _sleepH = missionNamespace getVariable [QGVAR(sleepHours), 0];
if !(_wakeH isEqualType 0) then { _wakeH = 0; };
if !(_sleepH isEqualType 0) then { _sleepH = 0; };

// Local hour for circadian phase and the resting heuristic.
private _localHour = 12;
if !(isNil "date") then {
    _localHour = date select 3 + (date select 4) / 60;
};

// ─── Sleep state detection ────────────────────────────────────────────────
private _sleeping = false;
if (_hasUnit) then {
    if (isClass (configFile >> "CfgPatches" >> "ace_medical")) then {
        // ACE3: unconscious IS sleep for fatigue purposes (recovery).
        _sleeping = _unit getVariable ["ACE_isUnconscious", false];
    } else {
        // No ACE3: resting heuristic — prone, still, at night, sustained.
        // Track consecutive resting seconds; 5 min of prone stillness at
        // night counts as rest.  Movement resets the counter.
        private _resting = (
            (stance _unit in ["PRONE", "CROUCH"]) &&
            (speed _unit < 0.1) &&
            ((_localHour >= 21) || (_localHour <= 6))
        );
        private _restSec = _unit getVariable [QGVAR(restingSeconds), 0];
        if (_resting) then {
            _restSec = _restSec + _deltaHours * 3600;
        } else {
            _restSec = 0;
        };
        _unit setVariable [QGVAR(restingSeconds), _restSec];
        _sleeping = _restSec > 300;
    };
} else {
    // No unit: assume awake (headless server accumulates wakefulness only).
    _sleeping = false;
};
if !(_sleeping isEqualType true) then { _sleeping = false; };

// ─── Accumulate ───────────────────────────────────────────────────────────
if (_sleeping) then {
    _wakeH = 0;
    _sleepH = _sleepH + _deltaHours;
} else {
    _sleepH = 0;
    _wakeH = _wakeH + _deltaHours;
};
missionNamespace setVariable [QGVAR(wakefulnessHours), _wakeH];
missionNamespace setVariable [QGVAR(sleepHours), _sleepH];

// ─── Borbely pressure + fatigue factor ────────────────────────────────────
private _sleepPressure = [_wakeH, _sleepH, _localHour, _sleeping]
    call FUNC(calculateSleepPressure);
_sleepPressure params ["_processS", "_processC", "_sleepiness"];

private _fatigue = [_sleepiness, _processS, _processC, _wakeH]
    call FUNC(calculateFatigueFactor);

missionNamespace setVariable [QGVAR(sleepiness), _sleepiness];
missionNamespace setVariable [QGVAR(fatigueFactor), _fatigue];
missionNamespace setVariable [QGVAR(sleepState), [1, 2] select _sleeping];

[_wakeH, _sleepH, _sleepiness, _fatigue]
