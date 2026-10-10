#include "..\..\script_component.hpp"

/*
Scalar-transport stability kernel (issue #116).  PURE: inputs to outputs.

The transport grid is chosen so the EXPLICIT Eulerian scheme would also be
stable, even though the shipped advection is the semi-Lagrangian scheme
(FUNC(scalarAdvectKernel)), which is not subject to a CFL limit.  This kernel
publishes the two dimensionless numbers so the margin is observable:

  Advection (CFL) number       C = |U| * dt / dx   <= 1
  Diffusion (von Neumann) number D = K * dt / dx^2 <= 1/2

Sources:
  - C, the Courant-Friedrichs-Lewy condition: Courant, Friedrichs & Lewy 1928,
    "Ueber die partiellen Differenzengleichungen der mathematischen Physik",
    Mathematische Annalen 100, 32-74.
  - D, the explicit central-difference diffusion limit D <= 1/2: the standard
    von Neumann (Fourier) stability bound for the explicit FTCS diffusion
    operator, stated in every finite-difference text (e.g. Press et al,
    "Numerical Recipes", section 19.2 "Diffusion Equation").

At the shipped grid (1 km cells) and the issue's example (1 Hz, 20 m/s) the
advection number is C = 0.02, stable by a factor of 50.

Arguments:
  0: u           (NUMBER) wind x component, m/s
  1: v           (NUMBER) wind y component, m/s
  2: cellM       (NUMBER) cell size, metres
  3: dt          (NUMBER) time step, seconds
  4: diffusivity (NUMBER) eddy diffusivity K, m^2/s

Return:
  ARRAY - [advectionNumber, diffusionNumber, isStable]
*/

params [
    ["_u", 0, [0]],
    ["_v", 0, [0]],
    ["_cellM", 1000, [0]],
    ["_dt", 0, [0]],
    ["_diffusivity", 0, [0]]
];

private _speed = (abs _u) max (abs _v);
private _cfl = 0;
private _diffusion = 0;
if (_cellM > 0) then {
    _cfl = _speed * _dt / _cellM;
    _diffusion = _diffusivity * _dt / (_cellM * _cellM);
};
private _stable = (_cfl <= 1) && (_diffusion <= 0.5);

[_cfl, _diffusion, _stable]
