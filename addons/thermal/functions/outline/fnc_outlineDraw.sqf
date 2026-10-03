#include "..\..\script_component.hpp"
/*
 * Per-frame fusion outline worker (issue #204).
 *
 * Structure ported from workshop 3811605241 whale_ecoti_llll
 * functions/fn_drawOutlines.sqf: a transparent canvas (FUNC(outlineCanvas)),
 * the convex hull of projected skeleton points (FUNC(outlineHull)), the
 * sensor-resolution level of detail (FUNC(outlineSensorLod)) and a body
 * skeleton read from the model's selection memory points.
 *
 * THIS SLICE draws each hot target as the hull of its projected skeleton
 * points, inflated slightly by the sensor blur term.  The source's
 * capsule-union organic silhouette (fn_outlineTopo) and its occlusion
 * raycasts are the source's refinement and are QUEUED; they are not ported
 * here.  A correct smaller slice beats a broken larger one.
 *
 * aee drives it: the hot list is FUNC(outlineCollect) (aee selTemperature
 * against ambient), and the field gate is FUNC(fusionFovGate) with the
 * half-angle FUNC(resolveFusionDevice) resolved for the mounted headset.  No
 * field of view is hardcoded.
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

// The hot list is aee's own thermal state and self-caches for 0.25 s.
private _hot = [] call FUNC(outlineCollect);

// The device pair carries the thermal channel half-angle; the gate uses it.
private _pair = [_player] call FUNC(resolveFusionDevice);
private _halfAngleDeg = _pair select 2;
if !(_halfAngleDeg isEqualType 0) then { _halfAngleDeg = 20; };
if (_halfAngleDeg <= 0) then { _halfAngleDeg = 20; };

private _eyeState = [_player] call EFUNC(core,getEyeState);
private _eye = _eyeState select 0;
private _viewDir = _eyeState select 1;

// The sensor detector resolution.  The source's default is 240 lines, and no
// published ECOTI detector line count is in the corpus (the sheet gives the
// 640x480 array, not the display line count), so the source default stands.
private _sensRes = 240;

// Capability independent of the target: the camera field calibrated from two
// worldToScreen probes, exactly the source's method.  It converts the sensor
// blur term from metres at range to screen units.
private _p1 = worldToScreen (positionCameraToWorld [0, 0, 100]);
private _p2 = worldToScreen (positionCameraToWorld [0, 1, 100]);
private _kY = 0;
if ((count _p1) >= 2 && (count _p2) >= 2) then {
    _kY = (abs ((_p2 select 1) - (_p1 select 1))) / 0.01;
};
if (_kY <= 0) then { _kY = 1.2; };

private _resY = (getResolution select 1) max 1;
private _width = 2 * (_resY / 1080);
private _colour = [1.00, 0.41, 0.10, 0.55];
private _skeleton = call FUNC(outlineSkeleton);

private _segments = [];
private _drawn = 0;

{
    private _obj = _x;
    if (isNull _obj) then { continue };

    // Ours, not the source's: the target must sit inside the resolved thermal
    // channel.  FUNC(fusionFovGate) is the same gate the emissive overlay uses.
    private _objPos = getPosASLVisual _obj;
    if !([_eye, _viewDir, _objPos, _halfAngleDeg] call FUNC(fusionFovGate)) then { continue };

    private _dist = _eye vectorDistance _objPos;
    // Metres one detector pixel covers at this range, and the target height in
    // sensor pixels.  The 1.8 m body height is the source's value.
    private _mpp = ((_dist max 0.5) * 2 * (tan _halfAngleDeg)) / _sensRes;
    private _hSens = 1.8 / (_mpp max 1e-6);
    private _lod = [_hSens] call FUNC(outlineSensorLod);
    private _bones = _skeleton select _lod;

    private _screenPts = [];
    {
        private _sp = _obj selectionPosition _x;
        if (_sp isNotEqualTo [0, 0, 0]) then {
            private _w = _obj modelToWorldVisual _sp;
            private _s = worldToScreen _w;
            if ((count _s) >= 2) then { _screenPts pushBack _s; };
        };
    } forEach _bones;

    if ((count _screenPts) < 3) then { continue };

    private _idx = [_screenPts] call FUNC(outlineHull);
    if ((count _idx) < 3) then { continue };

    private _poly = [];
    { _poly pushBack (_screenPts select _x); } forEach _idx;

    // Inflate outward from the screen centroid by the sensor blur, converted
    // from metres at range to screen units by the calibrated _kY.
    private _infl = (_mpp * 0.5) min 0.12;
    private _inflZone = (_infl * _kY) / (_dist max 0.5);
    private _cx = 0;
    private _cy = 0;
    { _cx = _cx + (_x select 0); _cy = _cy + (_x select 1); } forEach _poly;
    private _n = count _poly;
    _cx = _cx / _n;
    _cy = _cy / _n;

    private _canvas = [];
    {
        private _dx = (_x select 0) - _cx;
        private _dy = (_x select 1) - _cy;
        private _len = sqrt ((_dx * _dx) + (_dy * _dy));
        if (_len > 1e-6) then {
            _dx = _dx / _len;
            _dy = _dy / _len;
        } else {
            _dx = 0;
            _dy = 0;
        };
        _canvas pushBack (_mapC ctrlMapScreenToWorld [(_x select 0) + (_dx * _inflZone), (_x select 1) + (_dy * _inflZone)]);
    } forEach _poly;

    private _m = count _canvas;
    {
        private _b = _canvas select ((_forEachIndex + 1) mod _m);
        if ((_x isNotEqualTo []) && (_b isNotEqualTo [])) then {
            _segments pushBack [_x, _b, _colour, _width];
        };
    } forEach _canvas;

    _drawn = _drawn + 1;
} forEach _hot;

["set", _segments] call FUNC(outlineCanvas);

private _logMsg = format [
    "fusion outline %1 ms (targets %2, drawn %3, segments %4)",
    round ((diag_tickTime - _perfT0) * 1000), count _hot, _drawn, count _segments
];
AEE_LOG_DEBUG(_logMsg);
