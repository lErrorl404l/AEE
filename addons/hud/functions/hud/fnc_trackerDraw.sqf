#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_trackerDraw
 *
 * ATAK-style presentation for the signal-dependent tracker.  It draws the
 * fuzzy markers and the uncertainty ellipse from the published tracker state
 * (aee_optics_trackerTracks) on the map and on the HUD.  It is read-only: it
 * creates no marker and edits none, and it changes no other module's state.
 *
 * The map overlay registers one Draw handler on the engine map control, the
 * fnc_mgrsMapDraw pattern (RscMapControl, display 12, control 51).  The HUD
 * worker is a Draw3D handler that draws a 3D label and a small uncertainty
 * ring at each track.
 *
 * Colour follows the ATAK friend palette: gold for a good fix, amber for a
 * degraded fix and red when the fix is lost.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};
if (!isNil QGVAR(trackerDrawEH)) exitWith {};

// ── Map overlay ───────────────────────────────────────────────────────────
// The map control exists only while the map is open, so the Draw handler is
// attached from the "Map" mission event on open.  The handler id is not kept:
// the guard at the top of this function registers it once.
addMissionEventHandler ["Map", {
    params ["_opened"];
    if (!_opened) exitWith {};

    private _display = findDisplay 12;
    if (isNull _display) exitWith {};
    private _mapCtrl = _display displayCtrl 51;
    if (isNull _mapCtrl) exitWith {};
    if (_mapCtrl getVariable [QGVAR(trackerMapReady), false]) exitWith {};

    _mapCtrl ctrlAddEventHandler ["Draw", {
        params ["_map"];
        if (!(missionNamespace getVariable [QGVAR(trackerEnabled), false])) exitWith {};

        private _tracks = missionNamespace getVariable [QGVAR(trackerTracks), []];
        {
            _x params [
                "_unit", "_exact", "_displayed", "_ellipse",
                "_trackAge", "_quality", "_linkState", "_suppressed"
            ];
            if (alive _unit) then {
                // The uncertainty ellipse: the semi axes and the orientation
                // from the GNSS error kernel, in ATAK style.
                _map drawEllipse [
                    _displayed,
                    _ellipse select 3,
                    _ellipse select 4,
                    _ellipse select 5,
                    [1, 0.85, 0, 0.35],
                    ""
                ];
                private _colour = [1, 0.85, 0, 0.9];
                if (_quality isEqualTo "degraded") then { _colour = [1, 0.65, 0, 0.9]; };
                if (_quality isEqualTo "none") then { _colour = [1, 0.25, 0.25, 0.9]; };
                private _text = format ["%1 %2 %3", name _unit, toUpper _quality, round (_ellipse select 7)];
                _map drawIcon [
                    "", _colour, _displayed, 0, 0, 0,
                    _text, 1, 0.024, "PuristaMedium", "center"
                ];
            };
        } forEach _tracks;
    }];

    _mapCtrl setVariable [QGVAR(trackerMapReady), true];
}];

// ── HUD worker ────────────────────────────────────────────────────────────
// A Draw3D worker: a text label and a 12-segment uncertainty ring at each
// displayed position, out to 3 km.
GVAR(trackerDrawEH) = addMissionEventHandler ["Draw3D", {
    if (!(missionNamespace getVariable [QGVAR(trackerEnabled), false])) exitWith {};
    if (visibleMap) exitWith {};

    private _player = call CBA_fnc_currentUnit;
    private _tracks = missionNamespace getVariable [QGVAR(trackerTracks), []];
    {
        _x params [
            "_unit", "_exact", "_displayed", "_ellipse",
            "_trackAge", "_quality", "_linkState", "_suppressed"
        ];
        if (alive _unit && {(_player distance _displayed) <= 3000}) then {
            private _colour = [1, 0.85, 0, 0.9];
            if (_quality isEqualTo "degraded") then { _colour = [1, 0.65, 0, 0.9]; };
            if (_quality isEqualTo "none") then { _colour = [1, 0.25, 0.25, 0.9]; };
            drawIcon3D [
                "", _colour, _displayed, 0, 0, 0,
                name _unit, 2, 0.024, "PuristaMedium", "center"
            ];
            drawIcon3D [
                "", _colour,
                [_displayed select 0, _displayed select 1, (_displayed select 2) - 0.6],
                0, 0, 0,
                ([_trackAge] call FUNC(hudFormatRange)),
                2, 0.020, "PuristaMedium", "center"
            ];

            // The uncertainty ring, drawn on the horizontal plane.
            private _semiMajor = _ellipse select 3;
            if (_semiMajor > 0.5) then {
                private _segments = 12;
                private _orientation = _ellipse select 5;
                for "_k" from 0 to (_segments - 1) do {
                    private _t0 = (_k / _segments) * 360;
                    private _t1 = ((_k + 1) / _segments) * 360;
                    private _p0 = [
                        (_displayed select 0) + (sin (_t0 + _orientation)) * _semiMajor,
                        (_displayed select 1) + (cos (_t0 + _orientation)) * _semiMajor,
                        _displayed select 2
                    ];
                    private _p1 = [
                        (_displayed select 0) + (sin (_t1 + _orientation)) * _semiMajor,
                        (_displayed select 1) + (cos (_t1 + _orientation)) * _semiMajor,
                        _displayed select 2
                    ];
                    drawLine3D [_p0, _p1, _colour];
                };
            };
        };
    } forEach _tracks;
}];
