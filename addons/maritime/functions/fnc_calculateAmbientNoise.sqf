#include "..\script_component.hpp"
/*
Deep-water ambient-noise spectrum level in the sea (issue #113).

Two published components, energy-summed:

  1. Wind / sea-surface noise, Wenz's "rule of fives".  The spectral levels
     are those measured by Knudsen, Alford and Emling (1948) and compiled
     by Wenz (1962):

         NL_wind(f, U) = 51.02 - (50/3) * (log10 f_kHz - log10 (U_kn / 5))

     with f in kHz and U in knots.  That is -5 dB per octave of frequency
     and +5 dB per doubling of wind speed about the anchor "25 dB (5 x 5)"
     at 1 kHz for 5 knots re 20 uPa, which is 25 + 20 log10(20) = 51.02
     dB re 1 uPa^2/Hz.

     Sources: Wenz, G. M. (1962), "Acoustic Ambient Noise in the Ocean:
     Spectra and Sources", JASA 34(12):1936-1956, DOI 10.1121/1.1909155;
     Knudsen, V. O., Alford, R. S. and Emling, J. W. (1948), "Underwater
     Ambient Noise", J. Marine Res. 7:410-429.  The rule is restated in
     Carey and Evans, "Ocean Ambient Noise: Measurement and Theory"
     (Springer 2011), ch. 1 p. 2.  Stated validity: 500 Hz to 5 kHz and
     2.5 to 40 knots; the wind speed is clamped to that range and the
     frequency to its 500 Hz floor, so the law is never extrapolated.

  2. Molecular thermal noise (Mellen 1952), the limit above about 50 kHz:

         NL_thermal(f) = -15 + 20 log10 f_kHz      dB re 1 uPa^2/Hz

     Source: APL-UW TR 9407 (1994), "APL-UW High-Frequency Ocean
     Environmental Acoustic Models Handbook", Eq. 47.

The total is the power sum of the two uncorrelated components,
10 log10(10^(NL_wind/10) + 10^(NL_thermal/10)) (APL-UW TR 9407 Eq. 46).

UNSOURCED, and marked here rather than presented as published:

  - Distant shipping below 500 Hz.  Wenz (1962) and Carey and Evans (2011)
    treat that band as site- and traffic-dependent, with no single fixed
    analytic parameterisation, so the rise below the 500 Hz corner is a
    stated approximation.
  - Shallow water.  The APL-UW handbook models the shallow-water increase
    as bottom multipath, which a single-level kernel cannot carry; the
    fixed bonus is a stated approximation.

Input:  [freqHz, windSpeedMs, shallow]
          freqHz       acoustic frequency, Hz
          windSpeedMs  wind speed at 10 m, m/s (the physical value; the
                       game's Beaufort sea state is mapped to it by the
                       driver, not here)
          shallow      true for the shallow-water case
Output: spectrum level in dB re 1 uPa^2/Hz

Pure and total.  The reference convention is dB re 1 uPa^2/Hz (ISO 18405).
*/

params [
    ["_freqHz", 1000, [0]],
    ["_windSpeedMs", 5, [0]],
    ["_shallow", false, [false]]
];

private _fKHz = (1 max _freqHz) / 1000;

// ─── 1. Wind / sea-surface component (Wenz "rule of fives") ───────────────
// 5 knots is the anchor wind speed; 1 knot = 0.514444 m/s.
private _ukn = ((_windSpeedMs / 0.514444) max 2.5) min 40;
private _fWindKHz = _fKHz max 0.5;
private _wind = 51.02 - (50 / 3) * ((log _fWindKHz) - (log (_ukn / 5)));

// ─── 2. Thermal component (Mellen 1952; APL-UW TR 9407 Eq. 47) ────────────
private _thermal = -15 + (20 * (log _fKHz));

// ─── Power sum of the two uncorrelated components (APL-UW Eq. 46) ─────────
private _total = 10 * (log ((10 ^ (_wind / 10)) + (10 ^ (_thermal / 10))));

// ─── UNSOURCED: distant shipping below the 500 Hz corner ──────────────────
private _shipping = 0;
if (_fKHz < 0.5) then {
    _shipping = 6 * ((log 0.5 - log _fKHz) / log 2);
};

// ─── UNSOURCED: shallow-water bonus ───────────────────────────────────────
private _shallowBonus = [0, 5] select _shallow;

_total + _shipping + _shallowBonus
