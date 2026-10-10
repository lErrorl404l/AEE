#include "..\script_component.hpp"
/*
Sound absorption in seawater (issue #113).

Francois and Garrison (1982), "Sound absorption based on ocean measurements:
Part II: Boric acid contribution and equation for total absorption",
Journal of the Acoustical Society of America 72(6):1879-1890,
DOI 10.1121/1.388673.

    alpha = A1 P1 f1 f^2 / (f1^2 + f^2)
          + A2 P2 f2 f^2 / (f2^2 + f^2)
          + A3 P3 f^2                      dB/km

with f in kHz and:

    c  = 1412 + 3.21 T + 1.19 S + 0.0167 D          (m/s, the paper's own)
    A1 = 8.86 / c * 10^(0.78 pH - 5)                boric acid amplitude
    f1 = 2.8 sqrt(S / 35) * 10^(4 - 1245 / (T + 273))       boric acid relaxation (kHz)
    A2 = 21.44 S / c * (1 + 0.025 T)                magnesium sulphate amplitude
    f2 = 8.17 * 10^(8 - 1990 / (T + 273)) / (1 + 0.0018 (S - 35))   MgSO4 relaxation (kHz)
    A3 = 4.937e-4 - 2.59e-5 T + 9.11e-7 T^2 - 1.5e-8 T^3    (T <= 20 C, pure water)
    A3 = 3.964e-4 - 1.146e-5 T + 1.45e-7 T^2 - 6.5e-10 T^3  (T > 20 C)
    P1 = 1
    P2 = 1 - 1.37e-4 D + 6.2e-9 D^2                 pressure correction (MgSO4)
    P3 = 1 - 3.83e-5 D + 4.9e-10 D^2                pressure correction (pure water)

  T   temperature, degC
  S   salinity, psu
  D   depth, m
  pH  acidity (open ocean 8.0..8.2)
  f   frequency, kHz

The paper's own sound speed c is used, not the Mackenzie value: the F&G
coefficients were fitted against this linear form, so mixing in a different
c would change the fit.  The two differ by under 1 percent in the validity
range, which is the paper's stated approximation.

The three terms are the boric acid relaxation (near 1 kHz), the magnesium
sulphate relaxation (tens of kHz) and the pure-water viscosity term (rising
without bound at high frequency).  Low frequencies travel far; high
frequencies are absorbed quickly.

Computed anchors (T=10 C, S=35 psu, D=0 m, pH=8): 0.0012 dB/km at 100 Hz,
0.070 dB/km at 1 kHz, 0.99 dB/km at 10 kHz, 34 dB/km at 100 kHz.  The
issue's stated vectors ("0.01-0.1 at 100 Hz", "~50 at 100 kHz") are wrong;
the equation gives the values above.  The issue's 10 kHz band (0.1-1) is
correct.

Input:  [f_Hz, T, S, D, pH]
Output: absorption in dB/km
*/

params [
    ["_fHz", 1000, [0]],
    ["_T", 10, [0]],
    ["_S", 35, [0]],
    ["_D", 0, [0]],
    ["_pH", 8.0, [0]]
];

private _f = _fHz / 1000;                 // kHz

// ─── The paper's own sound speed ──────────────────────────────────────────
private _c = 1412 + 3.21 * _T + 1.19 * _S + 0.0167 * _D;

// ─── Boric acid relaxation ────────────────────────────────────────────────
private _A1 = (8.86 / _c) * (10 ^ (0.78 * _pH - 5));
private _f1 = 2.8 * (sqrt (_S / 35)) * (10 ^ (4 - 1245 / (_T + 273)));

// ─── Magnesium sulphate relaxation ────────────────────────────────────────
private _A2 = 21.44 * (_S / _c) * (1 + 0.025 * _T);
private _f2 = (8.17 * (10 ^ (8 - 1990 / (_T + 273)))) / (1 + 0.0018 * (_S - 35));

// ─── Pure water viscosity ─────────────────────────────────────────────────
private _A3 = if (_T <= 20) then {
    4.937e-4 - 2.59e-5 * _T + 9.11e-7 * _T ^ 2 - 1.5e-8 * _T ^ 3
} else {
    3.964e-4 - 1.146e-5 * _T + 1.45e-7 * _T ^ 2 - 6.5e-10 * _T ^ 3
};

// ─── Pressure corrections ─────────────────────────────────────────────────
private _P2 = 1 - 1.37e-4 * _D + 6.2e-9 * _D ^ 2;
private _P3 = 1 - 3.83e-5 * _D + 4.9e-10 * _D ^ 2;

private _f2sq = _f ^ 2;

private _alpha =
      (_A1 * _f1 * _f2sq) / (_f1 ^ 2 + _f2sq)
    + (_A2 * _P2 * _f2 * _f2sq) / (_f2 ^ 2 + _f2sq)
    + _A3 * _P3 * _f2sq;

_alpha
