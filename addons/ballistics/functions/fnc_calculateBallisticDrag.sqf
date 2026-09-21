#include "..\script_component.hpp"
/*
Real ballistic drag (issue #167).

Computes the G1/G7 drag retardation for a round from its ballistic
coefficient, matching the engine's quadratic drag form
(a = airFriction * v^2) AND the real drag law:

  retard = 0.00068418 * (Cd_G1(Mach) / BC) * v^2        (G1)
  retard = 0.00068418 * (Cd_G7(Mach) / BC) * v^2        (G7)

The constant 0.00068418 = 0.5 * rho * pi * (0.0254)^2 / (4 * 0.453592)
at rho = 1.225 kg/m3 (ICAO standard sea level), converting the G1
lb/in^2 BC convention to SI.  This is the SAME kernel ACE3 uses (their
drag.rs calculate_retard), verified against the engine's airFriction:
a 5.56 M855 (G1 0.307) drops to airFriction ~0.00126, a .50 BMG
(G1 1.05) to ~0.000374 (the bridge research, cross-checked against
ACE3's shipped config values).

The Cd(Mach) table is the modern BRL G1/G7 drag function (the standard
used by Applied Ballistics, JBM, pyballistics, and ACE3):
  transonic peak ~0.66 at Mach 1.3-1.4 (~3.2x the subsonic value).
This is the piece the vanilla engine lacks: a single constant
airFriction cannot model the real transonic drag rise, so a round
crossing Mach 1 in flight (5.56 at ~600 m, .50 BMG at ~900 m) gets the
real drag spike instead of a flat coefficient.

Arguments:
  0: bc (NUMBER, the ballistic coefficient in the G1 or G7 standard)
  1: velocity (NUMBER, the round's current velocity, m/s)
  2: dragModel (NUMBER, 1 = G1, 7 = G7; default 1)
  3: airDensity (NUMBER, the relative air density 0..1.2, default 1.0)

Returns the drag retardation (m/s^2, positive = deceleration).
*/
params ["_bc", "_velocity", ["_dragModel", 1, [0]], ["_rhoRel", 1.0, [0]]];
if (_bc <= 0) exitWith { 0.0 };
if (_velocity <= 0) exitWith { 0.0 };

// Mach number at the current velocity (sea-level speed of sound 340 m/s).
private _mach = _velocity / 340;

// The modern BRL G1 drag coefficient table (Mach -> Cd).  The
// transonic rise peaks ~0.66 at Mach 1.3-1.4.  Values from the
// standard G1 reference (the 1920s G1 projectile, tabulated by the
// BRL and used by Applied Ballistics / JBM / pyballistic).
// (Mach, Cd_G1)
private _g1 = [
    [0.0, 0.2032], [0.5, 0.2032], [0.8, 0.2285], [0.9, 0.3013],
    [1.0, 0.4805], [1.1, 0.5951], [1.2, 0.6550], [1.3, 0.6600],
    [1.4, 0.6460], [1.5, 0.6573], [1.6, 0.6590], [1.8, 0.6315],
    [2.0, 0.5934], [2.25, 0.5650], [2.5, 0.5397], [3.0, 0.5035],
    [3.5, 0.4830], [4.0, 0.4660], [5.0, 0.4470]
];

// The modern BRL G7 drag coefficient table (the VLD/boat-tail rounds:
// .338 LM, .300 WM, Mk262, M118LR).  The G7 Cd is lower than G1 in the
// supersonic regime (the boat-tail's advantage).
private _g7 = [
    [0.0, 0.1198], [0.5, 0.1198], [0.8, 0.1366], [0.9, 0.1838],
    [1.0, 0.3003], [1.1, 0.3767], [1.2, 0.4130], [1.3, 0.4140],
    [1.4, 0.3990], [1.5, 0.4100], [1.6, 0.4118], [1.8, 0.3991],
    [2.0, 0.3779], [2.25, 0.3635], [2.5, 0.3530], [3.0, 0.3390],
    [3.5, 0.3330], [4.0, 0.3300], [5.0, 0.3260]
];

private _table = [_g1, _g7] select (_dragModel == 7);

// Table lookup with linear interpolation between the Mach breakpoints.
private _cd = 0.2032;
for "_i" from 0 to (count _table - 2) do {
    private _m0 = (_table select _i) select 0;
    private _m1 = (_table select (_i + 1)) select 0;
    if (_mach >= _m0 && _mach <= _m1) exitWith {
        private _c0 = (_table select _i) select 1;
        private _c1 = (_table select (_i + 1)) select 1;
        _cd = linearConversion [_m0, _m1, _mach, _c0, _c1, true];
    };
};
// Above the last table entry, hold the high-Mach Cd.
private _lastIdx = (count _table) - 1;
if (_mach > ((_table select _lastIdx) select 0)) then {
    _cd = (_table select _lastIdx) select 1;
};

// The retard (the engine's airFriction-equivalent): the constant is the
// G1 conversion factor (rho * pi * (0.0254)^2 / (4 * 0.453592) at
// rho = 1.225).  The air-density ratio scales it (thinner air = less
// drag, the real atmospheric correction).
0.00068418 * (_cd / _bc) * (_velocity ^ 2) * _rhoRel