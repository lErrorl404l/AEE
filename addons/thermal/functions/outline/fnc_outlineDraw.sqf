#include "..\..\script_component.hpp"
/*
 * Per-frame fusion outline worker (issue #204).
 *
 * Capsule-union silhouette copied from workshop 3811605241 whale_ecoti_llll
 * functions/fn_outlineTopo.sqf and functions/fn_drawOutlines.sqf: each hot
 * body is drawn as the UNION of its member capsules (FUNC(outlineTopo)), with
 * per-body-zone occlusion by checkVisibility and lineIntersectsSurfaces.  This
 * replaces the earlier hull of the projected skeleton (FUNC(outlineHull), now
 * removed).  The capsule topology is computed once per pass and rebuilt from
 * the animated bones every frame, which is what keeps the outline glued to the
 * moving body.
 *
 * aee drives it: the hot list is FUNC(outlineCollect) (aee's own
 * QGVAR(selTemperature) against the ambient air temperature), the device bound
 * is the thermal half-angle from FUNC(resolveFusionDevice) applied by
 * FUNC(fusionFovGate), and the canvas is FUNC(outlineCanvas).  No field of
 * view is hardcoded.  Two bounds are kept, and they are different things:
 *   - the fusion field (FUNC(fusionFovGate)) is the thermal CHANNEL;
 *   - the window test below is the source's HUD BOX (the pre-warm zone feeds
 *     the topology before a target enters the box; segments are clipped to it).
 *
 * Deliberate omissions from the source: the per-soldier gear radius
 * adjustments (headgear / vest / backpack) and the backpack inflation are not
 * ported, so the capsule radii are the unequipped table in
 * FUNC(outlineSkeleton).  The organic silhouette and the occlusion raycasts are
 * ported.
 *
 * Params:
 *   0: _player (OBJECT, default player).
 *
 * Returns: nothing.
 */
params [["_player", player, [objNull]]];

if (!hasInterface) exitWith {};
if (isNull _player) exitWith {};

private _settingOn = missionNamespace getVariable [QGVAR(fusionOutline), true];
if !(_settingOn isEqualType true) then { _settingOn = true; };
if (!_settingOn) exitWith {};

private _on = missionNamespace getVariable [QGVAR(outlineOn), false];
if !(_on isEqualType true) then { _on = false; };
if (!_on) exitWith {};

private _cal = ["begin"] call FUNC(outlineCanvas);
if (_cal isEqualTo []) exitWith {};
private _mapC = _cal select 4;

private _perfT0 = diag_tickTime;

// ---------- constants copied from the source (fn_drawOutlines) ----------
private _col = [1.00, 0.41, 0.10];   // orange core
private _opac = 0.55;
private _wCore = 2;
private _frac = 0.30;                 // HUD box half-size, fraction of safeZoneH
private _sensRes = 240;               // thermal detector lines
private _range = 400;                 // outline range, metres

// ---------- hot list (aee thermal state) ----------
private _hot = [] call FUNC(outlineCollect);

// ---------- our field gate: the resolved thermal channel half-angle ----------
private _pair = [_player] call FUNC(resolveFusionDevice);
private _halfAngleDeg = _pair select 2;
if !(_halfAngleDeg isEqualType 0) then { _halfAngleDeg = 20; };
if (_halfAngleDeg <= 0) then { _halfAngleDeg = 20; };

private _eyeState = [_player] call EFUNC(core,getEyeState);
private _eye = _eyeState select 0;
private _viewDir = _eyeState select 1;

// ---------- camera basis (ASL corrected: the source's v30.4 fix) ----------
private _camPos = positionCameraToWorld [0, 0, 0];               // AGL (for worldToScreen)
private _camASLr = AGLToASL _camPos;                              // true position (ASL)
private _fwdN = vectorNormalized ((AGLToASL (positionCameraToWorld [0, 0, 10])) vectorDiff _camASLr);
private _rgtN = vectorNormalized ((AGLToASL (positionCameraToWorld [10, 0, 0])) vectorDiff _camASLr);
private _upN = vectorNormalized ((AGLToASL (positionCameraToWorld [0, 10, 0])) vectorDiff _camASLr);
private _camTer = (_camASLr select 2) - (_camPos select 2);       // ground height under the camera
private _camASL = AGLToASL (_camPos vectorAdd (_fwdN vectorMultiply 0.6));
private _ign1 = vehicle player;

// ---------- FOV calibration (the source's worldToScreen method) ----------
private _p1 = worldToScreen (positionCameraToWorld [0, 0, 100]);
private _p2 = worldToScreen (positionCameraToWorld [0, 1, 100]);
private _kY = 0;
if ((count _p1) >= 2 && (count _p2) >= 2) then {
    private _newK = (abs ((_p2 select 1) - (_p1 select 1))) / 0.01;
    if ((_newK > 0.20) && (_newK < 60)) then { _kY = _newK; };
};
if (_kY <= 0) then { _kY = 1.2; };

// ---------- HUD box and its half-tangents ----------
private _halfW = (_frac * safeZoneH) / 2;
private _bx0 = 0.5 - _halfW;
private _bx1 = 0.5 + _halfW;
private _by0 = 0.5 - _halfW;
private _by1 = 0.5 + _halfW;
private _tanHalf = ((_halfW / _kY) max 0.003) min 1.00;
private _resX = (getResolution select 0) max 1;
private _resY = (getResolution select 1) max 1;
private _tanHalfX = _tanHalf * ((_resX / safeZoneW) / (_resY / safeZoneH));
private _tanWarm = _tanHalf * 1.25;
private _tanWarmX = _tanHalfX * 1.25;
private _pxTan = safeZoneH / (_kY * _resY);
private _pxTan1080 = _pxTan * (_resY / 1080);

// ---------- widths and colours (base 1080p, scaled to the resolution) ----------
private _scl = _resY / 1080;
private _wMin = (1.5 * _scl) max 1.2;
private _wFull = _wCore * _scl;
private _wSoft = (_wCore + 3) * _scl;

private _lvlMul = [1, 0.55, 0.25];
private _colsCore = _lvlMul apply { [_col select 0, _col select 1, _col select 2, _opac * _x] };
private _colsSoft = _lvlMul apply { [_col select 0, _col select 1, _col select 2, _opac * 0.30 * _x] };

private _levels = call FUNC(outlineSkeleton);

private _core = [];
private _soft = [];
private _drawn = 0;

{
    private _obj = _x;
    if (isNull _obj) then { continue };

    private _pASL = getPosASLVisual _obj;

    // OUR gate: the target must sit inside the resolved thermal channel.
    if !([_eye, _viewDir, _pASL, _halfAngleDeg] call FUNC(fusionFovGate)) then { continue };

    // Source window test: the HUD BOX, not the thermal channel.
    private _camU = _camPos vectorAdd [0, 0, _camTer - ((_pASL select 2) - ((ASLToAGL _pASL) select 2))];
    private _c0 = (_pASL vectorAdd [0, 0, 0.8]) vectorDiff _camASLr;
    private _f0 = _c0 vectorDotProduct _fwdN;
    if (_f0 < -2.2) then { continue };
    private _fullIn = false;
    if (_f0 > 0.5) then {
        private _u0 = abs ((_c0 vectorDotProduct _rgtN) / _f0);
        private _v0 = abs ((_c0 vectorDotProduct _upN) / _f0);
        private _mg = 2.2 / _f0;
        if ((_u0 > (_tanWarmX + _mg)) || (_v0 > (_tanWarm + _mg))) then { continue };
        private _mi = 1.5 / _f0;
        _fullIn = ((_u0 + _mi) < _tanHalfX) && ((_v0 + _mi) < _tanHalf);
    };

    private _dist = _camASLr vectorDistance _pASL;
    private _fade = ((_range - _dist) / (0.25 * _range)) min 1;
    if (_fade <= 0.02) then { continue };
    private _h1080 = 1.8 / ((_dist max 0.5) * _pxTan1080);

    // Simulated thermal sensor: target height on the detector, then the LOD.
    private _mpp = ((_dist max 0.5) * 2 * _tanHalf) / _sensRes;
    private _hSens = 1.8 / (_mpp max 1e-6);
    private _lv = [_hSens] call FUNC(outlineSensorLod);
    private _level = _levels select _lv;
    private _boneList = _level select 0;
    private _capList = _level select 1;
    private _probes = _level select 2;
    private _pmap = _level select 3;
    private _minPts = _level select 4;
    private _spIdx = if ((count _level) > 5) then { _level select 5 } else { [] };

    // Bone positions in the model, then in the world.
    private _sps = _boneList apply {
        private _sp = _obj selectionPosition _x;
        if (_sp isEqualTo [0, 0, 0]) then { [] } else { _sp }
    };
    // Virtual backpack points.  The gear pass is not ported, so these are the
    // source's two body points (the source inflates them when a backpack is
    // worn); the capsule then stays hidden in the torso.
    if (_spIdx isNotEqualTo []) then {
        private _bpA = _sps select (_spIdx select 0);
        private _bpB = _sps select (_spIdx select 1);
        if ((_bpA isEqualTo []) || (_bpB isEqualTo [])) then {
            _sps pushBack [];
            _sps pushBack [];
        } else {
            _sps pushBack _bpA;
            _sps pushBack _bpB;
        };
    };

    private _nOk = 0;
    private _pts = _sps apply {
        if (_x isEqualTo []) then { [] } else { _nOk = _nOk + 1; _obj modelToWorldVisual _x }
    };
    if (_nOk < _minPts) then { continue };

    // Capsule descriptors (the source's _cd construction).
    private _cd = _capList apply {
        private _cap = _x;
        private _ia = _cap select 0;
        private _ib = _cap select 1;
        private _rCap = _cap select 2;
        private _ext = _cap select 3;
        private _rBCap = if ((count _cap) > 4) then { _cap select 4 } else { -1 };
        if (_rBCap < 0) then { _rBCap = _rCap; };
        private _pA = _pts select _ia;
        private _pB = _pts select _ib;
        if ((_pA isEqualTo []) || (_pB isEqualTo [])) then { [] } else {
            private _b3 = _pB;
            if (_ext > 0) then {
                _b3 = _pA vectorAdd ((vectorNormalized (_pA vectorDiff _pB)) vectorMultiply _ext);
            };
            private _ab3 = _b3 vectorDiff _pA;
            private _view = vectorNormalized ((_pA vectorAdd (_ab3 vectorMultiply 0.5)) vectorDiff _camU);
            private _dir = if ((vectorMagnitude _ab3) < 0.005) then { _upN } else { vectorNormalized _ab3 };
            private _n3 = _dir vectorCrossProduct _view;
            if ((vectorMagnitude _n3) < 1e-3) then { _n3 = _rgtN; };
            _n3 = vectorNormalized _n3;
            [_pA, _ab3, _n3, vectorNormalized (_view vectorCrossProduct _n3), _rCap, _rBCap]
        }
    };

    // Capsule-union silhouette topology: the source's real mechanism.
    private _topo = [_cd, _camU, _fwdN, _rgtN, _upN, _pxTan1080, false] call FUNC(outlineTopo);

    // Occlusion per body zone.  A wall, a vehicle or the terrain hides the
    // outline, but another soldier in front does not (the source's v28.4
    // filter), so a firing line or a column does not blank the outline.
    private _vis = _probes apply {
        private _probeA = _pts select ((_capList select _x) select 0);
        private _probeB = _pts select ((_capList select _x) select 1);
        if ((_probeA isEqualTo []) || (_probeB isEqualTo [])) then { 1 } else {
            private _probeASL = AGLToASL ((_probeA vectorAdd _probeB) vectorMultiply 0.5);
            private _visV = [_ign1, "VIEW", _obj] checkVisibility [_camASL, _probeASL];
            if (_visV < 0.70) then {
                private _hits = lineIntersectsSurfaces [_camASL, _probeASL, _ign1, _obj, true, 4, "VIEW", "FIRE"];
                if ((_hits isNotEqualTo []) && {(_hits findIf {
                    private _ho = _x select 3;
                    if (isNull _ho) then { _ho = _x select 2; };
                    (isNull _ho) || !(_ho isKindOf "CAManBase")
                }) < 0}) then { _visV = 1; };
            };
            _visV
        }
    };

    // Reconstruct the world polylines from the per-capsule [t, c, s] params.
    private _lines = [];
    {
        private _polys = _x;
        private _cIdx = _forEachIndex;
        private _capD = _cd select _cIdx;
        if ((_polys isNotEqualTo []) && (_capD isNotEqualTo [])) then {
            private _zone = 0;
            if (_vis isNotEqualTo []) then {
                private _zoneV = _vis select (_pmap select _cIdx);
                _zone = if (_zoneV >= 0.70) then { 0 } else { if (_zoneV >= 0.35) then { 1 } else { if (_zoneV >= 0.10) then { 2 } else { -1 } } };
            };
            if (_zone >= 0) then {
                private _a3 = _capD select 0;
                private _ab3 = _capD select 1;
                private _n3 = _capD select 2;
                private _e3 = _capD select 3;
                {
                    private _wpts = _x apply {
                        _a3 vectorAdd (_ab3 vectorMultiply (_x select 0))
                            vectorAdd (_n3 vectorMultiply (_x select 1))
                            vectorAdd (_e3 vectorMultiply (_x select 2))
                    };
                    _lines pushBack [_wpts, _zone];
                } forEach _polys;
            };
        };
    } forEach _topo;

    // Widths and colours for this target.
    private _wf = ((sqrt (_h1080 / 120)) max 0.60) min 1;
    private _wc = (_wFull * _wf) max _wMin;
    private _colsC = _colsCore;
    private _colsS = _colsSoft;
    if (_fade < 1) then {
        _colsC = _colsCore apply { [_x select 0, _x select 1, _x select 2, (_x select 3) * _fade] };
        _colsS = _colsSoft apply { [_x select 0, _x select 1, _x select 2, (_x select 3) * _fade] };
    };
    private _doSoft = _h1080 > 160;   // soft underlay only for large silhouettes

    // World polylines -> draw segments (window clip for edge targets).
    private _nBefore = count _core;
    {
        private _wpts = _x select 0;
        private _lineLvl = _x select 1;
        private _colC = _colsC select _lineLvl;
        private _colS = _colsS select _lineLvl;
        if (_fullIn) then {
            private _pv = [];
            {
                private _s = worldToScreen _x;
                private _mp = if ((count _s) < 2) then { [] } else { _mapC ctrlMapScreenToWorld _s };
                if ((_pv isNotEqualTo []) && (_mp isNotEqualTo [])) then {
                    _core pushBack [_pv, _mp, _colC, _wc];
                    if (_doSoft) then { _soft pushBack [_pv, _mp, _colS, _wSoft]; };
                };
                _pv = _mp;
            } forEach _wpts;
        } else {
            private _scr = _wpts apply { worldToScreen _x };
            for "_q" from 0 to ((count _scr) - 2) do {
                private _sa = _scr select _q;
                private _sb = _scr select (_q + 1);
                if (((count _sa) >= 2) && ((count _sb) >= 2)) then {
                    private _sx0 = _sa select 0;
                    private _sy0 = _sa select 1;
                    private _ddx = (_sb select 0) - _sx0;
                    private _ddy = (_sb select 1) - _sy0;
                    private _t0 = 0;
                    private _t1 = 1;
                    {
                        private _lbP = _x select 0;
                        private _lbQ = _x select 1;
                        if (_lbP == 0) then {
                            if (_lbQ < 0) then { _t0 = 2; };
                        } else {
                            private _lbR = _lbQ / _lbP;
                            if (_lbP < 0) then {
                                if (_lbR > _t1) then { _t0 = 2; } else { if (_lbR > _t0) then { _t0 = _lbR; }; };
                            } else {
                                if (_lbR < _t0) then { _t0 = 2; } else { if (_lbR < _t1) then { _t1 = _lbR; }; };
                            };
                        };
                    } forEach [[-_ddx, _sx0 - _bx0], [_ddx, _bx1 - _sx0], [-_ddy, _sy0 - _by0], [_ddy, _by1 - _sy0]];
                    if (_t0 < _t1) then {
                        private _ma = _mapC ctrlMapScreenToWorld [_sx0 + (_ddx * _t0), _sy0 + (_ddy * _t0)];
                        private _mb = _mapC ctrlMapScreenToWorld [_sx0 + (_ddx * _t1), _sy0 + (_ddy * _t1)];
                        _core pushBack [_ma, _mb, _colC, _wc];
                        if (_doSoft) then { _soft pushBack [_ma, _mb, _colS, _wSoft]; };
                    };
                };
            };
        };
    } forEach _lines;

    if ((count _core) > _nBefore) then { _drawn = _drawn + 1; };
} forEach _hot;

["set", _soft + _core] call FUNC(outlineCanvas);

private _logMsg = format [
    "fusion outline %1 ms (targets %2, segments %3, drawn %4, half %5 deg)",
    round ((diag_tickTime - _perfT0) * 1000), count _hot, count (_soft + _core), _drawn, _halfAngleDeg
];
AEE_LOG_DEBUG(_logMsg);
