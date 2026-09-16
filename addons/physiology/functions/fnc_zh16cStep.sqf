#include "..\script_component.hpp"
/*
ZH-L16C decompression model (issue #118).

Implements the Bühlmann ZH-L16C 16-compartment dissolved-gas model:

  - 16 tissue compartments, each with N2 and He half-times and a/b
    M-value coefficients (the dive-computer variant; compartment 1 is
    the 4-minute fast tissue).
  - Loading (Schreiner):  P = P0 + (Pi - P0) * (1 - e^(-t*ln2/tHalf))
    where Pi is the inspired gas pressure = fGas * (P_amb - P_H2O).
  - Water vapour pressure: 0.0627 bar (Bühlmann value, Rq = 1.0,
    confirmed against Subsurface core/deco.cpp WV_PRESSURE).
  - Ceiling:  P_amb_allowed = (P_tissue - a*GF) / (1 - GF*(1 - 1/b))
    GF = 1 reduces to the pure Bühlmann ceiling b*(P_tissue - a).
  - Mixed-gas a/b: weighted average by tissue gas fraction (N2 vs He).

Constants from the published ZH-L16C table (Bühlmann "Tauchmedizin"
1993, reproduced in Baker 1998/2000 and the SAETT FAQ which labels the
dive-computer "a" column).  NOT the ZHL-16b variant (5-minute first
compartment, used by Subsurface): 16C keeps compartment 1 at 4 min.

Input:  [_depthM, _fN2, _fHe, _tissues]  - depth, gas mix, 16x2 state
Output: [newTissues, ceilingM]  - updated state and the controlling
        ceiling depth (metres, positive down)
*/

params [["_depthM", 0, [0]], ["_fN2", 0.79, [0]], ["_fHe", 0, [0]], ["_tissues", [], [[]]], ["_gf", 1, [0]]];

// Fresh state = N2 equilibrium at the surface breathing air:
// PN2 = (1 - 0.0627) * 0.79 = 0.74047 bar in every compartment.  A diver
// descending from the surface already carries this preload, which is the
// baseline the published NDL tables use.
if (_tissues isEqualTo []) then {
    private _baseline = 0.74047;
    private _fresh = [];
    for "_i" from 0 to 15 do { _fresh pushBack _baseline; };
    for "_i" from 0 to 15 do { _fresh pushBack 0; };
    _tissues = _fresh;
};

// ─── ZH-L16C constants ────────────────────────────────────────────────────
private _tHalfN2 = [4.0, 8.0, 12.5, 18.5, 27.0, 38.3, 54.3, 77.0,
                    109.0, 146.0, 187.0, 239.0, 305.0, 390.0, 498.0, 635.0];
private _tHalfHe = [1.51, 3.02, 4.72, 6.99, 10.21, 14.48, 20.53, 29.11,
                    41.20, 55.19, 70.69, 90.34, 115.29, 147.42, 188.24, 240.03];
private _aN2 = [1.2599, 1.0, 0.8618, 0.7562, 0.62, 0.5043, 0.441, 0.4,
                0.375, 0.35, 0.3295, 0.3065, 0.2835, 0.261, 0.248, 0.2327];
private _bN2 = [0.5050, 0.6514, 0.7222, 0.7825, 0.8126, 0.8434, 0.8693, 0.8910,
                0.9092, 0.9222, 0.9319, 0.9403, 0.9477, 0.9544, 0.9602, 0.9653];
private _aHe = [1.7424, 1.383, 1.1919, 1.0458, 0.922, 0.8205, 0.7305, 0.6502,
                0.595, 0.5545, 0.5333, 0.5189, 0.5181, 0.5176, 0.5172, 0.5119];
private _bHe = [0.4245, 0.5747, 0.6527, 0.7223, 0.7582, 0.7957, 0.8279, 0.8553,
                0.8757, 0.8903, 0.8997, 0.9073, 0.9122, 0.9171, 0.9217, 0.9267];

// ─── Ambient and inspired pressures ───────────────────────────────────────
private _pH2O = 0.0627;                    // water vapour, Bühlmann value
private _pAmb = (_depthM / 10) + 1;        // 10 m per bar, +1 surface
private _pInspiredN2 = (_pAmb - _pH2O) * _fN2;
private _pInspiredHe = (_pAmb - _pH2O) * _fHe;

// ─── Tissue loading (one-step exponential per compartment) ───────────────
// The half-times are in MINUTES; the SQF integrates at 1-second cadence,
// so the time constant in the exponential is 1/60 minutes.
private _dtMin = 1 / 60;
private _newN2 = [];
private _newHe = [];
for "_i" from 0 to 15 do {
    private _pn2 = _tissues select _i;
    private _phe = _tissues select (16 + _i);
    private _kN2 = ln 2 / (_tHalfN2 select _i);
    private _kHe = ln 2 / (_tHalfHe select _i);
    _pn2 = _pInspiredN2 + (_pn2 - _pInspiredN2) * exp (-_kN2 * _dtMin);  // 1 s step
    _phe = _pInspiredHe + (_phe - _pInspiredHe) * exp (-_kHe * _dtMin);
    _newN2 pushBack _pn2;
    _newHe pushBack _phe;
};
private _newTissues = _newN2 + _newHe;

// ─── Ceiling (controlling compartment, GF 1.0 = pure Bühlmann) ───────────
// Gradient factor: P_amb_allowed = (P_tissue - GF*a) / (1 - GF*(1 - 1/b)).
// GF = 1 reduces to b*(P_tissue - a).  Lower GF = more conservative.
private _gfC = _gf max 0.5 min 1.0;
private _ceilingBar = 0;
for "_i" from 0 to 15 do {
    private _pn2 = _newTissues select _i;
    private _phe = _newTissues select (16 + _i);
    // Mixed-gas a/b by tissue gas fraction
    private _total = _pn2 + _phe;
    private _fN2t = if (_total > 0) then { _pn2 / _total } else { 0 };
    private _fHet = if (_total > 0) then { _phe / _total } else { 0 };
    private _a = ((_aN2 select _i) * _fN2t) + ((_aHe select _i) * _fHet);
    private _b = ((_bN2 select _i) * _fN2t) + ((_bHe select _i) * _fHet);
    private _allow = (_total - _gfC * _a) / (1 - _gfC * (1 - 1 / _b));
    _ceilingBar = _ceilingBar max _allow;
};
private _ceilingM = ((_ceilingBar - 1) * 10) max 0;

[_newTissues, _ceilingM]
