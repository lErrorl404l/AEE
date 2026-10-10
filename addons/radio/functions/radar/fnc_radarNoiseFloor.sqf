#include "..\..\script_component.hpp"
/*
Minimum detectable power - the receiver noise floor times the required SNR.

  P_min = k T_0 B F_n SNR_min

  k       Boltzmann constant, 1.38e-23 J/K
  T_0     reference temperature, 290 K
  B       receiver bandwidth, Hz
  F_n     noise figure, linear
  SNR_min minimum signal-to-noise ratio for detection, linear

Source: Skolnik, "Radar Handbook", 3rd ed., ch. 1.  k and T_0 are the
standard values (k = 1.38e-23, T_0 = 290 K).  SNR_min ~ 13 dB for
Pd = 0.5, Pfa = 1e-6 (Marcum single-pulse detection) is the issue's
stated anchor; the caller passes the linear ratio.

Pure: reads no engine state, writes none.

Arguments:
  0: Number - bandwidth B, Hz
  1: Number - noise figure F_n, linear
  2: Number - required SNR, linear

Returns:
  Number - minimum detectable power P_min, W
*/
params [
    ["_bandwidth", 1, [0]],
    ["_noiseFigure", 1, [0]],
    ["_snrMin", 1, [0]]
];

private _k = 1.38e-23;
private _t0 = 290;

_k * _t0 * _bandwidth * _noiseFigure * _snrMin
