#include "..\..\script_component.hpp"

/*
Dense-gas pooling in terrain depressions (issue #120).

A dense gas that reaches a hollow collects there: it has nowhere to drain,
so its local concentration rises above the flat-ground plume value.  The
model the issue states is

  P_cell  = max(0, h_neighbour_mean - h_cell)
  C_eff   = C_plume * (1 + k_pool * P_cell)

where h_cell is the ground height of the cell, h_neighbour_mean is the
mean height of the surrounding cells, and P_cell is the pool depth in
metres.  k_pool is the concentration gain per metre of pooled depth.

NOTE: no published dense-gas model uses this form.  Real models resolve
terrain by three-dimensional CFD, or modulate a plume with terrain
downwash (AERMOD).  DEGADIS itself is a flat-ground box model.  The
form and the default k_pool are a MODELLING CHOICE for the engine, not a
measured or published constant, and k_pool is exposed so a caller can
tune it.  Do not cite this as a physical law.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command.

Arguments:
  0: NUMBER - cell ground height, m
  1: NUMBER - mean ground height of the neighbouring cells, m
  2: NUMBER - flat-ground plume concentration, kg/m3
  3: NUMBER - k_pool, concentration gain per metre (default 0.5)

Returns:
  ARRAY [poolDepth m, enhancedConcentration kg/m3]
*/

params [
    ["_cellHeight", 0, [0]],
    ["_neighbourMeanHeight", 0, [0]],
    ["_concentration", 0, [0]],
    ["_kPool", 0.5, [0]]
];

private _poolDepth = 0 max (_neighbourMeanHeight - _cellHeight);
private _enhanced = _concentration * (1 + _kPool * _poolDepth);

[_poolDepth, _enhanced]
