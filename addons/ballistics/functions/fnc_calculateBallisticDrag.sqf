#include "..\script_component.hpp"
/*
Real ballistic drag for any projectile (issue #167).

Computes the drag retardation from a ballistic coefficient or a drag
table, matching the engine's quadratic drag form (a = airFriction * v^2)
AND the real drag law:

  retard = 0.00068418 * (Cd(Mach) / BC) * v^2 * rhoRel

The constant 0.00068418 = 0.5 * rho0 * pi * (0.0254)^2 / (4 * 0.453592)
at rho0 = 1.225 kg/m3, which converts the lb/in^2 coefficient
convention to SI.

The Mach number uses the LOCAL speed of sound, not a fixed 340 m/s:

  a = 20.05 * sqrt(T + 273.15)         (m/s, T in Celsius)

At -40 C that is 300 m/s and at +50 C it is 359 m/s, so a fixed value
would misplace the transonic band and with it the whole drag curve.

Every standard drag function the database holds is available by name:
G1, G2, G5, G6, G7, G8, GA, GB, GI, GS, LW2, RA4, RWS1943 and SCHAPIRO.
The tables live in fnc_getDragTables, generated from the verified source.
A projectile may also carry a direct Cd(Mach) table of its own, which is
what a measured custom drag model is.

Arguments:
  0: bc (NUMBER, the ballistic coefficient in the chosen standard)
  1: velocity (NUMBER, the current velocity, m/s)
  2: dragModel (STRING or NUMBER, default "G1"; 7 and "G7" are the same)
  3: rhoRel (NUMBER, relative air density, default 1.0)
  4: airTempC (NUMBER, air temperature, default 15)

Returns the drag retardation (m/s^2, positive = deceleration).
*/
params [
    ["_bc", 0, [0]],
    ["_velocity", 0, [0]],
    ["_dragModel", "G1", ["", 0]],
    ["_rhoRel", 1.0, [0]],
    ["_airTempC", 15, [0]]
];
if (_bc <= 0) exitWith { 0.0 };
if (_velocity <= 0) exitWith { 0.0 };

private _model = if (_dragModel isEqualType "") then {
    toUpper _dragModel
} else {
    format ["G%1", round _dragModel]
};

private _table = (call FUNC(getDragTables)) getOrDefault [_model, []];
if (_table isEqualTo []) exitWith { 0.0 };

// The local speed of sound, then the Mach number at that temperature.
private _sound = 20.05 * sqrt (_airTempC + 273.15);
private _mach = _velocity / _sound;

// Table lookup with linear interpolation between the Mach breakpoints.
private _cd = _table select 0 select 1;
private _n = count _table;
if (_mach <= (_table select 0 select 0)) then {
    _cd = _table select 0 select 1;
} else {
    if (_mach >= (_table select (_n - 1) select 0)) then {
        _cd = _table select (_n - 1) select 1;
    } else {
        for "_i" from 0 to (_n - 2) do {
            private _m0 = _table select _i select 0;
            private _m1 = _table select (_i + 1) select 0;
            if (_mach >= _m0 && _mach <= _m1) exitWith {
                private _c0 = _table select _i select 1;
                private _c1 = _table select (_i + 1) select 1;
                _cd = linearConversion [_m0, _m1, _mach, _c0, _c1, true];
            };
        };
    };
};

0.00068418 * (_cd / _bc) * (_velocity ^ 2) * _rhoRel
