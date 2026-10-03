#include "..\..\script_component.hpp"
/*
 * Fusion HUD compass tape (issue #204).
 *
 * Draws the scrolling heading tape at the top centre of the fusion box: the
 * big heading number, the fixed centre mark, a three-digit label every 10
 * degrees, a tick every 5 degrees and the cardinal letters N / NE / E / SE /
 * S / SW / W / NW just below the strip.  Ported from workshop 3810296503
 * whale_ecoti_llll functions/fn_drawHUD.sqf; the geometry, the idc layout and
 * the skip-on-no-change cache are the source's.
 *
 * It lives on the UI layer, not in drawLine3D, because the NVG post-process
 * tints the whole 3D world and would wash the amber out; the UI layer is drawn
 * outside the filter (source fn_drawHUD.sqf header).
 *
 * Source data replaced by aee data: the source derived the heading from the
 * positionCameraToWorld pair; this version takes the shared aee eye state
 * FUNC(core,getEyeState), which tracks freelook and vehicle seats the same way.
 * The brightness comes from FUNC(hudTapeBoot)'s QGVAR(hudTapeBootProfile).
 *
 * Returns: nothing.
 */
private _raised = missionNamespace getVariable [QGVAR(hudTapeOn), false];
if !(_raised isEqualType true) then { _raised = false; };
if (!_raised) exitWith {};
if (!hasInterface) exitWith {};

private _disp = uiNamespace getVariable [QGVAR(fusionHudDisplay), displayNull];
if (isNull _disp) exitWith {};

private _hdr = _disp displayCtrl 920001;
if (isNull _hdr) exitWith {};

private _player = call CBA_fnc_currentUnit;
private _head = 0;
if (!isNull _player) then {
    private _state = [_player] call EFUNC(core,getEyeState);
    private _fwd = _state select 1;
    if (_fwd isEqualType [] && {count _fwd isEqualTo 3}) then {
        _head = (((_fwd select 0) atan2 (_fwd select 1)) + 360) mod 360;
    };
};

// Ruler colour, scaled by the power-on / power-off brightness envelope.
private _colBase = FUSION_HUD_RULER_COLOR;
private _colOff = [0, 0, 0, 0];

private _prof = missionNamespace getVariable [QGVAR(hudTapeBootProfile), [1, 1, 1, 0]];
if !(_prof isEqualType []) then { _prof = [1, 1, 1, 0]; };
private _bootK = if ((count _prof) > 0) then { _prof select 0 } else { 1 };
if !(_bootK isEqualType 0) then { _bootK = 1; };

private _col = [
    (_colBase select 0) * _bootK,
    (_colBase select 1) * _bootK,
    (_colBase select 2) * _bootK,
    (_colBase select 3) * _bootK
];

private _scl = FUSION_HUD_SCALE;
private _hudY = FUSION_HUD_Y;

// Skip when the heading, colour and scale are all unchanged.  The raise clears
// the cache, and the brightness envelope changes the colour each animated
// frame, so an animated frame is never skipped.
private _sig = [_col, _scl, _hudY];
private _cache = missionNamespace getVariable [QGVAR(hudTapeCache), []];
if !(_cache isEqualType []) then { _cache = []; };
if ((count _cache) >= 3) then {
    if ((abs (_head - (_cache select 0)) < 0.03) && {(_cache select 2) isEqualTo _sig}) exitWith {};
};
missionNamespace setVariable [QGVAR(hudTapeCache), [_head, true, _sig]];

private _bw = FUSION_HUD_BOX_FRACTION * safeZoneH;
private _bh = FUSION_HUD_BOX_FRACTION * safeZoneH;
private _bx = safeZoneX + safeZoneW / 2 - _bw / 2;
private _by = safeZoneY + safeZoneH / 2 - _bh / 2;
private _cx = _bx + _bw / 2;

private _tapeFr = FUSION_HUD_TAPE_FRACTION;
private _span = FUSION_HUD_TAPE_SPAN;

private _pxPerDeg = (_bw * _tapeFr * _scl) / (2 * _span);
private _lblW = _pxPerDeg * 7;
private _tickW = (_bh * 0.002 * _scl) max 0.0004;
private _hMaj = _bh * 0.018 * _scl;
private _hMin = _bh * 0.011 * _scl;
private _fntBig = _bh * 0.033 * _scl;
private _fntSml = _bh * 0.022 * _scl;

private _yHead = _by + _bh * _hudY;
private _yLbl = _yHead + _bh * (0.070 * _scl);
private _yTick = _yHead + _bh * (0.120 * _scl);

// The font is re-applied on every refresh.  A cutRsc rebuild resets the
// controls to the config font, and a value-unchanged skip would then leave the
// tape at the config's small size forever (source fn_drawHUD.sqf).
_hdr ctrlSetFontHeight _fntBig;
_hdr ctrlCommit 0;
for "_i" from 0 to 12 do {
    private _lc = _disp displayCtrl (920011 + _i);
    if (!isNull _lc) then {
        _lc ctrlSetFontHeight _fntSml;
        _lc ctrlCommit 0;
    };
};
private _fntDir = _fntSml * 1.15;
for "_i" from 0 to 7 do {
    private _lc = _disp displayCtrl (920061 + _i);
    if (!isNull _lc) then {
        _lc ctrlSetFontHeight _fntDir;
        _lc ctrlCommit 0;
    };
};

// The big heading number, full width and centred, so it lands on the box axis.
private _h3 = (round _head) mod 360;
private _hStr = format ["%1", _h3];
if (_h3 < 10) then { _hStr = format ["00%1", _h3]; } else { if (_h3 < 100) then { _hStr = format ["0%1", _h3]; }; };
private _deg = toString [176];

_hdr ctrlSetPosition [safeZoneX, _yHead, safeZoneW, _bh * 0.070 * _scl];
_hdr ctrlSetText format ["%1%2M", _hStr, _deg];
_hdr ctrlSetTextColor _col;
_hdr ctrlCommit 0;

// The fixed centre mark.
private _mk = _disp displayCtrl 920002;
if (!isNull _mk) then {
    _mk ctrlSetPosition [_cx - _tickW * 0.9, _yTick - _bh * 0.005 * _scl, _tickW * 1.8, _hMaj * 1.4];
    _mk ctrlSetBackgroundColor _col;
    _mk ctrlCommit 0;
};

// The 13 ten-degree labels.
private _base10 = (round (_head / 10)) * 10;
for "_i" from 0 to 12 do {
    private _c = _disp displayCtrl (920011 + _i);
    if (!isNull _c) then {
        private _a = _base10 + (_i - 6) * 10;
        private _aw = ((_a mod 360) + 360) mod 360;
        private _dx = (_a - _head) * _pxPerDeg;
        private _s = format ["%1", _aw];
        if (_aw < 10) then { _s = format ["00%1", _aw]; } else { if (_aw < 100) then { _s = format ["0%1", _aw]; }; };
        _c ctrlSetPosition [_cx + _dx - _lblW / 2, _yLbl, _lblW, _bh * 0.045 * _scl];
        _c ctrlSetText _s;
        _c ctrlSetTextColor _col;
        _c ctrlCommit 0;
    };
};

// The 25 five-degree ticks; a ten-degree tick is taller.
private _base5 = (round (_head / 5)) * 5;
for "_i" from 0 to 24 do {
    private _c = _disp displayCtrl (920031 + _i);
    if (!isNull _c) then {
        private _a = _base5 + (_i - 12) * 5;
        private _dx = (_a - _head) * _pxPerDeg;
        private _h = [_hMin, _hMaj] select ((((_a mod 10) + 10) mod 10) == 0);
        _c ctrlSetPosition [_cx + _dx - _tickW / 2, _yTick, _tickW, _h];
        _c ctrlSetBackgroundColor _col;
        _c ctrlCommit 0;
    };
};

// The cardinal letters, just below the tick strip.  The nearest equivalent
// angle is taken first so a round to 360 does not jump the north letter.
private _dirs = [[0, "N"], [45, "NE"], [90, "E"], [135, "SE"], [180, "S"], [225, "SW"], [270, "W"], [315, "NW"]];
private _yDir = _yTick + _hMaj + _bh * 0.006 * _scl;
private _halfD = _pxPerDeg * _span;
for "_i" from 0 to 7 do {
    private _c = _disp displayCtrl (920061 + _i);
    if (!isNull _c) then {
        private _da = (_dirs select _i) select 0;
        private _aa = _da + (round ((_head - _da) / 360)) * 360;
        private _dx = (_aa - _head) * _pxPerDeg;
        if (abs _dx <= _halfD) then {
            _c ctrlSetPosition [_cx + _dx - _lblW / 2, _yDir, _lblW, _bh * 0.052 * _scl];
            _c ctrlSetText ((_dirs select _i) select 1);
            _c ctrlSetTextColor _col;
        } else {
            _c ctrlSetText "";
            _c ctrlSetTextColor _colOff;
        };
        _c ctrlCommit 0;
    };
};
