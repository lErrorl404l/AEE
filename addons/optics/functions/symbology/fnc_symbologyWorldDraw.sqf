#include "..\..\script_component.hpp"
// The 3D symbol range.  A set range keeps the Draw3D worker bounded.
#define SYMBOLOGY_WORLD_RANGE 2500
/*
 * aee_optics_fnc_symbologyWorldDraw
 *
 * Draw3D worker for the AEE symbols in the 3D view.  It draws the real
 * CfgMarkers texture for each in-range unit with drawIcon3D, so the world
 * symbol and the map marker share one asset.  The texture path is read from
 * the marker type in CfgMarkers; the colour is FUNC(symbolPalette).
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
        _font = [false] call FUNC(mgrsFontFamily);
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

    // ── Draw one real marker texture above a unit. ───────────────────────
    private _drawWorld = {
        params ["_unit", "_spec", "_label", "_echelonClass"];
        private _base = getPos _unit;
        private _origin = [
            _base select 0, _base select 1, (_base select 2) + 2.5
        ];
        private _markerType = _spec select 1;
        private _texture = getText (
            configFile >> "CfgMarkers" >> _markerType >> "texture"
        );
        if (_texture isEqualTo "") exitWith {};
        private _colour = [
            _spec select 0, missionNamespace getVariable [QGVAR(symbologyPalette), "NATO"]
        ] call FUNC(symbolPalette);
        drawIcon3D [
            _texture, _colour, _origin, 1.5, 1.5, 0,
            _label, 2, 0.024, _font, "center"
        ];
        // The echelon overlay is a 64 x 128 texture with the ticks in the top
        // band, so it sits above the frame at the same origin.
        private _echelonTexture = getText (
            configFile >> "CfgMarkers" >> _echelonClass >> "texture"
        );
        if (_echelonTexture isNotEqualTo "") then {
            drawIcon3D [
                _echelonTexture, _colour, _origin, 1.5, 3.0, 0,
                "", 2, 0.024, _font, "center"
            ];
        };
    };

    // ── The player ───────────────────────────────────────────────────────
    private _playerCategory = [_player] call FUNC(symbologyUnitCategory);
    private _playerDimension = [_player] call FUNC(symbologyUnitDimension);
    private _playerEchelon = [_player] call FUNC(symbologyUnitEchelon);
    private _playerSpec = [
        playerSide, _playerCategory, "friend", _playerEchelon, _palette, _playerDimension
    ] call FUNC(symbolResolve);
    private _playerEchelonClass = [_playerEchelon] call FUNC(symbologyEchelonMarker);
    [_player, _playerSpec, name _player, _playerEchelonClass] call _drawWorld;

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
            private _echelon = [_unit] call FUNC(symbologyUnitEchelon);
            private _dimension = [_unit] call FUNC(symbologyUnitDimension);
            private _spec = [
                side _unit, _category, _affiliation, _echelon, _palette, _dimension
            ] call FUNC(symbolResolve);
            private _echelonClass = [_echelon] call FUNC(symbologyEchelonMarker);
            [_unit, _spec, name _unit, _echelonClass] call _drawWorld;
        };
    } forEach (missionNamespace getVariable [QGVAR(symbologyWorldUnits), []]);
}];
