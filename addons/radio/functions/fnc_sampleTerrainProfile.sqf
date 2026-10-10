#include "..\script_component.hpp"

/*
Terrain profile sampler for the diffraction kernel.

Samples getTerrainHeightASL along the horizontal line from the transmitter
to the receiver at equal spacing and returns the heights ASL.  The engine
query is the only engine dependency here; the diffraction geometry lives in
fnc_calculateTerrainDiffraction.

The sample count is bounded (the issue's cost fix): the spacing widens when
the path is longer than the cap allows, so one link never exceeds the cap.
Sampling at 50-100 m over a 5 km link is 50-100 samples, which the issue
states is affordable.

Arguments:
  0: Array  - transmitter position, ASL
  1: Array  - receiver position, ASL
  2: Number - nominal sample spacing, metres (default 50)
  3: Number - sample cap (default 120)

Returns:
  Array - terrain heights ASL, first = Tx end, last = Rx end
Public: No
*/

params [
    ["_txPos", [], [[]]],
    ["_rxPos", [], [[]]],
    ["_step", 50, [0]],
    ["_maxSamples", 120, [0]]
];

if ((count _txPos < 2) || (count _rxPos < 2)) exitWith { [] };

private _dx = (_rxPos select 0) - (_txPos select 0);
private _dy = (_rxPos select 1) - (_txPos select 1);
private _dist = sqrt ((_dx * _dx) + (_dy * _dy));
if (_dist <= 0) exitWith { [] };

// Bounded sample count: widen the spacing when the path is long, so a link
// never exceeds the cap.
private _n = ((ceil (_dist / (_step max 1))) + 1) min (_maxSamples max 2);

private _profile = [];
for "_i" from 0 to (_n - 1) do {
    private _t = _i / (_n - 1);
    private _x = (_txPos select 0) + (_dx * _t);
    private _y = (_txPos select 1) + (_dy * _t);
    _profile pushBack getTerrainHeightASL [_x, _y];
};

_profile
