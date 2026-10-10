#include "..\script_component.hpp"

/*
Terrain diffraction excess loss over a sampled profile (Deygout method).

SOURCE: Recommendation ITU-R P.526-16 (2025-11), Annex 1 section 4.1
(single knife-edge, equations 26 and 31) and section 4.3 (double isolated
edges, the "predominant edge" method that recurses on the sub-paths).

The path is a list of terrain heights ASL sampled at equal horizontal
spacing.  The transmitter and receiver antenna heights are added to the
first and last samples.  Each interior sample j has an excess height h_j
above the straight Tx-Rx line and a dimensionless diffraction parameter
(P.526 eq. 26):

    nu_j = h_j * sqrt( 2/lambda * (1/d1 + 1/d2) )    d1, d2 = distances
                                                     to the path ends

The predominant edge is the sample with the largest nu.  Its loss is
J(nu) (fnc_calculateKnifeEdgeLoss, P.526 eq. 31).  The method recurses:
the sub-paths Tx->edge and edge->Rx are searched again, up to the edge
cap, and the losses are summed.  This is the classic Deygout
successive-knife-edge method (Deygout, J. (1966) "Multiple knife-edge
diffraction of microwaves", IEEE Trans. Antennas Propag. 14(4) 480-489,
DOI 10.1109/TAP.1966.1138719).  P.526 section 4.3 states a correction term
Tc (eq. 41) for the two-edge case; this kernel does NOT apply it, so the
result is a conservative (slightly high) estimate.  That is recorded
rather than approximated.

A sample is an obstacle only when it protrudes ABOVE the direct Tx-Rx
line (h > 0).  P.526 section 4.1 models an isolated knife-edge obstacle,
not a smooth surface: without this rule a flat profile would put every
sample at grazing and the recursion would sum spurious edges.  A smooth
or gently rolling surface therefore reads 0 dB here; its Fresnel-zone
intrusion is not modelled (P.526 section 3 covers the smooth Earth).

The kernel is pure: no engine state, no missionNamespace, no random.

Arguments:
  0: Array  - terrain heights ASL, metres, first = Tx end, last = Rx end
  1: Number - horizontal sample spacing, metres
  2: Number - Tx antenna height above the terrain at the first sample, m
  3: Number - Rx antenna height above the terrain at the last sample, m
  4: Number - wavelength, metres

Returns the excess diffraction loss in dB (0 for a clear path).

Example: [[100, 150, 100], 100, 2, 2, 3] call aee_radio_fnc_calculateTerrainDiffraction
Public: No
*/

params [
    ["_profile", [], [[]]],
    ["_step", 50, [0]],
    ["_txAGL", 2, [0]],
    ["_rxAGL", 2, [0]],
    ["_lambda", 3, [0]]
];

private _n = count _profile;
if ((_n < 2) || (_step <= 0) || (_lambda <= 0)) exitWith { 0 };

private _txH = (_profile select 0) + _txAGL;
private _rxH = (_profile select (_n - 1)) + _rxAGL;

// Sub-paths awaiting analysis: [startIndex, startHeight, endIndex, endHeight].
// The predominant edge over all sub-paths is taken each pass and the chosen
// sub-path splits in two, which is the Deygout recursion written iteratively.
private _paths = [[0, _txH, _n - 1, _rxH]];
private _loss = 0;
private _edges = 0;
private _done = false;

// Three edges is the Deygout cap the issue names (3-4); beyond that the
// added edges are negligible.
while { (!_done) && (_edges < 3) } do {
    private _bestNu = -1e9;
    private _bestPath = -1;
    private _bestIdx = -1;

    for "_p" from 0 to ((count _paths) - 1) do {
        private _path = _paths select _p;
        private _i0 = _path select 0;
        private _h0 = _path select 1;
        private _i1 = _path select 2;
        private _h1 = _path select 3;
        if ((_i1 - _i0) >= 2) then {
            for "_j" from (_i0 + 1) to (_i1 - 1) do {
                private _d1 = (_j - _i0) * _step;
                private _d2 = (_i1 - _j) * _step;
                private _lineH = _h0 + ((_h1 - _h0) * _d1 / (_d1 + _d2));
                private _h = (_profile select _j) - _lineH;
                // Only a sample above the line is an isolated obstacle.
                if (_h > 0) then {
                    private _nu = _h * sqrt ((2 / _lambda) * ((1 / _d1) + (1 / _d2)));
                    if (_nu > _bestNu) then {
                        _bestNu = _nu;
                        _bestPath = _p;
                        _bestIdx = _j;
                    };
                };
            };
        };
    };

    if (_bestNu <= -0.78) then {
        // No sample obstructs the path: the recursion ends.
        _done = true;
    } else {
        _loss = _loss + ([_bestNu] call FUNC(calculateKnifeEdgeLoss));

        private _path = _paths select _bestPath;
        private _i0 = _path select 0;
        private _h0 = _path select 1;
        private _i1 = _path select 2;
        private _h1 = _path select 3;
        private _edgeH = _profile select _bestIdx;

        private _nextPaths = [];
        for "_p" from 0 to ((count _paths) - 1) do {
            if (_p == _bestPath) then {
                _nextPaths pushBack [_i0, _h0, _bestIdx, _edgeH];
                _nextPaths pushBack [_bestIdx, _edgeH, _i1, _h1];
            } else {
                _nextPaths pushBack (_paths select _p);
            };
        };
        _paths = _nextPaths;

        _edges = _edges + 1;
    };
};

_loss
