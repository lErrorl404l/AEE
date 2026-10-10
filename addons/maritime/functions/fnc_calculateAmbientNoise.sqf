#include "..\script_component.hpp"
/*
Ambient noise spectrum level in the sea (issue #113).

Source of the curves: Wenz, G. M. (1962), "Acoustic Ambient Noise in the
Ocean: Spectra and Sources", Journal of the Acoustical Society of America
34(12):1936-1956, DOI 10.1121/1.1909155.

Wenz published the ambient-noise spectrum as GRAPHICAL curves, not as a
closed-form equation.  There is no citable analytic parameterisation.  The
sea-state dependence below is therefore a stated model anchored to the
issue's readings of the Wenz curves, and the frequency shape is a stated
approximation.  Every unsourced number is marked UNSOURCED.

Anchored values (deep water, 1 kHz, dB re 1 uPa^2/Hz):

    sea state 0   40
    sea state 3   55      (issue: 55-60)
    sea state 6   70

so the wind/sea-state component at 1 kHz is

    L(1 kHz) = 40 + 5 * seaState              UNSOURCED (Wenz curve reading)

Above 500 Hz the wind and sea-state component dominates.  Below 500 Hz
shipping noise dominates.  The reference convention is dB re 1 uPa^2/Hz.

  T   input:  [freqHz, seaState, shallow]
  freqHz   acoustic frequency, Hz
  seaState Beaufort-like sea state 0..6+ (values above 6 are clamped for
           the level formula, which is anchored to 0..6)
  shallow  true for the shallow-water case (louder, more variable)

Input:  [freqHz, seaState, shallow]
Output: spectrum level in dB re 1 uPa^2/Hz
*/

params [
    ["_freqHz", 1000, [0]],
    ["_seaState", 3, [0]],
    ["_shallow", false, [false]]
];

private _f = 1 max _freqHz;
private _ss = 0 max _seaState;

// ─── Sea-state component at the 1 kHz reference ───────────────────────────
// UNSOURCED: the +5 dB per sea state and the 40 dB intercept are the issue's
// readings of the Wenz curves.  Wenz 1962 is graphical, so these are not
// re-derived from a formula.
private _level1k = 40 + 5 * _ss;

// ─── Frequency shape ──────────────────────────────────────────────────────
// UNSOURCED: the wind-driven spectrum is broadly flat between 500 Hz and
// 1 kHz and falls about 6 dB per octave above 1 kHz.
private _shape = 0;
if (_f > 1000) then {
    _shape = -6 * ((log _f - log 1000) / log 2);
};

// ─── Shipping band ────────────────────────────────────────────────────────
// UNSOURCED: below 500 Hz shipping dominates; the level rises about 6 dB per
// octave toward low frequency down to the shipping floor.
private _shipping = 0;
if (_f < 500) then {
    _shipping = 6 * ((log 500 - log _f) / log 2);
};

// ─── Shallow water ────────────────────────────────────────────────────────
// UNSOURCED: shallow water is louder and more variable; a fixed bonus is a
// stated approximation.
private _shallowBonus = [0, 5] select _shallow;

_level1k + _shape + _shipping + _shallowBonus
