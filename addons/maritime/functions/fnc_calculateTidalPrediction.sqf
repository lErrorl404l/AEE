#include "..\script_component.hpp"
/*
Harmonic tide prediction, eight principal constituents
(M2 S2 N2 K2 K1 O1 P1 Q1):

  h(t) = sum_i  f_i * A_i * cos(V_i(t) + u_i - g_i)

A, g   amplitude and Greenwich phase lag of the world's tide gauge, from
       TICON-4 (fnc_getTideConstituents; data/maritime/tide_constituents.json):
       Altis/Stratis/Malden -> Samothraki, Tanoa -> Lautoka.  An unbound
       world uses the Doodson equilibrium ratios scaled by the M2 setting,
       with g = 0.  Livonia has no ocean tide.
V      Schureman (1958, US C&GS SP 98, Table 2) equilibrium argument at
       Greenwich, T = 15 UT + 180, with the mean longitudes of the moon s,
       sun h, lunar perigee p (Meeus 1998, 47.1-47.7 and 25.2).
f, u   nodal factors from the moon's node N (Pugh 1987, Table 4.3).
UT     from the game clock (local apparent solar time) by
       aee_lib_fnc_gameClockToUT, the same instant the sun and moon use.

The formula reproduces NOAA's official prediction for San Francisco
(9414290) to 4.4 cm RMS (tools/gen_tide_constituents.py gates on it).

Sets  aee_core_currentTideOffset_m    (m, about mean sea level)
Sets  aee_core_currentTideDescription
Returns the offset.
*/

params [];

private _table = [] call FUNC(getTideConstituents);
if (_table isEqualTo []) exitWith {
    missionNamespace setVariable [QEGVAR(core,currentTideOffset_m), 0];
    missionNamespace setVariable [QEGVAR(core,currentTideDescription), "None"];
    0
};
private _cons = _table select 0;

private _lon = ([] call EFUNC(lib,getWorldLocation)) select 2;

// [V, f, u] for each constituent at a local clock offset (hours).
private _fnc_args = {
    params ["_offsetH"];
    // The game clock is local apparent solar time (the engine's convention,
    // aee_lib_fnc_gameClockToUT), shared with the sun, moon and stars.  The
    // instant is [whole days since 2000-01-01, UT hours]: float32 cannot
    // hold a Julian Day, so every argument is a daily rate times the days.
    private _ut = [date, dayTime, _lon] call EFUNC(lib,gameClockToUT);
    private _utH = (_ut select 1) + _offsetH;
    private _days = (_ut select 0) - 0.5 + (_utH / 24);
    private _s = (218.3164477 + 13.17639647 * _days) mod 360;
    private _h = (280.46646 + 0.98564736 * _days) mod 360;
    private _p = (83.3532465 + 0.11140352 * _days) mod 360;
    private _N = (125.04452 - 0.05295376 * _days) mod 360;
    private _tau = 15 * _utH + 180;
    private _fM2 = 1.0004 - 0.0373 * cos _N + 0.0002 * cos (2 * _N);
    private _uM2 = -2.14 * sin _N;
    private _fK1 = 1.0060 + 0.1150 * cos _N - 0.0088 * cos (2 * _N) + 0.0006 * cos (3 * _N);
    private _uK1 = -8.86 * sin _N + 0.68 * sin (2 * _N) - 0.07 * sin (3 * _N);
    private _fO1 = 1.0089 + 0.1871 * cos _N - 0.0147 * cos (2 * _N) + 0.0014 * cos (3 * _N);
    private _uO1 = 10.80 * sin _N - 1.34 * sin (2 * _N) + 0.19 * sin (3 * _N);
    private _fK2 = 1.0241 + 0.2863 * cos _N + 0.0083 * cos (2 * _N) - 0.0015 * cos (3 * _N);
    private _uK2 = -17.74 * sin _N + 0.68 * sin (2 * _N) - 0.04 * sin (3 * _N);
    [
        [2 * _tau - 2 * _s + 2 * _h, _fM2, _uM2],
        [2 * _tau, 1, 0],
        [2 * _tau - 3 * _s + 2 * _h + _p, _fM2, _uM2],
        [2 * _tau + 2 * _h, _fK2, _uK2],
        [_tau + _h - 90, _fK1, _uK1],
        [_tau - 2 * _s + _h + 90, _fO1, _uO1],
        [_tau - _h + 90, 1, 0],
        [_tau - 3 * _s + _h + _p + 90, _fO1, _uO1]
    ]
};
private _fnc_height = {
    params ["_args"];
    private _sum = 0;
    {
        _x params ["_A", "_g"];
        (_args select _forEachIndex) params ["_V", "_f", "_u"];
        _sum = _sum + _f * _A * cos (_V + _u - _g);
    } forEach _cons;
    _sum
};

private _args = [0] call _fnc_args;
private _tideHeight = [_args] call _fnc_height;
private _slope = (([[0.25] call _fnc_args] call _fnc_height) - _tideHeight) / 0.25;

// ─── Description ─────────────────────────────────────────────────────────
// High/low within the top and bottom fifth of the semidiurnal swing.
private _band = 0.6 * (((_cons select 0) select 0) + ((_cons select 1) select 0));
private _tideDesc = if (_tideHeight > _band) then {
    "High"
} else {
    if (_tideHeight < -_band) then { "Low" } else { ["Falling", "Rising"] select (_slope > 0) }
};
// Spring/neap from the astronomical M2-S2 phase difference, twice the
// moon's elongation: +1 at new and full moon (spring), -1 at the quarters
// (neap).  A real port lags this by its age of tide (g_S2 - g_M2).
private _alignment = cos (((_args select 0) select 0) - ((_args select 1) select 0));
if (_alignment > 0.9) then { _tideDesc = _tideDesc + " (Spring Tide)"; };
if (_alignment < -0.9) then { _tideDesc = _tideDesc + " (Neap Tide)"; };

missionNamespace setVariable [QEGVAR(core,currentTideOffset_m), _tideHeight];
missionNamespace setVariable [QEGVAR(core,currentTideDescription), _tideDesc];
_tideHeight
