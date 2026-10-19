#include "..\..\script_component.hpp"
/*
Blast throw velocity and tumble rate for a body caught in the blast wind
(issue #160, the #132 tertiary throw applied to the corpse).

Every input comes from the existing blast model; no second physics model
is added.  The chain:

  - Peak dynamic pressure behind the shock (gamma = 1.4):
        q_o = 2.5 * P_so^2 / (7 * P_0 + P_so)            [kPa]
    Kinney & Graham, Explosive Shocks in Air (1985); Glasstone & Dolan,
    The Effects of Nuclear Weapons, ch. III (the overpressure/dynamic-
    pressure relation).
  - Blast wind speed (Bernoulli, ambient density):
        u = sqrt(2 * q_o / rho_0)                         [m/s]
    Kinney & Graham.  Approximate: it uses the AMBIENT density, so it is
    an upper bound (the post-shock density is higher).
  - Drag impulse on the body over the positive phase:
        J = (C_d A) * q_o * t_d                           [N.s]
        dv = J / m                                        [m/s]
    The drag-area product C_d*A is MEASURED, not assumed.  Richmond &
    Fletcher blew instrumented dummies down on the open desert surface
    (Project LN401), and their three reported dynamic-pressure impulses
    and peak body velocities (Table 3 of EC JRC119310, 2019: 8.78 kPa.ms
    -> 0.092 m/s, 58.27 -> 0.61, 379.13 -> 4.0) give a constant velocity
    per unit impulse of 0.01050 m/s per kPa.ms for their 70 kg subject,
    so C_d*A = 0.0105 * 70 = 0.735 m2.  The three points agree on it to
    better than 1 per cent.
  - The body cannot outrun the wind: dv is capped at u.
  - CEILING.  The impulse model over-predicts close in, where the model
    ignores body disruption, so dv is capped at the human terminal
    velocity (55 m/s, belly-to-earth).  This is a documented ceiling, not
    a measured blast-throw limit.
  - Tumble.  The drag resultant acts below the centre of mass, so the
    body rotates.  Angular impulse = J * d, I = m * k^2:
        omega = dv * d / k^2
    d = (c - 0.5) * h, with the COM at c = 0.57 of standing height
    (anthropometry) and the drag centre at h/2.  k = 0.30 m is the radius
    of gyration of the body about a transverse axis (Winter, Biomechanics
    and Motor Control of Human Movement).

Input:  [_pSo_kPa, _td_ms, _massKg]
Output: [throwSpeed_mps, tumbleRate_radps]
*/
params [["_pSo", 0, [0]], ["_td", 0, [0]], ["_massKg", 80, [0]]];

if (_pSo <= 0 || _td <= 0 || _massKg <= 0) exitWith { [0, 0] };

private _p0 = 101.325;   // kPa, ISA sea-level pressure
private _rho0 = 1.225;   // kg/m3, ISA sea-level density

// Peak dynamic pressure (Kinney & Graham 1985).
private _qo = 2.5 * _pSo * _pSo / (7 * _p0 + _pSo);

// Blast wind speed (Bernoulli; approximate, ambient density).
private _u = sqrt (2 * (_qo * 1000) / _rho0);

// Drag impulse over the positive phase.
private _cdArea = 0.735;         // m2, measured (Richmond & Fletcher; see header)
private _j = _cdArea * (_qo * 1000) * (_td / 1000);

private _dv = _j / _massKg;

// A body cannot outrun the wind.
_dv = _dv min _u;
// CEILING: the human terminal velocity; the impulse model over-predicts
// close in, where a real body is disrupted rather than launched.
_dv = _dv min 55;

// Tumble: the drag resultant acts below the centre of mass.
private _cCom = 0.57;    // COM at 57% of standing height
private _h = 1.75;       // m, mean adult male height
private _k = 0.30;       // m, radius of gyration (Winter)
private _d = (_cCom - 0.5) * _h;
private _omega = (_dv * _d) / (_k * _k);

[_dv, _omega]
