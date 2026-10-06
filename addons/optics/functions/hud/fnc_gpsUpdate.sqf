#include "..\..\script_component.hpp"
/*
 * MGRS GPS device readout per-tick update.
 *
 * Runs from the CBA per-frame handler started in XEH_postInit.  The readout
 * appears only when the player carries an ItemGPS and the
 * aee_optics_mgrsEnabled setting is on.  The engine GPS readout is fixed, so
 * this is the aee MGRS surface for the device.
 *
 * The fix quality and the error radius are read from the tracker driver
 * (task 13).  Before the tracker runs they show an explicit unknown, never an
 * invented value.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};

private _enabled = missionNamespace getVariable [QGVAR(mgrsEnabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };

private _player = call CBA_fnc_currentUnit;
private _hasGps = ("ItemGPS" in (assignedItems _player)) || ("ItemGPS" in (items _player));

private _show = _enabled && alive _player && _hasGps;
if (!_show) exitWith {
    if (missionNamespace getVariable [QGVAR(gpsOn), false]) then {
        [false] call FUNC(gpsBuild);
    };
};

[true] call FUNC(gpsBuild);

private _display = uiNamespace getVariable [QGVAR(gpsDisplay), displayNull];
if (isNull _display) exitWith {};

private _anchor = call EFUNC(core,getGeoAnchor);
private _precision = missionNamespace getVariable [QGVAR(mgrsPrecision), 10];
if !(_precision isEqualType 0) then { _precision = 10; };

private _grid = ["", getPos _player, _anchor, _precision] call FUNC(mgrsMarkerText);

private _setText = {
    params ["_display", "_idc", "_text"];
    disableSerialization;
    private _ctrl = _display displayCtrl _idc;
    if (!isNull _ctrl) then { _ctrl ctrlSetText _text; };
};

// The fix quality and the error radius come from the signal-dependent tracker
// driver (task 13).  They read an explicit unknown until the tracker runs, so
// the readout never shows an invented value.
private _fix = missionNamespace getVariable [QGVAR(trackerFix), "--"];
if !(_fix isEqualType "") then { _fix = "--"; };
private _r95 = missionNamespace getVariable [QGVAR(trackerR95), 0];
if !(_r95 isEqualType 0) then { _r95 = 0; };

[_display, 9020, _grid] call _setText;
[_display, 9021, "PREC " + (str _precision) + " DIGITS"] call _setText;
[_display, 9022, "FIX " + (toUpper _fix)] call _setText;
[_display, 9023, "ERR " + (str (round _r95)) + " m"] call _setText;
