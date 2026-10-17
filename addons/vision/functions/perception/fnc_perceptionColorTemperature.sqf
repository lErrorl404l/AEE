#include "..\..\script_component.hpp"

/*
Daylight chromaticity kernel (human-vision model, colour slice).

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  Returns the
CIE 1931 chromaticity and the correlated colour temperature of the light
falling on a horizontal surface, the white-balance source of the base grade.

Clear sky.  The spectra of the direct beam and of the diffuse sky are the
Bird & Riordan 1986 SPCTRAL2 model (validated against pvlib-python to machine
precision), integrated against the CIE 1931 2 deg colour-matching functions
offline (tools/gen_daylight.py -> fnc_daylightTable).  The table is
interpolated in apparent solar elevation, aerosol optical depth and surface
pressure.

Aerosol optical depth.  The published haze extinction (per km at 550 nm,
fnc_calculateHaze) less the Rayleigh scattering coefficient of air at 550 nm
(0.0116 per km at sea level, Bucholtz 1995, Appl. Opt. 34:2765) gives the
aerosol extinction; times the aerosol scale height 1.2 km (Elterman 1968,
AFCRL-68-0153) it is the optical depth at 550 nm, carried to 500 nm with the
SPCTRAL2 Angstrom exponent 1.14.

Cloud.  Kasten & Czeplak 1980 (Solar Energy 24:177): the global irradiance
falls as 1 - 0.75 N^3.4 and the diffuse fraction rises as kd0 + (1 - kd0) N^2
(their kd0 0.3 replaced by the clear-sky model's own diffuse fraction).
Cloud droplets are much larger than the wavelength and scatter neutrally, so
the cloud-diffuse light keeps the chromaticity of the clear global light; the
clear part of the dome (1 - N) keeps the blue sky.  Light adds in XYZ.

The table also carries the CIE 1951 scotopic integral, so the same mixing
gives the S/P ratio of the light.

Below 0.5 deg the table's horizon sky is held: twilight colour (the ozone
Chappuis band) lies outside SPCTRAL2.

CCT.  McCamy 1992 (Color Res. Appl. 17:142) below 3000 K; Hernandez-Andres,
Lee & Romero 1999 (Appl. Opt. 38:5703) from 3000 to 50 000 K.

Arguments:
  0: Number - apparent solar elevation, degrees
  1: Number - overcast fraction N, 0 to 1
  2: Number - haze extinction at 550 nm, per km (aee_core_currentHaze)
  3: Number - surface pressure, hPa

Returns:
  Array - [x, y, cct, sp]: CIE 1931 chromaticity, kelvin, and the S/P ratio
          (CIE 1951 scotopic over photopic luminance, the input of the CIE
          191:2010 mesopic system).
*/

params [
    ["_sunElevation", 0, [0]],
    ["_overcast", 0, [0]],
    ["_haze", 0.08, [0]],
    ["_pressure", 1013.25, [0]]
];

private _t = call FUNC(daylightTable);
private _elevs = _t get "elev";
private _aods = _t get "aod";
private _pres = _t get "pres";
private _rows = _t get "rows";
private _nE = count _elevs;
private _nA = count _aods;

private _n = (_overcast max 0) min 1;
private _aod550 = ((_haze - 0.0116) max 0) * 1.2;
private _aod = _aod550 * ((500 / 550) ^ -1.14);

// Bracket index and weight of a value in an ascending (or descending) grid.
private _fnc_bracket = {
    params ["_grid", "_v"];
    private _last = (count _grid) - 1;
    private _asc = (_grid select _last) > (_grid select 0);
    private _i = 0;
    for "_k" from 0 to (_last - 1) do {
        private _next = _grid select (_k + 1);
        if ([(_v >= _next), (_v <= _next)] select (!_asc)) then { _i = _k + 1; };
    };
    _i = _i min (_last - 1);
    private _a = _grid select _i;
    private _b = _grid select (_i + 1);
    [_i, (((_v - _a) / (_b - _a)) max 0) min 1]
};

([_elevs, _sunElevation max (_elevs select 0)] call _fnc_bracket) params ["_iE", "_wE"];
([_aods, _aod] call _fnc_bracket) params ["_iA", "_wA"];
([_pres, _pressure] call _fnc_bracket) params ["_iP", "_wP"];

// Trilinear interpolation of the six tristimulus values.
private _acc = [0, 0, 0, 0, 0, 0, 0, 0];
{
    _x params ["_dP", "_dA", "_dE"];
    private _w = ([1 - _wP, _wP] select _dP) * ([1 - _wA, _wA] select _dA) * ([1 - _wE, _wE] select _dE);
    private _row = _rows select ((((_iP + _dP) * _nA) + (_iA + _dA)) * _nE + (_iE + _dE));
    for "_k" from 0 to 7 do { _acc set [_k, (_acc select _k) + _w * (_row select _k)]; };
} forEach [[0,0,0],[0,0,1],[0,1,0],[0,1,1],[1,0,0],[1,0,1],[1,1,0],[1,1,1]];
_acc params ["_bX", "_bY", "_bZ", "_sX", "_sY", "_sZ", "_bS", "_sS"];
if (_sunElevation < (_elevs select 0)) then { _bX = 0; _bY = 0; _bZ = 0; _bS = 0; };

// Cloud (Kasten & Czeplak 1980), in units of the clear global luminance.
private _yClear = (_bY + _sY) max 1e-9;
private _kd0 = _sY / _yClear;
private _kd = _kd0 + (1 - _kd0) * (_n * _n);
private _g = 1 - 0.75 * (_n ^ 3.4);
private _beam = _g * (1 - _kd) / ((_bY max 1e-9) / _yClear);
private _sky = _g * _kd * (1 - _n) / ((_sY max 1e-9) / _yClear);
private _cloud = _g * _kd * _n;
private _X = 0;
private _Y = 0;
private _Z = 0;
if (_bY > 0) then {
    _X = _beam * _bX / _yClear;
    _Y = _beam * _bY / _yClear;
    _Z = _beam * _bZ / _yClear;
};
_X = _X + (_sky * _sX / _yClear) + (_cloud * (_bX + _sX) / _yClear);
_Y = _Y + (_sky * _sY / _yClear) + (_cloud * (_bY + _sY) / _yClear);
_Z = _Z + (_sky * _sZ / _yClear) + (_cloud * (_bZ + _sZ) / _yClear);
private _S = (_sky * _sS / _yClear) + (_cloud * (_bS + _sS) / _yClear);
if (_bY > 0) then { _S = _S + (_beam * _bS / _yClear); };
private _sp = _S / (_Y max 1e-9);

private _sum = (_X + _Y + _Z) max 1e-9;
private _cx = _X / _sum;
private _cy = _Y / _sum;

// CCT: McCamy 1992 below 3000 K, Hernandez-Andres et al. 1999 above.
private _nM = (_cx - 0.3320) / (0.1858 - _cy);
private _cct = (449 * (_nM ^ 3)) + (3525 * (_nM ^ 2)) + (6823.3 * _nM) + 5520.33;
if (_cct >= 3000) then {
    private _nH = (_cx - 0.3366) / (_cy - 0.1735);
    _cct = -949.86315 + (6253.80338 * exp (-_nH / 0.92159)) + (28.70599 * exp (-_nH / 0.20039)) + (0.00004 * exp (-_nH / 0.07125));
};
[_cx, _cy, (_cct max 1000) min 50000, _sp]
