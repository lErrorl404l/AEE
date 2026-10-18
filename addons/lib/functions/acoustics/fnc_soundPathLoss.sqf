#include "..\..\script_component.hpp"
/*
Outdoor sound path loss, ISO 9613-2:1996 (acoustic propagation).  Pure.

The A-weighted loss from 1 m to the receiver, with the attenuation terms at
500 Hz (ISO 9613-2 clause 1, note 1, for A-weighted sources):
  A = A_div + A_atm + A_gr + A_fol
  A_div = 20 log10(d / 1 m)                  geometrical divergence (eq. 7,
                                             referred to the 1 m level)
  A_atm = alpha d                            alpha from ISO 9613-1 at 500 Hz
                                             (aee_lib_fnc_atmosphericAbsorption)
  A_gr  = G (4.8 - (2 h_m / d)(17 + 300 / d)), >= 0     (eq. 10; G the
                                             porous fraction of the ground,
                                             clause 7.3.1: 0 hard - paving,
                                             water, ice - 1 porous - grass,
                                             farmland, snow, forest floor)
  A_fol = dense foliage, Table A.1 at 500 Hz: 1 dB for 10-20 m of foliage,
          0.05 dB/m for 20-200 m, held at 200 m beyond.
The method is for downwind or moderate-inversion propagation, the
favourable condition (clause 5); upwind refractive shadow zones are not
modelled, nor is the reflection gain over hard ground.

Arguments:
  0: Number - distance, m
  1: Number - source height above the ground, m
  2: Number - receiver height above the ground, m
  3: Number - ISO 9613-1 absorption at 500 Hz, dB/m
  4: Number - porous ground fraction G, 0..1
  5: Number - path length through dense foliage, m
Returns:
  Number - path loss, dB
*/
params [
    ["_d", 1, [0]], ["_hs", 1.5, [0]], ["_hr", 1.5, [0]],
    ["_alpha", 0.0019, [0]], ["_g", 1, [0]], ["_foliageM", 0, [0]]
];
private _dist = _d max 1;
private _hm = ((_hs max 0) + (_hr max 0)) / 2;
private _aGr = ((4.8 - ((2 * _hm / _dist) * (17 + (300 / _dist)))) max 0) * ((_g max 0) min 1);
private _df = (_foliageM max 0) min 200;
private _aFol = 0;
if (_df >= 10) then { _aFol = [1, 0.05 * _df] select (_df >= 20); };
(20 * (log _dist)) + ((_alpha max 0) * _dist) + _aGr + _aFol
