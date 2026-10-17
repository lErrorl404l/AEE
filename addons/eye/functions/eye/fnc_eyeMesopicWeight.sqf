#include "..\..\script_component.hpp"

/*
Mesopic adaptation coefficient m: the fraction of vision that cones carry.

The CIE 191:2010 recommended system for mesopic photometry (MES2).  From
the photopic luminance L_p and the scotopic-to-photopic ratio S/P of the
light (L_s = L_p S/P), the coefficient m and the mesopic luminance L_mes
are found by the fixed-point iteration CIE 191 recommends, from m0 = 0.5:

  L_mes,n = (m_{n-1} L_p + (1 - m_{n-1}) L_s V'(l0))
            / (m_{n-1} + (1 - m_{n-1}) V'(l0)),   V'(l0) = 683/1699
  m_n     = 0.7670 + 0.3334 log10(L_mes,n / 1 cd m-2)
  m = 1 when L_mes >= 5 cd/m2, m = 0 when L_mes <= 0.005 cd/m2.

The iteration converges for S/P below about 18 (Li et al., Opt. Express 26
(2018) 31351); real light sources lie far below.  m = 0 is pure scotopic
vision (rods), m = 1 pure photopic (cones).

Arguments:
  0: Number - photopic luminance L_p, cd/m2
  1: Number - S/P ratio of the light (daylight about 2.4)
  2: Number - L_mes below which m = 0, cd/m2 (CIE 191: 0.005)
  3: Number - L_mes above which m = 1, cd/m2 (CIE 191: 5)

Returns:
  Number - m in [0, 1].
*/

params [
    ["_lp", 0, [0]],
    ["_sp", 2.4, [0]],
    ["_lo", 0.005, [0]],
    ["_hi", 5, [0]]
];

if (_lp <= 0) exitWith { 0 };
private _v0 = 683 / 1699;
private _ls = _lp * (_sp max 0);
private _m = 0.5;
private _done = false;
for "_i" from 1 to 50 do {
    if (!_done) then {
        private _lmes = ((_m * _lp) + ((1 - _m) * _ls * _v0)) / (_m + ((1 - _m) * _v0));
        private _next = 0.7670 + (0.3334 * (log (_lmes max 1e-12)));
        if (_lmes >= _hi) then { _next = 1; };
        if (_lmes <= _lo) then { _next = 0; };
        _next = (_next max 0) min 1;
        if ((abs (_next - _m)) < 1e-7) then { _done = true; };
        _m = _next;
    };
};
_m
