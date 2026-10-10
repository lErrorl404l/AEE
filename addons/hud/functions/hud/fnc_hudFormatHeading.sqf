#include "..\..\script_component.hpp"
/*
 * ECOTI HUD compass heading formatter (pure kernel).
 *
 * Turns a camera bearing in degrees into the two HUD strings: the cardinal
 * letter and the zero-padded three-digit bearing.  The engine caller passes
 * the live camera direction; this kernel only formats.
 *
 * Ported from workshop 3759527903 FPANO_ECOTI/scripts/FPANO_fnc_hud.sqf
 * (the cardinal switch and the degrees padding).
 *
 * Params:
 *   0: _dir (SCALAR) - bearing in degrees, any value; wraps into 0..359.
 *
 * Returns: ARRAY [cardinal (STRING), degrees (STRING, 3 characters)].
 */
params [["_dir", 0, [0]]];

_dir = _dir mod 360;
if (_dir < 0) then { _dir = _dir + 360; };
_dir = round _dir;
if (_dir >= 360) then { _dir = 0; };

// 45-degree sectors, north spanning 338..22 (source thresholds).
private _cardinal = "N";
if (_dir >= 23) then {
    _cardinal = "NE";
    if (_dir >= 68) then {
        _cardinal = "E";
        if (_dir >= 113) then {
            _cardinal = "SE";
            if (_dir >= 158) then {
                _cardinal = "S";
                if (_dir >= 203) then {
                    _cardinal = "SW";
                    if (_dir >= 248) then {
                        _cardinal = "W";
                        if (_dir >= 293) then {
                            _cardinal = "NW";
                            if (_dir >= 338) then { _cardinal = "N"; };
                        };
                    };
                };
            };
        };
    };
};

private _degrees = str _dir;
if (_dir < 10) then {
    _degrees = "00" + _degrees;
} else {
    if (_dir < 100) then {
        _degrees = "0" + _degrees;
    };
};

[_cardinal, _degrees]
