#include "..\..\script_component.hpp"

/*
Crater shape from a known apparent crater.

When the apparent crater is known (a published measurement or a numerical
model such as CONWEP), this kernel derives the remaining crater features from
the two shape relations:

    V      = 0.5 * pi * R_a^2 * D_a      paraboloid volume (m^3)
    R_lip  = 1.25 * R_a                  lip radius (m)
    H_lip  = 0.25 * D_a                  lip height (m)
    R_ej   = 2.15 * R_a                  ejecta radius (m, Glasstone 6.71)
    R_true = 1.15 * R_a                  true radius (m, up to optimum DOB)
    D_true = max(D_a, DOB + 0.4 * W^(1/3))

The apparent crater is the visible crater after fallback.  The true crater is
the excavated crater before fallback: its diameter is 1.15 times the apparent
up to the optimum depth of burial, and its depth is the deeper of the apparent
depth and the burial depth plus 0.4 * W^(1/3).  The 0.4 is ft/lb^(1/3) and
converts to 0.15864 m/kg^(1/3).

Sources: TM 5-855-1; UFC 3-340-02; Kinney and Graham (1985); Glasstone and
Dolan (Glasstone 6.71); Ambrosini.

Input:  [_rA, _dA, _dofM, _massKg] - apparent radius (m), apparent depth (m),
        depth of burial of the charge centre (m), charge mass (kg).
Output: [V, R_lip, H_lip, R_ej, R_true, D_true] (0s when the radius is not
        positive).
Public: No
*/

params [["_rA", 1, [0]], ["_dA", 1, [0]], ["_dofM", 0, [0]], ["_massKg", 1, [0]]];

if (_rA <= 0 || _dA <= 0) exitWith { [0, 0, 0, 0, 0, 0] };

private _v = 0.5 * pi * _rA * _rA * _dA;
private _rLip = 1.25 * _rA;
private _hLip = 0.25 * _dA;
private _rEj = 2.15 * _rA;
private _rTrue = 1.15 * _rA;
private _dTrue = _dA max (_dofM + 0.15864 * (_massKg ^ (1 / 3)));

[_v, _rLip, _hLip, _rEj, _rTrue, _dTrue]
