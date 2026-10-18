#include "..\script_component.hpp"
/*
Ambient-noise spectrum level in the sea (issue #113).

The four-component empirical model of Coates (1990), "Underwater Acoustic
Systems" (Wiley), as stated by Stojanovic (2007), "On the relationship
between capacity and distance in an underwater acoustic communication
channel", ACM SIGMOBILE MC2R 11(4):34, eq. 6 (f in kHz, dB re 1 uPa^2/Hz):

  turbulence  10 log Nt  = 17 - 30 log f
  shipping    10 log Ns  = 40 + 20 (s - 0.5) + 26 log f - 60 log(f + 0.03)
  wind/waves  10 log Nw  = 50 + 7.5 w^1/2 + 20 log f - 40 log(f + 0.4)
  thermal     10 log Nth = -15 + 20 log f

s the distant-shipping activity 0..1, w the wind speed in m/s.  The
components are uncorrelated, so the total is their power sum (APL-UW TR
9407, eq. 46).  Turbulence governs below ~10 Hz, shipping 10-100 Hz, the
sea surface 100 Hz-100 kHz and molecular thermal noise above.

Input:  [freqHz, windSpeedMs, shippingActivity]
Output: spectrum level, dB re 1 uPa^2/Hz (ISO 18405 convention).
Pure and total.
*/

params [
    ["_freqHz", 1000, [0]],
    ["_windSpeedMs", 5, [0]],
    ["_shipping", 0.5, [0]]
];

private _f = (1 max _freqHz) / 1000;
private _lf = log _f;
private _s = (_shipping max 0) min 1;
private _w = _windSpeedMs max 0;

private _nt = 17 - (30 * _lf);
private _ns = 40 + (20 * (_s - 0.5)) + (26 * _lf) - (60 * (log (_f + 0.03)));
private _nw = 50 + (7.5 * (sqrt _w)) + (20 * _lf) - (40 * (log (_f + 0.4)));
private _nth = -15 + (20 * _lf);

10 * (log ((10 ^ (_nt / 10)) + (10 ^ (_ns / 10)) + (10 ^ (_nw / 10)) + (10 ^ (_nth / 10))))
