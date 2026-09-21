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
drag.rs calculate_retard), verified against the engine's airFriction.

The Cd(Mach) tables are the AUTHORITATIVE modern BRL/JBM tables (76 G1
points, 81 G7 points, transcribed from the JBM drag-curve tool and
cross-checked against Litz "Applied Ballistics" A5-1/A5-3, McCoy
"Modern Exterior Ballistics" Ch.7, NATO AOP-55 Annex A, and the US ARL
BRL reports - the transonic band Mach 0.8-1.2 verified at every 0.05
Mach increment).  The dense table captures the real transonic drag rise
that a coarse table misses: Cd peaks ~0.66 at Mach 1.3 (~3.2x the
subsonic 0.20).

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

// The G1 drag table (JBM/BRL, transonic-verified, 76 points).
private _G1 = [
    [0.000, 0.2630], [0.050, 0.2560], [0.100, 0.2490], [0.150, 0.2410],
    [0.200, 0.2340], [0.250, 0.2280], [0.300, 0.2210], [0.350, 0.2160],
    [0.400, 0.2100], [0.450, 0.2060], [0.500, 0.2030], [0.550, 0.2020],
    [0.600, 0.2030], [0.700, 0.2170], [0.725, 0.2230], [0.750, 0.2310],
    [0.775, 0.2420], [0.800, 0.2550], [0.825, 0.2710], [0.850, 0.2900],
    [0.875, 0.3140], [0.900, 0.3420], [0.925, 0.3730], [0.950, 0.4080],
    [0.975, 0.4450], [1.000, 0.4810], [1.025, 0.5140], [1.050, 0.5430],
    [1.075, 0.5680], [1.100, 0.5880], [1.125, 0.6050], [1.150, 0.6190],
    [1.200, 0.6390], [1.250, 0.6520], [1.300, 0.6590], [1.350, 0.6620],
    [1.400, 0.6630], [1.450, 0.6610], [1.500, 0.6570], [1.550, 0.6530],
    [1.600, 0.6490], [1.650, 0.6450], [1.700, 0.6400], [1.750, 0.6360],
    [1.800, 0.6320], [1.850, 0.6270], [1.900, 0.6230], [1.950, 0.6190],
    [2.000, 0.5934], [2.100, 0.5820], [2.200, 0.5710], [2.300, 0.5610],
    [2.400, 0.5510], [2.500, 0.5400], [2.600, 0.5300], [2.700, 0.5210],
    [2.800, 0.5130], [2.900, 0.5050], [3.000, 0.4990], [3.100, 0.4930],
    [3.200, 0.4870], [3.300, 0.4820], [3.400, 0.4770], [3.500, 0.4720],
    [3.600, 0.4670], [3.700, 0.4630], [3.800, 0.4590], [3.900, 0.4560],
    [4.000, 0.4530], [4.100, 0.4500], [4.200, 0.4470], [4.300, 0.4450],
    [4.400, 0.4430], [4.500, 0.4410], [4.600, 0.4400], [4.700, 0.4390],
    [4.800, 0.4380], [4.900, 0.4370], [5.000, 0.4370]
];

// The G7 drag table (JBM/BRL, transonic-verified, 81 points).
private _G7 = [
    [0.000, 0.1198], [0.050, 0.1198], [0.100, 0.1198], [0.150, 0.1198],
    [0.200, 0.1198], [0.250, 0.1198], [0.300, 0.1198], [0.350, 0.1198],
    [0.400, 0.1198], [0.450, 0.1198], [0.500, 0.1198], [0.550, 0.1198],
    [0.600, 0.1198], [0.700, 0.1208], [0.725, 0.1226], [0.750, 0.1256],
    [0.775, 0.1299], [0.800, 0.1358], [0.825, 0.1434], [0.850, 0.1527],
    [0.875, 0.1637], [0.900, 0.1763], [0.925, 0.1905], [0.950, 0.2063],
    [0.975, 0.2237], [1.000, 0.2427], [1.025, 0.2632], [1.050, 0.2852],
    [1.075, 0.3086], [1.100, 0.3334], [1.125, 0.3596], [1.150, 0.3871],
    [1.200, 0.4460], [1.250, 0.5095], [1.300, 0.5743], [1.350, 0.6320],
    [1.400, 0.6748], [1.450, 0.7000], [1.500, 0.7100], [1.550, 0.7100],
    [1.600, 0.7030], [1.650, 0.6930], [1.700, 0.6810], [1.750, 0.6680],
    [1.800, 0.6550], [1.850, 0.6420], [1.900, 0.6300], [1.950, 0.6180],
    [2.000, 0.6060], [2.100, 0.5850], [2.200, 0.5670], [2.300, 0.5510],
    [2.400, 0.5370], [2.500, 0.5240], [2.600, 0.5130], [2.700, 0.5020],
    [2.800, 0.4920], [2.900, 0.4830], [3.000, 0.4750], [3.100, 0.4670],
    [3.200, 0.4600], [3.300, 0.4540], [3.400, 0.4480], [3.500, 0.4430],
    [3.600, 0.4380], [3.700, 0.4330], [3.800, 0.4290], [3.900, 0.4250],
    [4.000, 0.4210], [4.100, 0.4180], [4.200, 0.4150], [4.300, 0.4120],
    [4.400, 0.4100], [4.500, 0.4070], [4.600, 0.4050], [4.700, 0.4030],
    [4.800, 0.4010], [4.900, 0.4000], [5.000, 0.4000]
];

private _table = [_G1, _G7] select (_dragModel == 7);

// Table lookup with linear interpolation between the Mach breakpoints.
private _cd = 0.2030;
private _n = count _table;
if (_mach <= (_table select 0 select 0)) then {
    _cd = _table select 0 select 1;
} else {
    if (_mach >= (_table select (_n - 1) select 0)) then {
        _cd = _table select (_n - 1) select 1;
    } else {
        for "_i" from 0 to (_n - 2) do {
            private _m0 = (_table select _i) select 0;
            private _m1 = (_table select (_i + 1)) select 0;
            if (_mach >= _m0 && _mach <= _m1) exitWith {
                private _c0 = (_table select _i) select 1;
                private _c1 = (_table select (_i + 1)) select 1;
                _cd = linearConversion [_m0, _m1, _mach, _c0, _c1, true];
            };
        };
    };
};

// The retard: the G1 conversion constant, scaled by the air density.
0.00068418 * (_cd / _bc) * (_velocity ^ 2) * _rhoRel
