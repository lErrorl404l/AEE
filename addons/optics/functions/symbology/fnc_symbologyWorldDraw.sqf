#include "..\..\script_component.hpp"
// The 3D symbol range.  A set range keeps the Draw3D worker bounded.
#define SYMBOLOGY_WORLD_RANGE 2500
/*
 * aee_optics_fnc_symbologyWorldDraw
 *
 * Draw3D worker for the NATO APP-6(C) symbols in the 3D view.  It draws the
 * AEE frame and inner glyph as 3D lines and the label as 3D text, for the
 * player and each in-range unit, out to a set range.
 *
 * The engine's own in-world unit icons cannot be suppressed: they are driven
 * by the difficulty preset and no script command removes them.  This worker
 * draws the AEE symbol over them and makes no claim to remove them.
 *
 * The unit list is rebuilt at most once a second, never per frame, so the
 * worker adds no per-frame allUnits sweep.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};
if (!isNil QGVAR(symbologyWorldEH)) exitWith {};

GVAR(symbologyWorldEH) = addMissionEventHandler ["Draw3D", {
    if (!(missionNamespace getVariable [QGVAR(symbologyEnabled), false])) exitWith {};
    if (visibleMap) exitWith {};

    private _player = call CBA_fnc_currentUnit;
    if (isNull _player) exitWith {};

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

    // ── Rebuild the in-range unit list at most once a second. ────────────
    private _now = diag_tickTime;
    private _last = missionNamespace getVariable [QGVAR(symbologyWorldTime), -1e9];
    if ((_now - _last) > 1) then {
        private _units = [];
        if (missionNamespace getVariable [QGVAR(symbologyUnits), true]) then {
            {
                if ((_player distance _x) <= SYMBOLOGY_WORLD_RANGE) then {
                    _units pushBack _x;
                };
            } forEach allUnits;
        };
        missionNamespace setVariable [QGVAR(symbologyWorldUnits), _units];
        missionNamespace setVariable [QGVAR(symbologyWorldTime), _now];
    };

    // ── Draw one symbol above a unit. ────────────────────────────────────
    private _drawWorld = {
        params ["_unit", "_spec", "_label"];
        private _base = getPos _unit;
        private _origin = [
            _base select 0, _base select 1, (_base select 2) + 2.5
        ];
        private _scale = 1.5;
        private _colour = _spec select 3;
        private _z = _origin select 2;

        {
            private _prim = _x;
            private _kind = _prim select 0;
            private _points = _prim select 1;
            if (_kind isEqualTo "ellipse") then {
                // A ring sampled as line segments; drawEllipse3D does not exist.
                private _boxCentre = _points select 0;
                private _axes = _points select 1;
                private _cx = (_origin select 0) + ((_boxCentre select 0) * _scale);
                private _cy = (_origin select 1) + ((_boxCentre select 1) * _scale);
                private _steps = 12;
                for "_i" from 0 to (_steps - 1) do {
                    private _a0 = 360 * _i / _steps;
                    private _a1 = 360 * (_i + 1) / _steps;
                    drawLine3D [
                        [
                            _cx + ((_axes select 0) * _scale * (cos _a0)),
                            _cy + ((_axes select 1) * _scale * (sin _a0)),
                            _z
                        ],
                        [
                            _cx + ((_axes select 0) * _scale * (cos _a1)),
                            _cy + ((_axes select 1) * _scale * (sin _a1)),
                            _z
                        ],
                        _colour
                    ];
                };
            } else {
                if ((count _points) > 1) then {
                    for "_i" from 0 to ((count _points) - 2) do {
                        private _pA = _points select _i;
                        private _pB = _points select (_i + 1);
                        drawLine3D [
                            [
                                (_origin select 0) + ((_pA select 0) * _scale),
                                (_origin select 1) + ((_pA select 1) * _scale),
                                _z
                            ],
                            [
                                (_origin select 0) + ((_pB select 0) * _scale),
                                (_origin select 1) + ((_pB select 1) * _scale),
                                _z
                            ],
                            _colour
                        ];
                    };
                };
            };
        } forEach ([_spec] call FUNC(symbolDrawPlan));

        if (_label isNotEqualTo "") then {
            drawIcon3D [
                "", _colour, _origin, 0, 0, 0,
                _label, 2, 0.024, _font, "center"
            ];
        };
    };

    // ── The player ───────────────────────────────────────────────────────
    private _playerCategory = [_player] call FUNC(symbologyUnitCategory);
    private _playerSpec = [
        playerSide, _playerCategory, "friend", "unknown", _palette
    ] call FUNC(symbolResolve);
    [_player, _playerSpec, name _player] call _drawWorld;

    // ── The in-range units ───────────────────────────────────────────────
    {
        private _unit = _x;
        if (alive _unit) then {
            private _category = [_unit] call FUNC(symbologyUnitCategory);
            private _colourName = "ColorUNKNOWN";
            if (side _unit isEqualTo west) then { _colourName = "ColorWEST"; };
            if (side _unit isEqualTo east) then { _colourName = "ColorEAST"; };
            if (side _unit isEqualTo resistance) then { _colourName = "ColorGUER"; };
            if (side _unit isEqualTo civilian) then { _colourName = "ColorCIV"; };
            private _affiliation = ["", _colourName, _friendly] call FUNC(symbologyAffiliation);
            private _spec = [
                side _unit, _category, _affiliation, "unknown", _palette
            ] call FUNC(symbolResolve);
            [_unit, _spec, name _unit] call _drawWorld;
        };
    } forEach (missionNamespace getVariable [QGVAR(symbologyWorldUnits), []]);
}];
