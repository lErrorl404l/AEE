#include "..\..\script_component.hpp"
/*
 * Fusion HUD corner readouts (issue #204).
 *
 * Fills the two corner lines inside the fusion box and the environment line
 * below them.  The layout is ported from workshop 3810296503 whale_ecoti_llll
 * functions/fn_drawInfo.sqf, which placed a position line top-left and a clock
 * top-right and ran on the source's 0.1 s loop (a time and a position do not
 * need a per-frame refresh).
 *
 * Source data replaced by aee data: the source derived an invented latitude and
 * longitude from the map's config origin; this version prints the engine grid
 * from mapGridPosition and the ASL height from getPosASL.  The clock uses
 * dayTime (source used daytime).  The environment line reads the aee state:
 * currentTemperature, currentHumidity, currentWindStr and currentWindDir.
 *
 * Returns: nothing.
 */
private _raised = missionNamespace getVariable [QGVAR(hudTapeOn), false];
if !(_raised isEqualType true) then { _raised = false; };
if (!_raised) exitWith {};
if (!hasInterface) exitWith {};

private _disp = uiNamespace getVariable [QGVAR(fusionHudDisplay), displayNull];
if (isNull _disp) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNull _player) exitWith {};

private _prof = missionNamespace getVariable [QGVAR(hudTapeBootProfile), [1, 1, 1, 0]];
if !(_prof isEqualType []) then { _prof = [1, 1, 1, 0]; };
private _infoK = if ((count _prof) > 2) then { _prof select 2 } else { 1 };
if !(_infoK isEqualType 0) then { _infoK = 1; };

private _base = FUSION_HUD_INFO_COLOR;
private _col = [
    (_base select 0) * _infoK,
    (_base select 1) * _infoK,
    (_base select 2) * _infoK,
    (_base select 3) * _infoK
];

private _bw = FUSION_HUD_BOX_FRACTION * safeZoneH;
private _bx = safeZoneX + safeZoneW / 2 - _bw / 2;
private _by = safeZoneY + safeZoneH / 2 - _bw / 2;

private _uiSz = 0.014;
private _uiH = _uiSz * 2.4;
private _uiW = _bw * 0.85;
private _edge = _uiSz * 0.5;
private _yTop = _by + _edge;
private _xL = _bx + _edge;
private _xR = _bx + _bw - _edge - _uiW;

// Top left: the grid square and the ASL height.
private _pc = _disp displayCtrl 920102;
if (!isNull _pc) then {
    _pc ctrlSetPosition [_xL, _yTop, _uiW, _uiH];
    _pc ctrlSetFontHeight _uiSz;
    private _grid = mapGridPosition _player;
    private _alt = round ((getPosASL _player) select 2);
    _pc ctrlSetText format ["%1 %2m", _grid, _alt];
    _pc ctrlSetTextColor _col;
    _pc ctrlCommit 0;
};

// Under it: the aee environment state.
private _ec = _disp displayCtrl 920103;
if (!isNull _ec) then {
    _ec ctrlSetPosition [_xL, _yTop + _uiH, _uiW, _uiH];
    _ec ctrlSetFontHeight _uiSz;
    private _temperature = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
    private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
    private _windStr = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
    private _windDir = missionNamespace getVariable [QEGVAR(core,currentWindDir), 0];
    if !(_temperature isEqualType 0) then { _temperature = 15; };
    if !(_humidity isEqualType 0) then { _humidity = 50; };
    if !(_windStr isEqualType 0) then { _windStr = 0; };
    if !(_windDir isEqualType 0) then { _windDir = 0; };
    _ec ctrlSetText format ["T%1C RH%2 W%3@%4", round _temperature, round _humidity, round _windStr, round _windDir];
    _ec ctrlSetTextColor _col;
    _ec ctrlCommit 0;
};

// Top right: the clock as HHMM, the source's layout.
private _tc = _disp displayCtrl 920101;
if (!isNull _tc) then {
    _tc ctrlSetPosition [_xR, _yTop, _uiW, _uiH];
    _tc ctrlSetFontHeight _uiSz;
    private _day = dayTime;
    private _hh = floor _day;
    private _mm = floor ((_day - _hh) * 60);
    if (_hh < 0) then { _hh = 0; };
    if (_hh > 23) then { _hh = 23; };
    if (_mm < 0) then { _mm = 0; };
    if (_mm > 59) then { _mm = 59; };
    private _h2 = if (_hh < 10) then { format ["0%1", _hh] } else { format ["%1", _hh] };
    private _m2 = if (_mm < 10) then { format ["0%1", _mm] } else { format ["%1", _mm] };
    _tc ctrlSetText format ["%1%2", _h2, _m2];
    _tc ctrlSetTextColor _col;
    _tc ctrlCommit 0;
};
