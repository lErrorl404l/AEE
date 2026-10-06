#include "..\..\script_component.hpp"
// The ownership tag an AEE marker carries.  AEE ships no marker today, so the
// overlay labels the player position; a tagged marker is labelled read-only.
#define MGRS_MARKER_TAG "AEE"
/*
 * ECOTI MGRS map overlay.
 *
 * Registers one Draw handler on the engine map control (RscMapControl, the
 * main map display) and labels the player position and the AEE-owned markers
 * with their MGRS reference.  The handler is read-only: it creates no marker
 * and edits none.  The player's engine mapGridPosition is read as a
 * cross-check and shown when the aee MGRS conversion yields nothing.
 *
 * The map control exists only while the map is open, so the Draw handler is
 * attached from the "Map" mission event on open.  The handler technique
 * follows addons/thermal/functions/outline/fnc_outlineCanvas.sqf:47.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};
if (!isNil QGVAR(mgrsMapEH)) exitWith {};

GVAR(mgrsMapEH) = addMissionEventHandler ["Map", {
    params ["_opened"];
    if (!_opened) exitWith {};

    private _display = findDisplay 12;
    if (isNull _display) exitWith {};
    private _mapCtrl = _display displayCtrl 51;
    if (isNull _mapCtrl) exitWith {};
    if (_mapCtrl getVariable [QGVAR(mgrsMapReady), false]) exitWith {};

    _mapCtrl ctrlAddEventHandler ["Draw", {
        params ["_map"];
        if (!(missionNamespace getVariable [QGVAR(mgrsEnabled), true])) exitWith {};

        private _anchor = call EFUNC(core,getGeoAnchor);
        private _precision = missionNamespace getVariable [QGVAR(mgrsPrecision), 10];
        private _player = call CBA_fnc_currentUnit;

        // The engine grid is the cross-check: FUNC(mgrsMarkerText) shows it
        // when the aee MGRS conversion yields nothing.
        private _playerText = [
            mapGridPosition _player,
            getPos _player,
            _anchor,
            _precision
        ] call FUNC(mgrsMarkerText);
        _map drawIcon [
            "", [0.75, 1, 1, 1], getPos _player, 0, 0, 0,
            _playerText, 1, 0.024, "PuristaMedium", "center"
        ];

        {
            private _text = markerText _x;
            if ((_text select [0, 3]) == MGRS_MARKER_TAG) then {
                private _label = [
                    _text,
                    getMarkerPos _x,
                    _anchor,
                    _precision
                ] call FUNC(mgrsMarkerText);
                _map drawIcon [
                    "", [0.75, 1, 1, 0.9], getMarkerPos _x, 0, 0, 0,
                    _label, 1, 0.020, "PuristaMedium", "center"
                ];
            };
        } forEach allMapMarkers;
    }];

    _mapCtrl setVariable [QGVAR(mgrsMapReady), true];
}];
