#include "..\..\script_component.hpp"

/*
Byram (1959) fireline intensity and flame length.

  IB = H * w * R          fireline intensity, kW/m
  L  = 0.0775 * IB^0.46   flame length, m

H is the low heat of combustion of the fuel (kJ/kg), w the fuel consumed in
the flaming front (kg/m^2) and R the rate of spread (m/s).  The flame-length
relation is the Byram form as fitted by Alexander (1982) and restated by
Alexander & Cruz (2012).

Sources: Byram, G. M. (1959) "Combustion of Forest Fuels", in Forest Fire:
Control and Use (Davis), McGraw-Hill, pp. 61-89.  Alexander, M. E. (1982)
"Calculating and interpreting forest fire intensities", Canadian Journal of
Botany 60(4):349-357.  Alexander & Cruz (2012) "Interdependencies between
flame length, fireline intensity, and fuel consumption...", Int. J. Wildland
Fire 21(1):95-99.

Params:
  _hKjkg   low heat of combustion, kJ/kg (default 18700)
  _wKgm2   fuel consumed in the flaming front, kg/m^2
  _rosMs   rate of spread, m/s

Returns [fireline intensity kW/m, flame length m].
*/

params [
    ["_hKjkg", 18700, [0]],
    ["_wKgm2", 0.166, [0]],
    ["_rosMs", 0, [0]]
];

private _ib = _hKjkg * _wKgm2 * _rosMs;
private _flame = 0.0775 * _ib ^ 0.46;

[_ib, _flame]
