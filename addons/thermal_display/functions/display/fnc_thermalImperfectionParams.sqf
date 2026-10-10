#include "..\..\script_component.hpp"

/*
Thermal-imperfection parameter kernel (image realism).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The thermal
display driver calls this once per tick and folds the four returned terms into
the existing display chain.  The detector's fixed-pattern noise (FPN) and its
NETD term already live in fnc_applyThermalVision.sqf; this kernel adds the
drift and hunting that sit on top of them.

Per-constant source register (UNSOURCED values are marked beside the clamp):
  temporal noise scale  1.0, range 0 to 2 (the operator setting, applied by
                        the driver).  Fixed-pattern and temporal noise are real
                        sensor noise.  FPN is DSNU plus PRNU, corrected by
                        flat-field or NUC and drifting with temperature,
                        integration time and gain (Wikipedia fixed-pattern
                        noise; EMVA Standard 1288).
  FPN and NETD          existing.  The display chain derives FPN amplitude
                        from the device NETD over the AGC window
                        (fnc_applyThermalVision.sqf:403).  Uncooled bolometer
                        NETD is 30 to 200 mK, cooled near 10 mK (Wikipedia
                        Noise-equivalent temperature, citing NMAB 1995).
                        Reused, not duplicated.
  AGC hunt amplitude    0.05, range 0 to 0.1.  AGC compresses dynamic range,
                        which produces breathing and washout (Wikipedia
                        Automatic gain control).  Hunting timescale
                        UNSOURCED.
  AGC hunt period       4.0 s, range 1 to 20 s.  UNSOURCED.  The AGC smooths
                        at a 0.5 s time constant
                        (fnc_updateThermalAGC.sqf:285-289), so the hunt sits
                        above it.  The hunt is a sine that is zero at entry
                        and negative at half the period: it pulls the display
                        gain down first, the gain overshoot of a real AGC.
  NUC drift amplitude   0.15, range 0 to 0.3.  FPN drifts and NUC is
                        refreshed (Wikipedia fixed-pattern noise; EMVA 1288).
                        The refresh cadence is UNSOURCED, modelled as a slow
                        co-prime sine at 37 s.
  Hot-source bloom      0.08, range 0 to 0.15.  Thermal blooming and haloing
                        have no authoritative source.  UNSOURCED.  It is the
                        DynamicBlur spike the NVG model uses for halo.
  Wake-up burst         0.5 s, fixed.  UNSOURCED.  A short interval after the
                        thermal view starts in which the artefacts sit at
                        their peak.  The driver passes a decaying settle
                        factor; the kernel scales the three artefacts by it.

Arguments:
  0: Number - scene contrast (0 to 1)
  1: Number - elapsed time, seconds
  2: Number - AGC hunt amplitude (0 to 0.1)
  3: Number - AGC hunt period, seconds (1 to 20)
  4: Number - NUC drift amplitude (0 to 0.3)
  5: Number - hot-source bloom base (0 to 0.15)
  6: Number - hot-source scalar (0 to 1)
  7: Number - settle factor (0 to 1; 1 at entry, decaying to 0)

Returns:
  Array - [bloom, agcHunt, nucDrift, temporalNoise]
*/

params [
    ["_contrast", 1, [0]],
    ["_time", 0, [0]],
    ["_huntAmp", 0.05, [0]],
    ["_huntPeriod", 4.0, [0]],
    ["_nucAmp", 0.15, [0]],
    ["_bloomBase", 0.08, [0]],
    ["_hot", 0, [0]],
    ["_settle", 0, [0]]
];

_huntAmp = (_huntAmp max 0) min 0.1;
_huntPeriod = (_huntPeriod max 1) min 20;
_nucAmp = (_nucAmp max 0) min 0.3;
_bloomBase = (_bloomBase max 0) min 0.15;
_hot = (_hot max 0) min 1;
_settle = (_settle max 0) min 1;

// AGC hunt: zero at entry, negative at half the period.  The half-rate sine
// gives that phase; the full cycle spans twice the named period.
private _agcHunt = -_huntAmp * sin(180 * _time / _huntPeriod);

// NUC drift: a slow, co-prime refresh cadence so it beats against the hunt.
private _nucDrift = _nucAmp * sin(360 * _time / 37);

private _bloom = _bloomBase * _hot;

// Wake-up burst: scale the three artefacts by the decaying settle factor.
_bloom = _bloom * _settle;
_agcHunt = _agcHunt * _settle;
_nucDrift = _nucDrift * _settle;

// Temporal noise: a fast jitter term, bounded to a unit factor.
private _noise = 0.5 + 0.5 * sin(360 * _time / 0.37);

_bloom = (_bloom max 0) min 0.15;
_agcHunt = (_agcHunt max -0.1) min 0.1;
_nucDrift = (_nucDrift max -0.3) min 0.3;
_noise = (_noise max 0) min 1;

[_bloom, _agcHunt, _nucDrift, _noise]
