#include "..\script_component.hpp"

/*
3D electromagnetic link propagation (issue #13).

Samples the terrain profile between two positions with getTerrainHeightASL,
builds the distances and heights the diffraction kernel needs, and returns
the Deygout multiple-edge diffraction loss plus a link state.

The ground-bounce (two-ray) excess is NOT computed here: it is a property of
the antenna heights and the range, and the radio budget applies it from the
reference link in fnc_calculateRadioPropagation.  This driver is the
terrain-dependent part of the 3D model.

This is the only EM kernel that touches the engine (getTerrainHeightASL), so
it is source-contracted in the test suite and is not executed by sqf_lite;
the pure kernels it composes are.

Args:
  0: tx position <ARRAY> ASL, m
  1: rx position <ARRAY> ASL, m
  2: frequency   <NUMBER> carrier, Hz
  3: tx height   <NUMBER> transmitter above ground, m
  4: rx height   <NUMBER> receiver above ground, m
  5: samples     <NUMBER> profile points along the path

Return: <ARRAY> [diffractionLossDB, state]
  state is "los" (clear), "diffraction" (shadowed, weak) or "shadow" (deep
  shadow).  The loss thresholds (1 dB, 15 dB) are UNSOURCED banding.
*/

params [
    ["_txPos", [], [[]]],
    ["_rxPos", [], [[]]],
    ["_freqHz", 1e8, [0]],
    ["_hTx", 2, [0]],
    ["_hRx", 1.5, [0]],
    ["_samples", 24, [0]]
];

if (((count _txPos) < 2) || ((count _rxPos) < 2)) exitWith { [0, "los"] };

private _n = ((_samples max 3) min 64);
private _x0 = _txPos select 0;
private _y0 = _txPos select 1;
private _x1 = _rxPos select 0;
private _y1 = _rxPos select 1;
private _dx = _x1 - _x0;
private _dy = _y1 - _y0;
private _dist2D = sqrt ((_dx ^ 2) + (_dy ^ 2));
private _z0 = (_txPos select 2) + _hTx;
private _z1 = (_rxPos select 2) + _hRx;

private _distances = [];
private _heights = [];
for "_i" from 0 to _n do {
    private _t = _i / _n;
    private _px = _x0 + (_dx * _t);
    private _py = _y0 + (_dy * _t);
    private _h = getTerrainHeightASL [_px, _py];
    if (_i == 0) then { _h = _z0; };
    if (_i == _n) then { _h = _z1; };
    _distances pushBack (_dist2D * _t);
    _heights pushBack _h;
};

private _diffraction = [_distances, _heights, _z0, _z1, _freqHz] call FUNC(calculateDeygoutDiffraction);

private _state = "los";
if (_diffraction >= 15) then {
    _state = "shadow";
} else {
    if (_diffraction >= 1) then { _state = "diffraction"; };
};

[_diffraction, _state]
