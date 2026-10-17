#include "..\script_component.hpp"
/*
GENERATED FILE. Do not edit by hand.
Regenerate with: python3 tools/gen_twilight.py

Clear-sky horizontal illuminance of twilight (the scattered light of a sun
below the horizon), by true solar altitude, interpolated in log10 lux from
the table of P. Schlyter, "Radiometry and photometry in astronomy", section
10 (held: data/astronomy/sources/schlyter_radfaq.html): 759 lx at 0 deg,
3.41 lx at -6, 0.00806 lx at -12, 0.000645 lx at -18.  Below -18 deg
(astronomical night) the sun contributes nothing.

Arguments: 0: solar altitude, deg
Return: illuminance, lux (0 above the horizon: daylight is not twilight)
Public: No
*/
params [["_alt", -90, [0]]];
if (_alt > 0 || _alt < -18) exitWith { 0 };
private _a = [0, -0.5, -1, -1.5, -2, -2.5, -3, -3.5, -4, -4.5, -5, -5.5, -6, -6.5, -7, -7.5, -8, -8.5, -9, -9.5, -10, -10.5, -11, -11.5, -12, -12.5, -13, -13.5, -14, -14.5, -15, -15.5, -16, -16.5, -17, -17.5, -18];
private _l = [2.88, 2.75, 2.61, 2.45, 2.28, 2.09, 1.9, 1.69, 1.48, 1.25, 1.02, 0.78, 0.53, 0.29, 0.04, -0.21, -0.46, -0.7, -0.93, -1.16, -1.38, -1.58, -1.77, -1.94, -2.09, -2.22, -2.34, -2.44, -2.54, -2.62, -2.69, -2.77, -2.84, -2.92, -3, -3.09, -3.19];
private _i = 0;
for "_k" from 0 to ((count _a) - 2) do {
    if (_alt <= (_a select _k)) then { _i = _k; };
};
_i = _i min ((count _a) - 2);
private _w = ((_a select _i) - _alt) / ((_a select _i) - (_a select (_i + 1)));
10 ^ (((_l select _i) * (1 - _w)) + ((_l select (_i + 1)) * _w))
