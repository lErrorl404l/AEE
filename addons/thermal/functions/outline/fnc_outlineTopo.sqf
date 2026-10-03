#include "..\..\script_component.hpp"
/*
 * Capsule-union silhouette topology (issue #204, fusion outline).
 *
 * Copied from workshop 3811605241 whale_ecoti_llll functions/fn_outlineTopo.sqf.
 * The silhouette of a body is the UNION of its member capsules (two end circles
 * and two straight sides).  This function samples each capsule's screen ring in
 * camera "tangent" coordinates, drops the samples that fall inside another
 * capsule, finds the exact crossing points by bisection and returns per-capsule
 * polylines.  A point is stored as [t, c, s] relative to its capsule basis:
 * point = A + AB*t + N*c + E*s.  fnc_outlineDraw rebuilds the world points
 * every frame from the animated bones, so the outline stays glued to the moving
 * body while the topology recomputes only a few times a second.
 *
 * aee drives it: fnc_outlineDraw builds the capsule descriptors and the camera
 * basis from aee's own state, the hot list FUNC(outlineCollect) (which compares
 * QGVAR(selTemperature) against the ambient air temperature) and the resolved
 * device field FUNC(resolveFusionDevice)/FUNC(fusionFovGate).
 *
 * Pure: array and vector maths only, no engine state, so the harness runs it.
 * The source reads the capsule fields with `params`; they are read here with
 * `select` and a count guard so the real kernel executes in tools/tests.
 *
 * Params:
 *   0: _cd    (ARRAY)  per capsule, [] (invalid) or [A3, AB3, N3, E3, rA, rB].
 *   1: _cam   (ARRAY)  the eye point (ASL vector).
 *   2: _vF    (ARRAY)  forward unit vector.
 *   3: _vR    (ARRAY)  right unit vector.
 *   4: _vU    (ARRAY)  up unit vector.
 *   5: _pxTan (SCALAR) tangent covered by one pixel (sampling density).
 *   6: _smooth (BOOL, default false) one Chaikin pass for large silhouettes.
 *
 * Returns: ARRAY indexed like _cd: each entry is a LIST of polylines, each a
 *          list of [t, c, s].
 *
 * SQF variable names are NOT case sensitive (_R and _r are the SAME variable),
 * so the source's _vF/_vR/_vU naming is kept to avoid any collision.
 */
params [
    ["_cd", [], [[]]],
    ["_cam", [0, 0, 0], [[]], 3],
    ["_vF", [0, 1, 0], [[]], 3],
    ["_vR", [1, 0, 0], [[]], 3],
    ["_vU", [0, 0, 1], [[]], 3],
    ["_pxTan", 0.001, [0]],
    ["_smooth", false, [true]]
];

// --------------------------------------------------------------------------
// 1) 2D projection of the capsules (perspective, tangent coordinates)
//    index : 0 a2 | 1 ab2 | 2 len2 | 3 radius at A | 4 radius at B | 5 centre
//            6 bounding radius | 7 n2 | 8 e2 | 9 len | 10 bounding radius^2
// --------------------------------------------------------------------------
private _c2 = _cd apply {
    if (_x isEqualTo []) then { [] } else {
        private _a3 = _x select 0;
        private _ab3 = _x select 1;
        private _n3 = _x select 2;
        private _e3 = _x select 3;
        private _rad = _x select 4;
        private _radB = if ((count _x) > 5) then { _x select 5 } else { -1 };
        if (_radB < 0) then { _radB = _rad; };
        private _da = _a3 vectorDiff _cam;
        private _db = _da vectorAdd _ab3;
        private _fa = (_da vectorDotProduct _vF) max 0.05;
        private _fb = (_db vectorDotProduct _vF) max 0.05;
        private _a2 = [(_da vectorDotProduct _vR) / _fa, (_da vectorDotProduct _vU) / _fa, 0];
        private _b2 = [(_db vectorDotProduct _vR) / _fb, (_db vectorDotProduct _vU) / _fb, 0];
        private _fm = (_fa + _fb) * 0.5;
        private _ab2 = _b2 vectorDiff _a2;
        private _len = vectorMagnitude _ab2;
        private _rrA = _rad / _fm;
        private _rrB = _radB / _fm;
        private _bR = (_len * 0.5) + (_rrA max _rrB);
        [
            _a2, _ab2, ((_len * _len) max 1e-12), _rrA, _rrB,
            (_a2 vectorAdd (_ab2 vectorMultiply 0.5)), _bR,
            [(_n3 vectorDotProduct _vR) / _fm, (_n3 vectorDotProduct _vU) / _fm, 0],
            [(_e3 vectorDotProduct _vR) / _fm, (_e3 vectorDotProduct _vU) / _fm, 0],
            _len, (_bR * _bR)
        ]
    };
};

// Interpolate two [t, c, s] samples.
private _lerp = {
    params ["_a", "_b", "_f"];
    [
        (_a select 0) + (((_b select 0) - (_a select 0)) * _f),
        (_a select 1) + (((_b select 1) - (_a select 1)) * _f),
        (_a select 2) + (((_b select 2) - (_a select 2)) * _f)
    ]
};

// --------------------------------------------------------------------------
// 2) The edge of each capsule
// --------------------------------------------------------------------------
private _topo = [];
private _nC = count _c2;

for "_i" from 0 to (_nC - 1) do {
    private _o = _c2 select _i;
    if (_o isEqualTo []) then { _topo pushBack []; continue };

    private _cdi = _cd select _i;
    private _r = _cdi select 4;
    private _rB = if ((count _cdi) > 5) then { _cdi select 5 } else { -1 };
    if (_rB < 0) then { _rB = _r; };

    // Neighbours: only the capsules whose bounding circle touches ours.
    // Nested guards rather than a boolean block: an empty descriptor must not
    // reach the bounding-circle read.
    private _cand = [];
    {
        if ((_forEachIndex isNotEqualTo _i) && (_x isNotEqualTo [])) then {
            if (((_o select 5) vectorDistance (_x select 5)) < ((_o select 6) + (_x select 6))) then {
                _cand pushBack _forEachIndex;
            };
        };
    } forEach _c2;

    // Adaptive density: the larger the member on screen, the more samples.
    private _rpx = ((_o select 3) max (_o select 4)) / _pxTan;
    private _m = ((round (_rpx / 3)) max 3) min 6;
    private _k = ((ceil (((_o select 9) / _pxTan) / 30)) max 1) min 4;

    // Closed ring: +N side, half circle at B, -N side, half circle at A.
    private _smp = [];
    for "_j" from 0 to (_k - 1) do { _smp pushBack [_j / _k, _r + ((_rB - _r) * (_j / _k)), 0]; };
    for "_j" from 0 to (_m - 1) do {
        private _th = _j * 180 / _m;
        _smp pushBack [1, _rB * (cos _th), _rB * (sin _th)];
    };
    for "_j" from 0 to (_k - 1) do { _smp pushBack [1 - (_j / _k), -(_r + ((_rB - _r) * (1 - (_j / _k)))), 0]; };
    for "_j" from 0 to (_m - 1) do {
        private _th = _j * 180 / _m;
        _smp pushBack [0, -_r * (cos _th), -_r * (sin _th)];
    };

    // 2D positions of the samples, computed once.
    private _a2o = _o select 0;
    private _abo = _o select 1;
    private _n2o = _o select 7;
    private _e2o = _o select 8;
    private _pos = _smp apply {
        _a2o vectorAdd (_abo vectorMultiply (_x select 0))
             vectorAdd (_n2o vectorMultiply (_x select 1))
             vectorAdd (_e2o vectorMultiply (_x select 2))
    };

    // State of each sample: -1 = outside, else the index of the hiding capsule.
    private _st = if (_cand isEqualTo []) then {
        _smp apply { -1 }
    } else {
        _pos apply {
            private _p = _x;
            private _h = _cand findIf {
                private _q = _c2 select _x;
                private _hit = false;
                if ((_p vectorDistanceSqr (_q select 5)) < (_q select 10)) then {
                    private _ap = _p vectorDiff (_q select 0);
                    private _t = (((_ap vectorDotProduct (_q select 1)) / (_q select 2)) max 0) min 1;
                    private _rt = ((_q select 3) + (((_q select 4) - (_q select 3)) * _t)) * 0.995;
                    _hit = (_ap vectorDistanceSqr ((_q select 1) vectorMultiply _t)) < (_rt * _rt);
                };
                _hit
            };
            if (_h < 0) then { -1 } else { _cand select _h }
        }
    };

    // Walk the ring and split it into the visible polylines.
    private _polys = [];
    private _nSmp = count _smp;
    private _start = _st findIf { _x < 0 };

    if (_start >= 0) then {
        private _cur = [];
        for "_q" from 0 to (_nSmp - 1) do {
            private _i0 = (_start + _q) mod _nSmp;
            private _i1 = (_i0 + 1) mod _nSmp;
            private _a0 = _st select _i0;
            private _a1 = _st select _i1;
            private _s0 = _smp select _i0;
            private _s1 = _smp select _i1;

            if (_a0 < 0) then {
                if (_a1 < 0) then {
                    // Outside -> outside: full segment.
                    if (_cur isEqualTo []) then { _cur pushBack _s0; };
                    _cur pushBack _s1;
                } else {
                    // Outside -> inside: bisect for the entry point.
                    private _p0 = _pos select _i0;
                    private _dp = (_pos select _i1) vectorDiff _p0;
                    private _qq = _c2 select _a1;
                    private _lo = 0;
                    private _hi = 1;
                    for "_b" from 1 to 4 do {
                        private _mid = (_lo + _hi) * 0.5;
                        private _ap = (_p0 vectorAdd (_dp vectorMultiply _mid)) vectorDiff (_qq select 0);
                        private _tq = (((_ap vectorDotProduct (_qq select 1)) / (_qq select 2)) max 0) min 1;
                        private _rq = ((_qq select 3) + (((_qq select 4) - (_qq select 3)) * _tq)) * 0.995;
                        if ((_ap vectorDistanceSqr ((_qq select 1) vectorMultiply _tq)) < (_rq * _rq)) then { _hi = _mid; } else { _lo = _mid; };
                    };
                    if (_cur isEqualTo []) then { _cur pushBack _s0; };
                    _cur pushBack ([_s0, _s1, _hi] call _lerp);
                    _polys pushBack _cur;
                    _cur = [];
                };
            } else {
                if (_a1 < 0) then {
                    // Inside -> outside: restart from the exit point.
                    private _p0 = _pos select _i0;
                    private _dp = (_pos select _i1) vectorDiff _p0;
                    private _qq = _c2 select _a0;
                    private _lo = 0;
                    private _hi = 1;
                    for "_b" from 1 to 4 do {
                        private _mid = (_lo + _hi) * 0.5;
                        private _ap = (_p0 vectorAdd (_dp vectorMultiply _mid)) vectorDiff (_qq select 0);
                        private _tq = (((_ap vectorDotProduct (_qq select 1)) / (_qq select 2)) max 0) min 1;
                        private _rq = ((_qq select 3) + (((_qq select 4) - (_qq select 3)) * _tq)) * 0.995;
                        if ((_ap vectorDistanceSqr ((_qq select 1) vectorMultiply _tq)) < (_rq * _rq)) then { _lo = _mid; } else { _hi = _mid; };
                    };
                    _cur = [[_s0, _s1, _lo] call _lerp, _s1];
                };
            };
        };
        if (_cur isNotEqualTo []) then { _polys pushBack _cur; };
    };

    // Merge the aligned points on the straight sides (s = 0, same c side).
    _polys = _polys apply {
        private _pl = _x;
        private _cnt = count _pl;
        if (_cnt < 3) then { _pl } else {
            private _out = [_pl select 0];
            for "_mi" from 1 to (_cnt - 2) do {
                private _pv = _pl select (_mi - 1);
                private _cu = _pl select _mi;
                private _nx = _pl select (_mi + 1);
                private _straight = ((_pv select 2) == 0) && {(_cu select 2) == 0} && {(_nx select 2) == 0}
                                    && {((_pv select 1) * (_cu select 1)) > 0} && {((_cu select 1) * (_nx select 1)) > 0};
                if (!_straight) then { _out pushBack _cu; };
            };
            _out pushBack (_pl select -1);
            _out
        }
    };

    // Chaikin smoothing (one pass) for the large silhouettes.
    if (_smooth) then {
        _polys = _polys apply {
            private _pl = _x;
            if ((count _pl) < 3) then { _pl } else {
                private _out = [_pl select 0];
                for "_m2" from 0 to ((count _pl) - 2) do {
                    private _pa = _pl select _m2;
                    private _pb = _pl select (_m2 + 1);
                    _out pushBack ([_pa, _pb, 0.25] call _lerp);
                    _out pushBack ([_pa, _pb, 0.75] call _lerp);
                };
                _out pushBack (_pl select -1);
                _out
            }
        };
    };

    _topo pushBack _polys;
};

_topo
