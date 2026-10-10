#include "..\..\script_component.hpp"

/*
Relative humidity after the surface modifier, the diurnal coupling and the
overcast-or-rain saturation constraint.

  RH = clamp100(RH_base + surfaceMod)
  RH = clamp100(RH * (1 + (T_ref - T_now) * k))
  RH = 100 when overcast > gate or rain > 0

RH couples to the diurnal temperature curve: at constant vapour content,
RH = 100 * e / e_sat(T), so RH falls as temperature rises.  T_ref is the
daily-mean temperature the driver tracks.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.  The driver
FUNC(updateHumidity) reads the state, updates the daily-mean temperature and
calls this kernel.

Arguments:
  0: Number - base relative humidity from the biome normals, %
  1: Number - surface modifier, %
  2: Number - daily-mean temperature, degrees Celsius
  3: Number - current temperature, degrees Celsius
  4: Number - overcast, 0 to 1
  5: Number - rain, 0 to 1

Returns:
  Number - relative humidity, % (integer, 0 to 100)
*/

params [
    ["_rhBase", 50, [0]],
    ["_surfaceMod", 0, [0]],
    ["_tRef", 15, [0]],
    ["_tNow", 15, [0]],
    ["_overcast", 0, [0]],
    ["_rain", 0, [0]]
];

private _diurnalCoef = 0.05;
private _overcastGate = 0.7;
private _saturation = 100;

private _rh = ((_rhBase + _surfaceMod) max 0) min _saturation;
_rh = _rh * (1 + (_tRef - _tNow) * _diurnalCoef);
_rh = (_rh max 0) min _saturation;
if (_overcast > _overcastGate || _rain > 0) then { _rh = _saturation; };

round _rh
