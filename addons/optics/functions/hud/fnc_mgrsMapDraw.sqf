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
 * MGRS lines over it.  The engine cursor tooltip is the map display's
 * Tooltip control of class RscMapControlTooltip (idc 2350), so the overlay
 * hides that control and draws the aee MGRS readout in its place.  The
 * player's engine mapGridPosition is read as a cross-check and shown when
 * the aee MGRS conversion yields nothing.
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

        // The MGRS readout uses the monospaced companion, gated on the
        // symbologyFont setting.  The engine font is the fallback when the
        // AEEFontMono family is unavailable.
        private _font = "PuristaMedium";
        if (missionNamespace getVariable [QGVAR(symbologyFont), true]) then {
            if (isClass (configFile >> "CfgFontFamilies" >> "AEEFontMono")) then {
                _font = "AEEFontMono";
            };
        };

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
            _playerText, 1, 0.024, _font, "center"
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
                    _label, 1, 0.020, _font, "center"
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
                        _label, 1, _size, _font, "center"
                    ];
                } forEach _labels;
            };
        };

        // ── Engine cursor tooltip ─────────────────────────────────────
        // The engine readout is the map display's Tooltip control of class
        // RscMapControlTooltip (idc 2350).  The engine moves it to the
        // cursor and fills it with the six-figure grid and the elevation.
        // Read its rectangle first: that is the readout's old position.
        // Then hide it, so the map shows one readout, ours.
        private _display = ctrlParent _map;
        private _readoutPos = [];
        if (!isNull _display) then {
            private _engineReadout = _display displayCtrl 2350;
            if (!isNull _engineReadout) then {
                _readoutPos = ctrlPosition _engineReadout;
                _engineReadout ctrlShow false;
            };
        };

        // ── Cursor readout ────────────────────────────────────────────
        // Draw the aee MGRS readout in the engine readout's old position.
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
                    // Prefer the engine readout's rectangle.  When the
                    // engine has not positioned it yet, sit just below
                    // and right of the cursor.
                    private _anchorScreen = [
                        (_mouse select 0) + 0.012,
                        (_mouse select 1) - 0.022
                    ];
                    if ((count _readoutPos) >= 2
                        && {(_readoutPos select 0) >= 0}
                        && {(_readoutPos select 1) >= 0}) then {
                        _anchorScreen = [_readoutPos select 0, _readoutPos select 1];
                    };
                    private _draw = _map ctrlMapScreenToWorld _anchorScreen;
                    if ((count _draw) >= 2) then {
                        _map drawIcon [
                            "", [1, 1, 1, 1], _draw, 0, 0, 0,
                            _cursorText, 1, 0.022, _font, "left"
                        ];
                    };
                };
            };
        };
    }];

    _mapCtrl setVariable [QGVAR(mgrsMapReady), true];
}];
