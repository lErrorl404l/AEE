#include "..\..\script_component.hpp"
// The ownership tag an AEE marker carries.  AEE ships no marker today, so the
// tag is a forward-compatibility convention: a tagged marker is left alone.
#define SYMBOLOGY_MARKER_TAG "AEE"
// The map symbol range for the unit pass.  A set range keeps the draw bounded.
#define SYMBOLOGY_UNIT_RANGE 3000
/*
 * aee_optics_fnc_symbologyMapDraw
 *
 * Draws the NATO APP-6(C) map symbols over the engine map.  It registers one
 * Draw handler on the engine map control (RscMapControl, display 12, control
 * 51) from the "Map" mission event on open, the fnc_mgrsMapDraw pattern.
 *
 * The handler is read-only apart from one local, reversible hide:
 *
 *   1. when the suppression setting is on, disableMapIndicators hides the
 *      engine indicators where the difficulty exposes them;
 *   2. every mission marker not tagged AEE is hidden with setMarkerAlphaLocal
 *      0 and its original markerAlpha is recorded;
 *   3. the symbol for each hidden marker, the player and each in-range unit is
 *      built from the adapters and FUNC(symbolResolve) and drawn with the
 *      FUNC(symbolDrawPlan) geometry;
 *   4. on map close every recorded alpha is restored and the cache is cleared.
 *
 * The hide is client-local and restored.  No global marker command is called,
 * so a mission marker is never broadcast, moved, recoloured or deleted.  No
 * texture path is drawn: drawIcon carries text only.
 *
 * The map control exists only while the map is open, so the handler is
 * attached from the "Map" event.  The marker list is re-scanned at most once a
 * second, so a static map does not re-scan every frame.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};
if (!isNil QGVAR(symbologyMapEH)) exitWith {};

GVAR(symbologyMapEH) = addMissionEventHandler ["Map", {
    params ["_opened"];

    // ── Map close: restore every marker hidden while the map was open. ───
    if (!_opened) exitWith {
        private _hidden = missionNamespace getVariable [QGVAR(symbologyHiddenMarkers), []];
        {
            (_x select 0) setMarkerAlphaLocal (_x select 1);
        } forEach _hidden;
        missionNamespace setVariable [QGVAR(symbologyHiddenMarkers), []];
        private _display = findDisplay 12;
        if (!isNull _display) then {
            private _mapCtrl = _display displayCtrl 51;
            if (!isNull _mapCtrl) then {
                _mapCtrl setVariable [QGVAR(symbologyMapReady), false];
            };
        };
    };

    private _display = findDisplay 12;
    if (isNull _display) exitWith {};
    private _mapCtrl = _display displayCtrl 51;
    if (isNull _mapCtrl) exitWith {};
    if (_mapCtrl getVariable [QGVAR(symbologyMapReady), false]) exitWith {};

    _mapCtrl ctrlAddEventHandler ["Draw", {
        params ["_map"];
        if (!(missionNamespace getVariable [QGVAR(symbologyEnabled), false])) exitWith {};

        // ── The engine indicators, where the engine exposes them. ────────
        if (missionNamespace getVariable [QGVAR(symbologySuppress), true]) then {
            disableMapIndicators [true, true, true, true];
        };

        private _palette = missionNamespace getVariable [QGVAR(symbologyPalette), "Auto"];
        private _localSide = "WEST";
        if (playerSide isEqualTo east) then { _localSide = "EAST"; };
        private _friendly = [_palette, _localSide] call FUNC(symbologyPaletteFriendly);

        private _font = "PuristaMedium";
        if (missionNamespace getVariable [QGVAR(symbologyFont), true]) then {
            if (isClass (configFile >> "CfgFontFamilies" >> "AEEFont")) then {
                _font = "AEEFont";
            };
        };

        // ── Re-scan at most once a second. ───────────────────────────────
        // New markers are hidden and their original alpha recorded.  The
        // in-range unit list is rebuilt here, never per frame.
        private _now = diag_tickTime;
        private _last = missionNamespace getVariable [QGVAR(symbologyScanTime), -1e9];
        if ((_now - _last) > 1) then {
            private _hidden = missionNamespace getVariable [QGVAR(symbologyHiddenMarkers), []];
            private _names = _hidden apply { _x select 0 };
            {
                private _name = _x;
                private _text = markerText _name;
                private _tagged = ((_text select [0, 3]) isEqualTo SYMBOLOGY_MARKER_TAG)
                    || ((_name select [0, 3]) isEqualTo SYMBOLOGY_MARKER_TAG);
                if (!_tagged && !(_name in _names)) then {
                    _hidden pushBack [_name, markerAlpha _name];
                    _names pushBack _name;
                    _name setMarkerAlphaLocal 0;
                };
            } forEach allMapMarkers;
            missionNamespace setVariable [QGVAR(symbologyHiddenMarkers), _hidden];

            private _player = call CBA_fnc_currentUnit;
            private _units = [];
            if (!isNull _player) then {
                {
                    if ((_player distance _x) <= SYMBOLOGY_UNIT_RANGE) then {
                        _units pushBack _x;
                    };
                } forEach allUnits;
            };
            missionNamespace setVariable [QGVAR(symbologyUnitCache), _units];
            missionNamespace setVariable [QGVAR(symbologyScanTime), _now];
        };

        // ── Draw one symbol at a world position. ─────────────────────────
        // The unit box maps to a constant screen size: the world size of one
        // box step comes from the screen scale at the symbol centre.
        private _drawSymbol = {
            params ["_centreWorld", "_spec", "_label"];
            private _centre = _map ctrlMapWorldToScreen _centreWorld;
            if ((count _centre) < 2) exitWith {};
            private _probeX = _map ctrlMapScreenToWorld [
                (_centre select 0) + 0.02, _centre select 1
            ];
            private _probeY = _map ctrlMapScreenToWorld [
                _centre select 0, (_centre select 1) + 0.02
            ];
            private _sx = (_probeX select 0) - (_centreWorld select 0);
            private _sy = (_centreWorld select 1) - (_probeY select 1);
            private _colour = _spec select 3;

            {
                private _prim = _x;
                private _kind = _prim select 0;
                private _points = _prim select 1;
                if (_kind isEqualTo "ellipse") then {
                    private _boxCentre = _points select 0;
                    private _axes = _points select 1;
                    private _ellipseCentre = [
                        (_centreWorld select 0) + ((_boxCentre select 0) * _sx),
                        (_centreWorld select 1) + ((_boxCentre select 1) * _sy)
                    ];
                    _map drawEllipse [
                        _ellipseCentre,
                        (_axes select 0) * abs _sx,
                        (_axes select 1) * abs _sy,
                        0, _colour, ""
                    ];
                } else {
                    if ((count _points) > 1) then {
                        private _poly = [];
                        for "_i" from 0 to ((count _points) - 1) do {
                            private _pt = _points select _i;
                            _poly pushBack [
                                (_centreWorld select 0) + ((_pt select 0) * _sx),
                                (_centreWorld select 1) + ((_pt select 1) * _sy)
                            ];
                        };
                        if (_kind isEqualTo "poly") then {
                            _map drawPolygon [_poly, _colour];
                        } else {
                            for "_i" from 0 to ((count _poly) - 2) do {
                                _map drawLine [
                                    _poly select _i, _poly select (_i + 1), _colour
                                ];
                            };
                        };
                    };
                };
            } forEach ([_spec] call FUNC(symbolDrawPlan));

            if (_label isNotEqualTo "") then {
                _map drawIcon [
                    "", _colour, _centreWorld, 0, 0, 0,
                    _label, 1, 0.024, _font, "center"
                ];
            };
        };

        // ── The markers ──────────────────────────────────────────────────
        if (missionNamespace getVariable [QGVAR(symbologyMarkers), true]) then {
            {
                private _name = _x select 0;
                private _category = [_name] call FUNC(symbologyMarkerCategory);
                private _affiliation = [_name, "", _friendly] call FUNC(symbologyAffiliation);
                private _spec = [
                    sideUnknown, _category, _affiliation, "unknown", _palette
                ] call FUNC(symbolResolve);
                [_name, _spec, markerText _name] call _drawSymbol;
            } forEach (missionNamespace getVariable [QGVAR(symbologyHiddenMarkers), []]);
        };

        // ── The player ───────────────────────────────────────────────────
        private _player = call CBA_fnc_currentUnit;
        if (!isNull _player) then {
            private _category = [_player] call FUNC(symbologyUnitCategory);
            private _spec = [
                playerSide, _category, "friend", "unknown", _palette
            ] call FUNC(symbolResolve);
            [getPos _player, _spec, ""] call _drawSymbol;
        };

        // ── The in-range units ───────────────────────────────────────────
        if (missionNamespace getVariable [QGVAR(symbologyUnits), true]) then {
            {
                private _unit = _x;
                if (alive _unit) then {
                    private _category = [_unit] call FUNC(symbologyUnitCategory);
                    private _spec = [
                        side _unit, _category, "friend", "unknown", _palette
                    ] call FUNC(symbolResolve);
                    [getPos _unit, _spec, ""] call _drawSymbol;
                };
            } forEach (missionNamespace getVariable [QGVAR(symbologyUnitCache), []]);
        };
    }];

    _mapCtrl setVariable [QGVAR(symbologyMapReady), true];
}];
