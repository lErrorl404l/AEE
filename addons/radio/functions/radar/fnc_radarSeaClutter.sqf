#include "..\..\script_component.hpp"
/*
Sea-surface clutter reflectivity - the NRL empirical model.

  sigma0(dB) = CC1
             + CC2 * log10(sin psi)
             + (27.5 + CC3 * psi) * log10(f) / (1 + 0.95 * psi)
             + CC4 * (SS + 1)^(1 / (2 + 0.085 * psi + 0.033 * SS))
             + CC5 * psi^2

  psi  grazing angle, degrees
  f    frequency, GHz
  SS   sea state (Douglas)

  Polarisation coefficients:
             CC1       CC2      CC3     CC4      CC5
    VV       -50.796   25.93    0.7093  21.588   0.00211
    HH       -73.0     20.781   7.351   25.65    0.0054

Source: Gregers-Hansen & Mital, "An Improved Empirical Model for Radar
Sea Clutter Reflectivity", NRL, 2012 (DTIC ADA559494).  Verified vector:
VV, 10 GHz, SS3, 1 deg -> -41.2 dB.

Pure: reads no engine state, writes none.

Arguments:
  0: Number - grazing angle psi, degrees
  1: Number - frequency f, GHz
  2: Number - sea state SS
  3: String - polarisation, "VV" or "HH"

Returns:
  Number - clutter reflectivity sigma0, dB
*/
params [
    ["_psi", 0, [0]],
    ["_freqGhz", 0, [0]],
    ["_seaState", 0, [0]],
    ["_polarisation", "VV", [""]]
];

private _coeff = if (_polarisation == "HH") then {
    [-73.0, 20.781, 7.351, 25.65, 0.0054]
} else {
    [-50.796, 25.93, 0.7093, 21.588, 0.00211]
};
private _cc1 = _coeff select 0;
private _cc2 = _coeff select 1;
private _cc3 = _coeff select 2;
private _cc4 = _coeff select 3;
private _cc5 = _coeff select 4;

private _sinPsi = sin _psi;
private _term2 = _cc2 * (log (_sinPsi max 1e-9));
private _term3 = (27.5 + _cc3 * _psi) * (log _freqGhz) / (1 + 0.95 * _psi);
private _term4 = _cc4 * ((_seaState + 1) ^ (1 / (2 + 0.085 * _psi + 0.033 * _seaState)));
private _term5 = _cc5 * (_psi ^ 2);

_cc1 + _term2 + _term3 + _term4 + _term5
