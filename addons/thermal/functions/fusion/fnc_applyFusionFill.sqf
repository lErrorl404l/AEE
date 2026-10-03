#include "..\..\script_component.hpp"
/*
 * Solid thermal fill (issue #204, Track B ENVG-B).
 *
 * Ported from workshop 3810296503 whale_ecoti_llll functions/fn_thermalFill.sqf,
 * the improved version.  Workshop 3809860654 whale_ecoti_lll ships the earlier
 * one, which repaints every target regardless of the view and flickers.  The
 * mechanism is the engine's own: save each texture slot of a hot body, paint
 * one solid bright colour (#(rgb,8,8,3)color(r,g,b,1.0)) into every slot, then
 * restore the saved textures when the body leaves.  It is a client-local
 * setObjectTexture, so it does not sync and does not write a save.
 *
 * The source's driving data is replaced, and the replacement is the point:
 *   - the hot list is FUNC(outlineCollect), aee's own QGVAR(selTemperature)
 *     against the ambient air temperature, not the source's CAManBase-only
 *     fn_collectHot;
 *   - the field is FUNC(fusionFovGate) at the half-angle FUNC(resolveFusionDevice)
 *     resolves for the mounted headset, not the source's HUD box list.
 * The source's save/restore registry, colour-change repaint and per-pass
 * signature cache are kept as they are.
 *
 * COMPOSITION WITH THE EMISSIVE LADDER.  This fill is a display MODE, selected
 * by QGVAR(fusionSolidFill).  FUNC(applyFusionOverlay) owns the fused display:
 * when the setting is on it hands the display to this function and skips the
 * 256-band emissive ladder, so one body is never painted by both primitives.
 * The fill registry is separate from QGVAR(fusionOverlaySaved), and the
 * overlay EXIT path restores this one with mode "EXIT".
 *
 * Params:
 *   0: _player (OBJECT, default player).
 *   1: _mode (STRING, default "") - "EXIT" restores every body and clears.
 *
 * Returns: nothing.
 */
params [["_player", player, [objNull]], ["_mode", "", [""]]];

if (!hasInterface) exitWith {};

private _reg = missionNamespace getVariable [QGVAR(fusionFillReg), []];
if !(_reg isEqualType []) then { _reg = []; };

// Restore path.  The overlay EXIT calls this with "EXIT".  The restore is
// unconditional and does not need a live player, so it runs even when the
// sensor session is already gone.
if (_mode == "EXIT") exitWith {
    {
        _x params ["_o", "_saved"];
        if (!isNull _o) then {
            {
                if (_x isNotEqualTo "") then { _o setObjectTexture [_forEachIndex, _x]; };
            } forEach _saved;
        };
    } forEach _reg;
    missionNamespace setVariable [QGVAR(fusionFillReg), []];
    missionNamespace setVariable [QGVAR(fusionFillSig), []];
    if ((count _reg) > 0) then {
        private _logMsg = format ["fusion fill: restored %1 bodies on exit", count _reg];
        AEE_LOG_DEBUG(_logMsg);
    };
};

if (isNull _player) exitWith {};

private _settingOn = missionNamespace getVariable [QGVAR(fusionSolidFill), false];
if !(_settingOn isEqualType true) then { _settingOn = false; };
private _fusionMode = missionNamespace getVariable [QGVAR(fusionMode), 0];
if !(_fusionMode isEqualType 0) then { _fusionMode = 0; };
private _want = _settingOn && _fusionMode == 1;

// The hot list, nearest first.  FUNC(outlineCollect) caches its per-object
// verdict for 0.25 s, so the selection walk does not run on every call.
private _hot = if (_want) then { [] call FUNC(outlineCollect) } else { [] };

// The field.  The eye and the look vector are the same cached eye state the
// outline and the overlay use, so the fill agrees with them on where the
// operator looks.  Nothing is painted outside the thermal channel.
private _vis = [];
if (_want && {_hot isNotEqualTo []}) then {
    private _eyeState = [_player] call EFUNC(core,getEyeState);
    private _eye = _eyeState select 0;
    private _viewDir = _eyeState select 1;
    if !(_viewDir isEqualType [] && {count _viewDir == 3}) then { _viewDir = vectorDir _player; };
    private _devicePair = [_player] call FUNC(resolveFusionDevice);
    private _halfAngleDeg = _devicePair select 2;
    if !(_halfAngleDeg isEqualType 0) then { _halfAngleDeg = 20; };
    if (_halfAngleDeg <= 0) then { _halfAngleDeg = 20; };
    {
        if (!isNull _x) then {
            if ([_eye, _viewDir, getPosASLVisual _x, _halfAngleDeg] call FUNC(fusionFovGate)) then {
                _vis pushBack _x;
            };
        };
    } forEach _hot;
};

// The solid colour is the source's outline colour, RGB only: the source writes
// alpha 1.0.  It matches the outline core in FUNC(outlineDraw).
private _col = [1.00, 0.41, 0.10];
private _tex = format ["#(rgb,8,8,3)color(%1, %2, %3, 1.0)", _col select 0, _col select 1, _col select 2];

// Diagnostic window, timed on diag_tickTime so the first call always logs.
private _LOG_INTERVAL = 30;
private _logAt = missionNamespace getVariable [QGVAR(fusionFillLogAt), -1e9];
if !(_logAt isEqualType 0) then { _logAt = -1e9; };
private _logNow = diag_tickTime >= _logAt;
if (_logNow) then {
    missionNamespace setVariable [QGVAR(fusionFillLogAt), diag_tickTime + _LOG_INTERVAL];
};

// Per-pass signature cache, copied from the source's fillSig.  The engine
// compares the whole pair in C++, so a pass with no body entering or leaving
// the field and no colour change skips every loop below.
private _sig = [_tex, _vis];
private _lastSig = missionNamespace getVariable [QGVAR(fusionFillSig), []];
if !(_lastSig isEqualType []) then { _lastSig = []; };
if (_sig isEqualTo _lastSig) exitWith {
    if (_logNow) then {
        private _logStable = format [
            "fusion fill: stable (mode=%1 lit=%2 inField=%3)", _fusionMode, count _reg, count _vis
        ];
        AEE_LOG_DEBUG(_logStable);
    };
};
missionNamespace setVariable [QGVAR(fusionFillSig), _sig];

// A colour change repaints the bodies already lit, so they follow it.  The
// original textures stay in the registry, so the restore is always available.
private _applied = missionNamespace getVariable [QGVAR(fusionFillTexApplied), ""];
if !(_applied isEqualType "") then { _applied = ""; };
private _recolor = _want && _applied isNotEqualTo _tex;
if (_want) then { missionNamespace setVariable [QGVAR(fusionFillTexApplied), _tex]; };

// The bodies already lit, flattened once.  "Is this body already lit" is then
// one engine-side find, not a nested SQF loop.
private _lit = [];
{ _lit pushBack (_x select 0); } forEach _reg;

private _keep = [];

// Pass 1: a registered body that left the field is restored at once.  A body
// that is still in the field is kept, and repainted only when the colour moved.
{
    _x params ["_o", "_saved"];
    private _stillHot = _want && {!isNull _o} && {(_vis find _o) >= 0};
    if (_stillHot) then {
        _keep pushBack [_o, _saved];
        if (_recolor) then {
            for "_i" from 0 to ((count _saved) - 1) do {
                _o setObjectTexture [_i, _tex];
            };
        };
    } else {
        if (!isNull _o) then {
            {
                if (_x isNotEqualTo "") then { _o setObjectTexture [_forEachIndex, _x]; };
            } forEach _saved;
        };
    };
} forEach _reg;

// Pass 2: a body that entered the field is saved and painted.  The slot count
// is the larger of the live textures and the config defaults, with the
// source's 12 for a man and 8 for anything else when both are empty.
if (_want) then {
    {
        private _o = _x;
        if (!isNull _o && {(_lit find _o) < 0}) then {
            private _cur = getObjectTextures _o;
            private _def = getArray (configOf _o >> "hiddenSelectionsTextures");
            private _n = count _cur;
            if ((count _def) > _n) then { _n = count _def; };
            if (_n <= 0) then {
                _n = [8, 12] select (_o isKindOf "CAManBase");
            };
            private _saved = [];
            for "_i" from 0 to (_n - 1) do {
                private _s = "";
                if (_i < count _cur) then { _s = _cur select _i; };
                if ((_s isEqualTo "") && {_i < count _def}) then { _s = _def select _i; };
                _saved pushBack _s;
                _o setObjectTexture [_i, _tex];
            };
            _keep pushBack [_o, _saved];
        };
    } forEach _vis;
};

missionNamespace setVariable [QGVAR(fusionFillReg), _keep];

if (_logNow) then {
    private _logMsg = format [
        "fusion fill: mode=%1 want=%2 hot=%3 inField=%4 lit=%5",
        _fusionMode, _want, count _hot, count _vis, count _keep
    ];
    AEE_LOG_DEBUG(_logMsg);
};
