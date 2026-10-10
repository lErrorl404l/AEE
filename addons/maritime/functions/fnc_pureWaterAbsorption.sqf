#include "..\script_component.hpp"
/*
Pure-water absorption coefficient a_w at a visible wavelength (issue #14).

Source: Pope and Fry (1997), Applied Optics 36:8710, "Absorption spectrum
(380-700 nm) of pure water. II. Integrating cavity measurements".  The
values come from the omlc.org digitisation of that paper.  The minimum,
0.0044 m^-1, is at 418 nm.  The anchors used here are (nm, m^-1):

    418  0.0044   minimum
    475  0.0114
    530  0.0434
    600  0.222
    660  0.410
    700  0.650

Correction: issue #14 lists 0.0145 at 475 nm.  That value belongs near
490 nm.  The digitisation gives 0.0114 at 475 nm and 0.0434 at 530 nm.  It
also gives 0.410 at 660 nm, not 0.401.  The corrected values are used here.

The value between two anchors is linearly interpolated.  Outside the range
the nearest anchor holds.  The linear interpolation is a stated
approximation to the smooth measured curve.

Input:  [_nm] - wavelength in nanometres
Output: a_w in m^-1
*/

params [["_nm", 475, [0]]];

private _anchors = [
    [418, 0.0044], [475, 0.0114], [530, 0.0434],
    [600, 0.222], [660, 0.410], [700, 0.650]
];

private _n = count _anchors;
private _lo0 = _anchors select 0;
private _hiN = _anchors select (_n - 1);
if (_nm <= (_lo0 select 0)) exitWith { _lo0 select 1 };
if (_nm >= (_hiN select 0)) exitWith { _hiN select 1 };

private _aw = 0;
for "_i" from 0 to (_n - 2) do {
    private _lo = _anchors select _i;
    private _hi = _anchors select (_i + 1);
    private _loNm = _lo select 0;
    private _hiNm = _hi select 0;
    if (_nm >= _loNm && _nm <= _hiNm) then {
        private _frac = (_nm - _loNm) / (_hiNm - _loNm);
        _aw = (_lo select 1) + _frac * ((_hi select 1) - (_lo select 1));
    };
};

_aw
