#include "..\script_component.hpp"

/*
Multiple-edge diffraction loss over a terrain profile (issue #13).

The issue text calls for a "sum of losses (Carnegie method)".  No
radio-diffraction method named "Carnegie" exists (verified: Crossref returns
nothing).  The established multiple-edge method is Deygout (1966), and that
is what is implemented here.

Deygout procedure: find the main edge (the largest diffraction parameter v
over the whole path), add its single-edge loss, then recurse on the two
sub-paths (tx to main edge, main edge to rx), re-referencing the straight
line to the main edge apex.  The recursion is capped at 3 edges, the usual
practical limit.

SOURCE: J. Deygout (1966) "Multiple knife-edge diffraction of microwaves",
IEEE Trans. Antennas Propag. 14(4):480-489, DOI 10.1109/TAP.1966.1138719.
The two-edge combination and the predominant-edge form are also given in
ITU-R P.526-16 section 4.3 (eq (39)-(43)); the per-edge loss is P.526-16
section 4.1 eq (31), the same expression fnc_calculateKnifeEdgeLoss uses.

Args:
  0: distances <ARRAY> distance from tx to each profile point, m (ascending)
  1: heights   <ARRAY> terrain height ASL at each profile point, m
  2: hTx       <NUMBER> transmitter height ASL, m
  3: hRx       <NUMBER> receiver height ASL, m
  4: frequency <NUMBER> carrier, Hz

Return: <NUMBER> total diffraction loss, dB (0 when the path is clear).
*/

params [
    ["_distances", [], [[]]],
    ["_heights", [], [[]]],
    ["_hTx", 0, [0]],
    ["_hRx", 0, [0]],
    ["_freqHz", 1e8, [0]]
];

private _n = count _heights;
if (_n < 3) exitWith { 0 };
if ((count _distances) != _n) exitWith { 0 };

private _lambda = 3e8 / (_freqHz max 1);
private _total = 0;
private _segments = [[0, _n - 1, _hTx, _hRx]];
private _head = 0;
private _edges = 0;

while { (_head < (count _segments)) && (_edges < 3) } do {
    private _seg = _segments select _head;
    _head = _head + 1;
    _seg params ["_i0", "_i1", "_h0", "_h1"];
    if ((_i1 - _i0) >= 2) then {
        private _d0 = _distances select _i0;
        private _d1 = _distances select _i1;
        private _span = _d1 - _d0;
        if (_span > 0) then {
            private _maxV = -1e9;
            private _maxI = -1;
            for "_i" from (_i0 + 1) to (_i1 - 1) do {
                private _di = _distances select _i;
                private _line = _h0 + ((_h1 - _h0) * ((_di - _d0) / _span));
                private _excess = (_heights select _i) - _line;
                private _da = _di - _d0;
                private _db = _d1 - _di;
                private _v = _excess * (sqrt ((2 * (_da + _db)) / (_lambda * (_da max 1) * (_db max 1))));
                if (_v > _maxV) then { _maxV = _v; _maxI = _i; };
            };
            if ((_maxV > 0) && (_maxI >= 0)) then {
                _total = _total + (6.9 + (20 * (log ((sqrt (((_maxV - 0.1) ^ 2) + 1)) + _maxV - 0.1))));
                _edges = _edges + 1;
                private _apex = _heights select _maxI;
                _segments pushBack [_i0, _maxI, _h0, _apex];
                _segments pushBack [_maxI, _i1, _apex, _h1];
            };
        };
    };
};

_total
