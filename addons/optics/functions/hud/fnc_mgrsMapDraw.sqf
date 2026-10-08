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
 *   1. the cardinal grid overlay, at a decimal interval chosen for the zoom;
 *   2. the cursor readout, our MGRS reference and terrain elevation;
 *   3. the player position, labelled with its MGRS reference;
 *   4. each AEE-owned marker, labelled with its MGRS reference.
 *
 * The engine map grid stays numeric.  The CfgWorlds Grid class formats
 * numbers only and no script command writes it, so the overlay draws its own
 * CARDINAL lines over it (ADR-030 records the choice: the map is north up, so
 * a cardinal grid matches the compass, a real paper map and the base engine).
 * The engine cursor tooltip is the map display's
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

        // The overlay font.  FUNC(mgrsFontFamily) returns the AEE monospaced
        // family only when its glyph files ship, else the engine family, so a
        // missing optional font never blanks the map.  The setting gates it.
        private _font = "PuristaMedium";
        if (missionNamespace getVariable [QGVAR(symbologyFont), true]) then {
            _font = [true] call FUNC(mgrsFontFamily);
        };

        private _anchor = call EFUNC(core,getGeoAnchor);

        // The visible world rectangle and its span.  The span sets the
        // displayed scale, and the grid overlay reuses the rectangle.
        private _cp = ctrlPosition _map;
        private _c0 = _map ctrlMapScreenToWorld [_cp select 0, _cp select 1];
        private _c1 = _map ctrlMapScreenToWorld [
            (_cp select 0) + (_cp select 2),
            (_cp select 1) + (_cp select 3)
        ];
        private _rect = [];
        private _span = 0;
        if (((count _c0) >= 2) && ((count _c1) >= 2)) then {
            _rect = [
                (_c0 select 0) min (_c1 select 0),
                (_c0 select 1) min (_c1 select 1),
                (_c0 select 0) max (_c1 select 0),
                (_c0 select 1) max (_c1 select 1)
            ];
            _span = ((_rect select 2) - (_rect select 0)) max ((_rect select 3) - (_rect select 1));
        };

        // The digit count and the finest grid step follow the displayed
        // scale when the auto setting is on, else the manual mgrsPrecision
        // list.
        private _precision = missionNamespace getVariable [QGVAR(mgrsPrecision), 10];
        private _gridInterval = 0;
        if (missionNamespace getVariable [QGVAR(mgrsPrecisionAuto), true]) then {
            private _scale = [_anchor select 3, _span] call FUNC(mgrsMapPrecision);
            _precision = _scale select 0;
            _gridInterval = _scale select 1;
        };
        if !(_precision isEqualType 0) then { _precision = 10; };
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
            "", [0.05, 0.05, 0.05, 1], getPos _player, 0, 0, 0,
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
                    "", [0.05, 0.05, 0.05, 1], getMarkerPos _x, 0, 0, 0,
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
            if ((count _rect) >= 4) then {
                private _key = _rect apply { round (_x / 10) };
                private _cache = missionNamespace getVariable [QGVAR(mgrsGridCache), []];
                // The cache is rebuilt on a miss.  Build the plan as the value
                // of an if-expression so it is assigned at THIS scope level,
                // never read back from a local written inside the nested
                // rebuild block.  A short or malformed cache falls through to
                // the rebuild, so a nil can never reach the params below.
                private _hit = if ((_cache isEqualType []) && {((count _cache) == 2)}) then {
                    (_cache select 0) isEqualTo _key
                } else {
                    false
                };
                private _plan = if (_hit) then {
                    _cache select 1
                } else {
                    private _fresh = [_anchor, _rect, _gridInterval] call FUNC(mgrsGridLines);
                    missionNamespace setVariable [QGVAR(mgrsGridCache), [_key, _fresh]];
                    _fresh
                };
                if !(_plan isEqualType []) then { _plan = []; };
                _plan params ["_segments", "_labels"];
                // The linework is DARK, to read against the light topographic
                // ground (colorBackground {0.90,0.88,0.80}) the way the map
                // labels do (colorNames {0.10,0.10,0.10,0.90}).  The old light
                // cyan at alpha 0.30 read as grey and was hard to see.  A major
                // line is darker and thicker than a minor one.
                //
                // Each segment is one whole grid line: FUNC(mgrsGridLines)
                // emits one axis-aligned segment per line, and the map control
                // maps world to screen linearly, so the segment is straight by
                // construction and has no interior joint to bead.  Line weight:
                // the engine's script drawLine default is 3
                // (BIKI), and the operator reports the old 1 px line as "very
                // very thin", so the minor line matches the default and the
                // index (major) line is heavier.
                {
                    _x params ["_pA", "_pB", "_major"];
                    private _colour = [0.08, 0.08, 0.10, 0.85];
                    private _width = 3;
                    if (_major) then {
                        _colour = [0.02, 0.02, 0.04, 1];
                        _width = 5;
                    };
                    _map drawLine [_pA, _pB, _colour, _width];
                } forEach _segments;
                {
                    _x params ["_pos", "_label", "_major"];
                    private _size = 0.022;
                    if (_major) then { _size = 0.026; };
                    _map drawIcon [
                        "", [0.05, 0.05, 0.05, 1], _pos, 0, 0, 0,
                        _label, 1, _size, _font, "center"
                    ];
                } forEach _labels;
            };
        };

        // ── Engine cursor tooltip ─────────────────────────────────────
        // The engine readout is the map display's Tooltip control of class
        // RscMapControlTooltip (idc 2350), filled and shown by closed engine
        // C++ AFTER this Draw event, so the hide here loses the race.  The
        // tooltip is neutralised at the config (config.cpp), and this hide is
        // only a first line of defence; there is no readout to hand back.
        private _display = ctrlParent _map;
        private _engineReadout = controlNull;
        if (!isNull _display) then {
            _engineReadout = _display displayCtrl 2350;
        };
        private _cursorReadout = missionNamespace getVariable [QGVAR(mgrsCursorReadout), true];
        if (!isNull _engineReadout) then {
            _engineReadout ctrlShow false;
        };

        // ── Cursor readout ────────────────────────────────────────────
        // Draw the aee MGRS readout at the cursor.  It shows OUR MGRS at the
        // displayed precision, so its digit group matches the drawn grid line.
        if (_cursorReadout) then {
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
                    private _anchorScreen = [
                        (_mouse select 0) + 0.012,
                        (_mouse select 1) - 0.022
                    ];
                    private _draw = _map ctrlMapScreenToWorld _anchorScreen;
                    if ((count _draw) >= 2) then {
                        _map drawIcon [
                            "", [0.05, 0.05, 0.05, 1], _draw, 0, 0, 0,
                            _cursorText, 1, 0.022, _font, "left"
                        ];
                    };
                };
            };
        };

        // ── GPS device readout on the map ─────────────────────────────
        // The hand-held GPS readout is a HUD element on the RscTitles layer,
        // which the open map display covers, so it is not visible on the map.
        // When the player carries an ItemGPS, draw the MGRS reference on the
        // map, so the grid can be read with the device while the map is open.
        if (("ItemGPS" in (assignedItems _player)) || ("ItemGPS" in (items _player))) then {
            private _cp = ctrlPosition _map;
            private _gpsScreen = [
                (_cp select 0) + ((_cp select 2) * 0.62),
                (_cp select 1) + ((_cp select 3) * 0.94)
            ];
            private _gpsWorld = _map ctrlMapScreenToWorld _gpsScreen;
            if ((count _gpsWorld) >= 2) then {
                private _gpsRef = ["", getPos _player, _anchor, _precision] call FUNC(mgrsMarkerText);
                if (_gpsRef isNotEqualTo "") then {
                    _map drawIcon [
                        "", [0.05, 0.05, 0.05, 1], _gpsWorld, 0, 0, 0,
                        "GPS  " + _gpsRef, 1, 0.024, _font, "left"
                    ];
                };
            };
        };
    }];

    _mapCtrl setVariable [QGVAR(mgrsMapReady), true];
}];
