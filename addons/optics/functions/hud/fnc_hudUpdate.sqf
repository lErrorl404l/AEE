#include "..\..\script_component.hpp"
/*
 * ECOTI environment HUD per-tick update.
 *
 * Runs from the CBA per-frame handler started in XEH_postInit.  The HUD is
 * an operator aid and the CBA setting aee_optics_hudEnabled defaults OFF.
 * Each tick reads that setting once, raises or clears the display, and, when
 * it is up, writes the aee environment state into the text controls.
 *
 * Ported from workshop 3759527903 FPANO_ECOTI/scripts/FPANO_fnc_hud.sqf.
 * The source reads ambientTemperature and its own trackers; this version
 * reads the aee environment state instead (currentTemperature, currentHumidity,
 * currentWindStr, currentWindDir) and the aee eye-state foundation for the
 * camera bearing.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};

private _enabled = missionNamespace getVariable [QGVAR(hudEnabled), false];
if !(_enabled isEqualType true) then { _enabled = false; };

if (_enabled) then {
    private _player = call CBA_fnc_currentUnit;
    private _show = alive _player
        && {!visibleMap}
        && {(currentVisionMode _player) == 1};
    if (!_show) exitWith {
        [false] call FUNC(hudBuild);
    };

    [true] call FUNC(hudBuild);

    private _display = uiNamespace getVariable [QGVAR(hudDisplay), displayNull];
    if (isNull _display) exitWith {};

    // Camera bearing: the aee eye-state forward vector, resolved against the
    // live camera so it tracks freelook and vehicle seats (source used the
    // camera position pair directly).
    private _state = [_player] call EFUNC(core,getEyeState);
    private _forward = _state select 1;
    private _bearing = 0;
    if (_forward isEqualType [] && count _forward isEqualTo 3) then {
        _bearing = (_forward select 0) atan2 (_forward select 1);
        if (_bearing < 0) then { _bearing = _bearing + 360; };
    };
    private _heading = [(_bearing mod 360)] call FUNC(hudFormatHeading);

    // The grid line: an MGRS reference when the setting is on, else the
    // legacy numeric grid.  FUNC(formatGridDisplay) owns that choice; the
    // position, the anchor and the setting value are all passed in.
    private _mgrsEnabled = missionNamespace getVariable [QGVAR(mgrsEnabled), true];
    if !(_mgrsEnabled isEqualType true) then { _mgrsEnabled = true; };
    private _mgrsPrecision = missionNamespace getVariable [QGVAR(mgrsPrecision), 10];
    if !(_mgrsPrecision isEqualType 0) then { _mgrsPrecision = 10; };

    private _grid = [
        getPosASL _player,
        call EFUNC(core,getGeoAnchor),
        _mgrsPrecision,
        mapGridPosition _player,
        _mgrsEnabled
    ] call FUNC(formatGridDisplay);
    private _altitude = round ((getPosASL _player) select 2);
    private _clock = [dayTime, "HH:MM"] call BIS_fnc_timeToString;

    private _temperature = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
    private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
    private _windStr = missionNamespace getVariable [QEGVAR(core,currentWindStr), 0];
    private _windDir = missionNamespace getVariable [QEGVAR(core,currentWindDir), 0];

    private _setText = {
        params ["_display", "_idc", "_text"];
        disableSerialization;
        private _ctrl = _display displayCtrl _idc;
        if (!isNull _ctrl) then { _ctrl ctrlSetText _text; };
    };

    [_display, 9010, _heading select 0] call _setText;
    [_display, 9003, _heading select 1] call _setText;
    [_display, 9015, _grid] call _setText;
    [_display, 9005, (str _altitude) + "m"] call _setText;
    [_display, 9006, _clock] call _setText;
    [_display, 9012, (str _temperature) + " C"] call _setText;
    [_display, 9013, "RH " + (str (round _humidity))] call _setText;
    [_display, 9014, "WIND " + (str (round _windStr)) + " m/s " + (str (round _windDir))] call _setText;

    // One update line per window, through AEE_LOG_DEBUG (the module trace
    // switch), so the HUD can be read in an .rpt without a per-frame cost.
    // It names the gate state and a few of the values it just published.
    private _logAt = missionNamespace getVariable [QGVAR(hudLogAt), -1e9];
    if !(_logAt isEqualType 0) then { _logAt = -1e9; };
    if (diag_tickTime >= _logAt) then {
        missionNamespace setVariable [QGVAR(hudLogAt), diag_tickTime + 5];
        private _logMsg = format [
            "environment HUD update: enabled=%1 show=%2 bearing=%3 grid=%4 alt=%5 temp=%6 hum=%7 wind=%8",
            _enabled, _show, round _bearing, _grid, _altitude, _temperature,
            round _humidity, round _windStr
        ];
        AEE_LOG_DEBUG(_logMsg);
    };
} else {
    if (missionNamespace getVariable [QGVAR(hudOn), false]) then {
        [false] call FUNC(hudBuild);
    };
};
