#include "..\..\script_component.hpp"
/*
 * ECOTI environment HUD map markers.
 *
 * Registers one Draw3D worker.  The worker rebuilds a read-only marker cache
 * once a second from the mission marker list, then draws each in-range marker
 * as 3D text with its distance.  It never creates or edits a marker.
 *
 * Ported from workshop 3759527903 FPANO_ECOTI/scripts/FPANO_fnc_mapMarkers.sqf
 * (the marker scan and the 3D label layout).  The ally-name and friendly-
 * vehicle passes of the source are omitted: they duplicate the marker list
 * and add per-second allUnits/vehicles sweeps for a dismounted aid.  The
 * source raster icons (POI/OP/FSS and the engine military icons) are replaced
 * by empty-icon 3D text, so no raster asset is referenced.
 *
 * Returns: nothing.
 */
if (!hasInterface) exitWith {};
if (!isNil QGVAR(hudMarkersEH)) exitWith {};

missionNamespace setVariable [QGVAR(hudMarkersEH), addMissionEventHandler ["Draw3D", {
    if (!(missionNamespace getVariable [QGVAR(hudEnabled), false])) exitWith {};
    if (!(missionNamespace getVariable [QGVAR(hudOn), false])) exitWith {};
    if ((currentVisionMode player) != 1) exitWith {};
    if (visibleMap) exitWith {};

    private _now = diag_tickTime;
    private _last = missionNamespace getVariable [QGVAR(hudMarkersTime), -10];
    if ((_now - _last) > 1) then {
        private _cache = [];
        {
            private _text = markerText _x;
            private _type = markerType _x;
            private _pos = getMarkerPos _x;
            if (_text isNotEqualTo "" && _type isNotEqualTo "") then {
                if ((_pos select 0) isNotEqualTo 0 || (_pos select 1) isNotEqualTo 0) then {
                    _cache pushBack [_text, _pos, _x, _type];
                };
            };
        } forEach allMapMarkers;
        missionNamespace setVariable [QGVAR(hudMarkersCache), _cache];
        missionNamespace setVariable [QGVAR(hudMarkersTime), _now];
    };

    private _player = call CBA_fnc_currentUnit;
    // The affiliation is computed against the palette-resolved friendly side,
    // exactly as the map layer does.  Without it the third argument defaults
    // to WEST and an EAST player reads every marker against WEST.
    private _palette = missionNamespace getVariable [QEGVAR(symbology,symbologyPalette), "Auto"];
    private _localSide = "WEST";
    if (playerSide isEqualTo east) then { _localSide = "EAST"; };
    private _friendly = [_palette, _localSide] call EFUNC(symbology,symbologyPaletteFriendly);
    private _resolvedPalette = _palette;
    if (_palette isEqualTo "Auto") then {
        _resolvedPalette = ["NATO", "OPFOR"] select (_friendly isEqualTo "EAST");
    };
    {
        _x params ["_text", "_pos", "_name", "_type"];
        private _dist = _player distance _pos;
        if (_dist <= 2500) then {
            // The real AEE marker texture in front of the text label.
            if (missionNamespace getVariable [QEGVAR(symbology,symbologyEnabled), false]) then {
                private _category = [_name, _type] call EFUNC(symbology,symbologyMarkerCategory);
                private _affiliation = [_name, "", _friendly] call EFUNC(symbology,symbologyAffiliation);
                private _spec = [
                    sideUnknown, _category, _affiliation, "unknown", _resolvedPalette
                ] call EFUNC(symbology,symbolResolve);
                private _texture = getText (
                    configFile >> "CfgMarkers" >> (_spec select 1) >> "texture"
                );
                if (_texture isNotEqualTo "") then {
                    private _colour = [_affiliation, "NATO"] call EFUNC(symbology,symbolPalette);
                    drawIcon3D [
                        _texture, _colour, _pos, 1.2, 1.2, 0,
                        "", 0, 0, "PuristaMedium", "center"
                    ];
                };
            };
            drawIcon3D [
                "", [0.75, 1, 1, 0.9], _pos, 0, 0, 0,
                _text, 2, 0.024, "PuristaMedium", "center"
            ];
            drawIcon3D [
                "", [0.75, 1, 1, 0.7],
                [_pos select 0, _pos select 1, (_pos select 2) - 0.6],
                0, 0, 0,
                ([_dist] call FUNC(hudFormatRange)),
                2, 0.020, "PuristaMedium", "center"
            ];
        };
    } forEach (missionNamespace getVariable [QGVAR(hudMarkersCache), []]);
}]];
