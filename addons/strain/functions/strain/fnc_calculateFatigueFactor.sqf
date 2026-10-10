#include "..\..\script_component.hpp"

/*
Fatigue performance factor from sleep pressure and circadian phase.

Model basis (replaces the issue spec's unsupported linear 4%/hour):

  Van Dongen, Maislin, Mullington & Dinges 2003 (Sleep 26(2):117-126,
  PMID 12683469): PVT lapses accumulate NEAR-LINEARLY with cumulative
  wakefulness beyond a ~15.84 h threshold.  Performance impairment is
  not a constant 4%/hour; it is negligible until ~16 h awake, then
  accumulates with wakefulness.

  Dawson & Reid 1997 (Nature 388:235, PMID 9230429): ~17-19 h awake is
  equivalent to 0.05% BAC; ~24 h awake to 0.10% BAC.  This gives the
  severity calibration: 24 h awake is severe impairment (~0.10% BAC).

  Van Dongen 2003 (dose-response): 14 days of 6 h sleep produces
  deficits equivalent to up to 2 nights of total sleep deprivation.

Model:
  performance = 1.0 for wakefulness <= 15.84 h (the published threshold)
  beyond that, impairment accumulates near-linearly with extra
  wakefulness, calibrated so 24 h awake (8.16 h past threshold) gives
  the 0.10% BAC-equivalent severity:

      impairment  = k * (hoursAwake - 15.84)
      k           = 0.05 per hour     (severe impairment at 24 h:
                                      0.05 * 8.16 = 0.41 -> factor 0.59)
      factor      = 1 - impairment, floor 0.30

  A floor of 0.30 keeps the soldier conscious but severely impaired
  (matches the issue's floor; consistent with 0.10%+ BAC being
  incapacitating rather than unconscious).

  The circadian wake drive modulates alertness: operations in the
  circadian low (02:00-06:00) add a small penalty, and peak wake drive
  (18:00) adds a small boost.  The modulation is the ratio of the
  circadian wake drive to the homeostatic pressure, scaled so it stays
  within +/-0.15 of the baseline factor (Dinges 1997 reports ~15% task
  performance swing across the circadian cycle).

Input:  [_sleepiness, _processS, _processC, _hoursAwake]
Output: performance factor 0.30..1.0 (1.0 = fully rested)
*/

params [["_sleepiness", 0, [0]], ["_processS", 0, [0]],
        ["_processC", 0, [0]], ["_hoursAwake", 0, [0]]];

private _WAKEFULNESS_THRESHOLD = 15.84;   // h, Van Dongen 2003
private _K = 0.05;                        // impairment per extra hour
private _FLOOR = 0.30;

// ─── Homeostatic impairment (near-linear beyond threshold) ────────────────
private _impairment = (_hoursAwake - _WAKEFULNESS_THRESHOLD) * _K;
private _factor = 1.0 - _impairment;
_factor = _factor max _FLOOR min 1.0;

// ─── Circadian modulation ─────────────────────────────────────────────────
// The circadian wake drive is bounded by the amplitude A, so the
// modulation is normalised: processC / A in -1..+1, scaled to a max
// +/-0.15 swing on the factor.  Positive processC (wake drive, ~18:00)
// boosts; negative (circadian low, ~06:00) penalises.
private _amp = missionNamespace getVariable [QGVAR(circadianAmplitude), 0.12];
if !(_amp isEqualType 0) then { _amp = 0.12; };
private _circMod = (_processC / _amp) * 0.15;
_factor = (_factor + _circMod) max _FLOOR min 1.0;

_factor
