#include "..\..\script_component.hpp"
// The ownership tag an AEE marker carries.  AEE ships no marker today, so the
// overlay labels the player position; a tagged marker is labelled read-only.
#define MGRS_MARKER_TAG "AEE"
/*
 * ECOTI MGRS map overlay.
 *
 * Registers one Draw handler on the engine map control (RscMapControl, the
 * main map display).  The handler is read-only: it creates no marker and
 * edits none.  It draws four things:
 *
 *   1. the MGRS grid overlay, at a decimal interval chosen for the zoom;
 *   2. the cursor readout, our MGRS reference and terrain elevation;
 *   3. the player position, labelled with its MGRS reference;
 *   4. each AEE-owned marker, labelled with its MGRS reference.
 *
 * The engine map grid stays numeric.  The CfgWorlds Grid class formats
 * numbers only and no script command writes it, so the overlay draws the
 * MGRS lines over it.  The vanilla cursor tooltip is engine-side and cannot
 * be replaced, so the cursor readout is drawn adjacent to it.  The player's
 * engine mapGridPosition is read as a cross-check and shown when the aee
 * MGRS conversion yields nothing.
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

        // ── MGRS grid overlay ─────────────────────────────────────────
        // The engine grid cannot carry MGRS, so this draws our own lines
        // and labels over it.  The plan is cached on the rounded visible
        // rectangle, so a static map does not re-run the conversion on
        // every draw.
        if (missionNamespace getVariable [QGVAR(mgrsMapGrid), true]) then {
            private _cp = ctrlPosition _map;
            private _c0 = _map ctrlMapScreenToWorld [_cp select 0, _cp select 1];
            private _c1 = _map ctrlMapScreenToWorld [
                (_cp select 0) + (_cp select 2),
                (_cp select 1) + (_cp select 3)
            ];
            if (((count _c0) >= 2) && ((count _c1) >= 2)) then {
                private _rect = [
                    (_c0 select 0) min (_c1 select 0),
                    (_c0 select 1) min (_c1 select 1),
                    (_c0 select 0) max (_c1 select 0),
                    (_c0 select 1) max (_c1 select 1)
                ];
                private _key = _rect apply { round (_x / 10) };
                private _cache = missionNamespace getVariable [QGVAR(mgrsGridCache), []];
                if ((count _cache) != 2 || ((_cache select 0) isNotEqualTo _key)) then {
                    _cache = [_key, [_anchor, _rect] call FUNC(mgrsGridLines)];
                    missionNamespace setVariable [QGVAR(mgrsGridCache), _cache];
                };
                private _plan = _cache select 1;
                _plan params ["_segments", "_labels"];
                {
                    _x params ["_pA", "_pB", "_major"];
                    private _colour = [0.45, 0.95, 0.95, 0.30];
                    private _width = 1;
                    if (_major) then {
                        _colour = [0.45, 0.95, 0.95, 0.55];
                        _width = 2;
                    };
                    _map drawLine [_pA, _pB, _colour, _width];
                } forEach _segments;
                {
                    _x params ["_pos", "_label", "_major"];
                    private _size = 0.018;
                    if (_major) then { _size = 0.022; };
                    _map drawIcon [
                        "", [0.60, 1, 1, 0.85], _pos, 0, 0, 0,
                        _label, 1, _size, "PuristaMedium", "center"
                    ];
                } forEach _labels;
            };
        };

        // ── Cursor readout ────────────────────────────────────────────
        // The vanilla cursor tooltip is engine-side and cannot be
        // replaced, so this readout is drawn adjacent to the cursor.
        if (missionNamespace getVariable [QGVAR(mgrsCursorReadout), true]) then {
            private _mouse = getMousePosition;
            private _cp = ctrlPosition _map;
            if ((_mouse select 0) >= (_cp select 0)
                && ((_mouse select 0) <= ((_cp select 0) + (_cp select 2)))
                && ((_mouse select 1) >= (_cp select 1))
                && ((_mouse select 1) <= ((_cp select 1) + (_cp select 3)))) then {
                private _world = _map ctrlMapScreenToWorld _mouse;
                if ((count _world) >= 2) then {
                    private _ref = [
                        "",
                        [_world select 0, _world select 1, 0],
                        _anchor,
                        _precision
                    ] call FUNC(mgrsMarkerText);
                    private _elev = getTerrainHeightASL [_world select 0, _world select 1];
                    private _cursorText = [_ref, _elev] call FUNC(mgrsCursorText);
                    private _offset = _map ctrlMapScreenToWorld [
                        (_mouse select 0) + 0.012,
                        (_mouse select 1) - 0.022
                    ];
                    if ((count _offset) >= 2) then {
                        _map drawIcon [
                            "", [1, 1, 1, 1], _offset, 0, 0, 0,
                            _cursorText, 1, 0.022, "PuristaMedium", "left"
                        ];
                    };
                };
            };
        };
    }];

    _mapCtrl setVariable [QGVAR(mgrsMapReady), true];
}];
