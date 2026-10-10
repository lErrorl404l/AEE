#include "..\..\script_component.hpp"

/*
Semi-Lagrangian scalar advection kernel (issue #116).  PURE: inputs to
outputs, it reads no engine state and writes none.

One time step of the advection term of the transport equation

    dc/dt = -(u dc/dx + v dc/dy + w dc/dz) + K (d2c/dx2 + ...) + S - R

is solved by tracing each cell centre BACKWARD along the horizontal wind for
one step and sampling the field at the departure point (semi-Lagrangian:
Staniforth & Cote 1991, Monthly Weather Review 119, 2206-2223; Stam 1999
"Stable Fluids", SIGGRAPH; Stam 2003 "Real-Time Fluid Dynamics for Games",
GDC).  The scheme is unconditionally stable: the Courant-Friedrichs-Lewy
limit does not apply, because the departure point is interpolated rather than
taken from a fixed upwind cell (Courant, Friedrichs & Lewy 1928 states the
limit for the explicit Eulerian scheme, which this kernel does not use).

The sample is BILINEAR.  Bilinear interpolation is first order and adds a
small implicit diffusion (Stam 1999, the numerical-dissipation section),
which is the accepted v1 trade-off; the issue states "start linear, move to
cubic if plumes smear".

The field is a flat row-major array: cell (i, j) is element i + j * width,
with i the x index and j the y index.

Arguments:
  0: field   (ARRAY)  flat row-major concentrations, length width*height
  1: width   (NUMBER) cells along x
  2: height  (NUMBER) cells along y
  3: originX (NUMBER) world x of cell (0, 0), metres
  4: originY (NUMBER) world y of cell (0, 0), metres
  5: cellM   (NUMBER) cell size, metres
  6: u       (NUMBER) wind x component, m/s
  7: v       (NUMBER) wind y component, m/s
  8: dt      (NUMBER) time step, seconds

Return:
  ARRAY - the advected flat field, length width*height.
*/

params [
    ["_field", [], [[]]],
    ["_width", 0, [0]],
    ["_height", 0, [0]],
    ["_originX", 0, [0]],
    ["_originY", 0, [0]],
    ["_cellM", 1000, [0]],
    ["_u", 0, [0]],
    ["_v", 0, [0]],
    ["_dt", 0, [0]]
];

if ((_width <= 0) || (_height <= 0) || (_cellM <= 0)) exitWith { _field };

// Bilinear sample of a flat field at fractional grid coords (_fx, _fy),
// inlined into the loop: a per-cell `call` of a helper costs more than the
// arithmetic it wraps on a 31x31 grid, and the y-dependent terms hoist out
// of the inner loop.  A sample outside the grid holds the nearest edge value.
private _invCell = 1 / _cellM;
private _out = [];
private _w = _width;
private _h = _height;

for "_j" from 0 to (_h - 1) do {
    private _yd = (_originY + (_j * _cellM)) - (_v * _dt);
    private _fy = (_yd - _originY) * _invCell;
    private _y = (_fy max 0) min (_h - 1);
    private _y0 = floor _y;
    private _y1 = (_y0 + 1) min (_h - 1);
    private _ty = _y - _y0;
    private _row0 = _y0 * _w;
    private _row1 = _y1 * _w;
    for "_i" from 0 to (_w - 1) do {
        private _xd = (_originX + (_i * _cellM)) - (_u * _dt);
        private _fx = (_xd - _originX) * _invCell;
        private _x = (_fx max 0) min (_w - 1);
        private _x0 = floor _x;
        private _x1 = (_x0 + 1) min (_w - 1);
        private _tx = _x - _x0;
        private _c00 = _field select (_x0 + _row0);
        private _c10 = _field select (_x1 + _row0);
        private _c01 = _field select (_x0 + _row1);
        private _c11 = _field select (_x1 + _row1);
        private _top = _c00 + (_c10 - _c00) * _tx;
        private _bot = _c01 + (_c11 - _c01) * _tx;
        _out pushBack (_top + (_bot - _top) * _ty);
    };
};

_out
