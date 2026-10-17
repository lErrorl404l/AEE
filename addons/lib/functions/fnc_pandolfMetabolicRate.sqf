#include "..\script_component.hpp"
/*
 * aee_lib_fnc_pandolfMetabolicRate
 *
 * Metabolic rate of standing or walking with a load.  Pure.
 *
 * Pandolf, Givoni & Goldman 1977 (J Appl Physiol 43:577):
 *   M = 1.5 W + 2.0 (W + L)(L / W)^2 + eta (W + L)(1.5 V^2 + 0.35 V G)   watts
 * W body mass kg, L load kg, V speed m/s, G grade %, eta the terrain factor.
 * Downhill (G < 0) the Santee et al. 2003 correction (Aviat Space Environ
 * Med 74:1171) is subtracted:
 *   CF = eta [G (W + L) V / 3.5 - (W + L)(G + 6)^2 / W + (25 - V^2)]
 * and the rate never falls below standing with the load.
 *
 * Arguments:
 *   0: body mass W, kg
 *   1: load L, kg
 *   2: speed V, m/s
 *   3: grade G, percent (rise / run x 100)
 *   4: terrain factor eta (fnc_pandolfTerrainFactor)
 * Return: metabolic rate, W
 */
params [["_w", 70, [0]], ["_l", 0, [0]], ["_v", 0, [0]], ["_g", 0, [0]], ["_eta", 1, [0]]];
private _body = _w max 1;
private _load = _l max 0;
private _speed = _v max 0;
private _wl = _body + _load;
private _standing = (1.5 * _body) + (2.0 * _wl * ((_load / _body) ^ 2));
private _m = _standing + (_eta * _wl * ((1.5 * _speed * _speed) + (0.35 * _speed * _g)));
if (_g < 0 && _speed > 0) then {
    _m = _m - (_eta * (((_g * _wl * _speed) / 3.5) - ((_wl * ((_g + 6) ^ 2)) / _body) + (25 - (_speed * _speed))));
};
_m max _standing
