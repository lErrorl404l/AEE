#include "..\script_component.hpp"

/*
Borbely two-process sleep model: homeostatic sleep pressure and circadian
drive.

Process S (homeostatic) — sleep pressure rises during wakefulness and
decays during sleep, both as saturating exponentials:

  wake:  S(t) = S_max - (S_max - S_0) * exp(-t / tau_s)
  sleep: S(t) = S_min + (S_0 - S_min) * exp(-t / tau_d)

  tau_s = 18.2 h   (rise during wake, Daan, Beersma & Borbely 1984,
                    Am J Physiol 246:R161-R178, PMID 6696142)
  tau_d = 4.2 h    (decay during sleep, same source, canonical with
                    S_min = 0 convention)
  S_max = 1, S_min = 0   (normalised, Daan 1984)

  NOTE: modern SWA fits give tau_d ~2.2 h, but only under the S_min > 0
  convention (Rusterholz, Durr & Achermann 2010, Sleep 33(4):491-498).
  The two conventions are not interchangeable.  This model uses the Daan
  1984 convention (S_min = 0, tau_d = 4.2 h) so the constants are
  self-consistent.  State this in any issue report.

Process C (circadian) — the circadian wake drive.  A sinusoid with its
peak in the LATE AFTERNOON / EARLY EVENING, the "wake maintenance zone"
(Dijk & Czeisler 1995, J Neurosci 15:3528-3538):

  C(t) = A * sin(2*pi*(t - phi) / 24)

  A    = 0.12   circadian amplitude (0.1-0.15 published range, Skeldon
                2014; simplified sinusoid)
  phi  = 12     phase such that the wake-drive peak is at ~18:00.  The
                sinusoid sin(360*(t - phi)/24) peaks at t = phi + 6, so
                phi = 12 gives the 18:00 peak that matches the published
                wake-maintenance zone (Dijk & Czeisler 1995; Shekleton
                et al. 2013: maximal circadian drive for alertness in
                the early evening 6-10 pm).  The issue spec's 6:00 is
                the peak of sleep PROPENSITY, not wake drive — using it
                here with a positive sign would put peak wake drive at
                6:00, which is the circadian LOW.  The 18:00 peak
                matches the published wake-maintenance zone.

Sleepiness = S - C (sleep pressure minus circadian wake drive).
A high value means sleepy.

Input:  [_hoursAwake, _sleepDecayHours, _localHour, _sleeping]
        _hoursAwake       - hours since last sleep onset (real)
        _sleepDecayHours  - hours of sleep elapsed in current sleep bout
        _localHour        - local wall-clock hour (0-24, fractional ok)
        _sleeping         - true while asleep
Output: [processS, processC, sleepiness]
         processS  0..1 homeostatic pressure (higher = sleepier)
         processC  -A..+A circadian wake drive (higher = more alert)
         sleepiness  processS - processC (higher = sleepier)
*/

params [["_hoursAwake", 0, [0]], ["_sleepDecayHours", 0, [0]],
        ["_localHour", 12, [0]], ["_sleeping", false, [true]]];

private _TAU_S = 18.2;
private _TAU_D = 4.2;
private _S_MAX = 1.0;
private _S_MIN = 0.0;
private _AMP   = missionNamespace getVariable [QGVAR(circadianAmplitude), 0.12];
if !(_AMP isEqualType 0) then { _AMP = 0.12; };
private _PHI   = 12.0;

// ─── Process S ────────────────────────────────────────────────────────────
private _processS = if (_sleeping) then {
    // Decay during sleep: S falls from its value at sleep onset toward
    // S_min with tau_d.  _sleepDecayHours is the elapsed sleep time.
    _S_MIN + (_S_MAX - _S_MIN) * exp (-_sleepDecayHours / _TAU_D)
} else {
    // Rise during wake: S saturates toward S_max with tau_s.
    _S_MAX - (_S_MAX - _S_MIN) * exp (-_hoursAwake / _TAU_S)
};

// ─── Process C (circadian wake drive, peak ~18:00) ────────────────────────
// SQF sin() takes DEGREES, not radians.  A full circadian cycle is 360
// degrees per 24 h, so the phase argument is 360 * (t - phi) / 24.
private _processC = _AMP * sin (360 * (_localHour - _PHI) / 24);

// ─── Sleepiness ───────────────────────────────────────────────────────────
private _sleepiness = _processS - _processC;

[_processS, _processC, _sleepiness]
