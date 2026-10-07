#include "..\..\script_component.hpp"
// The map symbol range for the unit pass.  A set range keeps the work bounded.
#define SYMBOLOGY_UNIT_RANGE 3000
/*
 * aee_optics_fnc_symbologyMarkersApply
 *
 * Applies the AEE symbols as real engine markers while the map is open.  The
 * work is client-local and reversible:
 *
 *   1. when the suppression setting is on, disableMapIndicators hides the
 *      engine indicators where the difficulty exposes them;
 *   2. every mission marker not tagged AEE has its type and colour converted
 *      with setMarkerTypeLocal and setMarkerColorLocal to the AEE symbol, and
 *      its original type and colour are recorded in a local cache;
 *   3. the player and each in-range unit get a real local AEE marker.
 *
 * No global marker command is called, so a mission marker is never broadcast,
 * moved, recoloured or deleted on another machine.
 * FUNC(symbologyMarkersRestore) puts every recorded marker back on map close.
 *
 * Returns: nothing.
 */
private _palette = missionNamespace getVariable [QGVAR(symbologyPalette), "Auto"];
private _localSide = "WEST";
if (playerSide isEqualTo east) then { _localSide = "EAST"; };
private _friendly = [_palette, _localSide] call FUNC(symbologyPaletteFriendly);
private _resolvedPalette = _palette;
if (_palette isEqualTo "Auto") then {
    _resolvedPalette = ["NATO", "OPFOR"] select (_friendly isEqualTo "EAST");
};

if (missionNamespace getVariable [QGVAR(symbologySuppress), true]) then {
    disableMapIndicators [true, true, true, true];
};

// ── The mission markers ─────────────────────────────────────────────────
private _cache = missionNamespace getVariable [QGVAR(symbologyMarkerCache), []];
private _names = _cache apply { _x select 0 };
{
    private _name = _x;
    private _tagged = (_name select [0, 4]) isEqualTo "AEE_";
    if (!_tagged && !(_name in _names)) then {
        private _category = [_name] call FUNC(symbologyMarkerCategory);
        private _affiliation = [_name, "", _friendly] call FUNC(symbologyAffiliation);
        private _spec = [
            sideUnknown, _category, _affiliation, "unknown", _resolvedPalette
        ] call FUNC(symbolResolve);
        _cache pushBack [_name, markerType _name, markerColor _name];
        _names pushBack _name;
        _name setMarkerTypeLocal (_spec select 1);
        _name setMarkerColorLocal (_spec select 2);
    };
} forEach allMapMarkers;
missionNamespace setVariable [QGVAR(symbologyMarkerCache), _cache];

// ── The player and the in-range units ───────────────────────────────────
if (!(missionNamespace getVariable [QGVAR(symbologyUnits), true])) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNull _player) exitWith {};

private _units = [_player];
{
    if ((_player distance _x) <= SYMBOLOGY_UNIT_RANGE) then {
        _units pushBack _x;
    };
} forEach allUnits;

private _created = missionNamespace getVariable [QGVAR(symbologyUnitMarkers), []];
private _live = [];
{
    private _unit = _x;
    private _markerName = "AEE_UNIT_" + (netId _unit);
    private _category = [_unit] call FUNC(symbologyUnitCategory);
    private _colourName = [side _unit, true] call BIS_fnc_sideColor;
    private _affiliation = ["", _colourName, _friendly] call FUNC(symbologyAffiliation);
    private _spec = [
        side _unit, _category, _affiliation, "unknown", _resolvedPalette
    ] call FUNC(symbolResolve);
    if (!(_markerName in _created)) then {
        _markerName = createMarkerLocal [_markerName, getPos _unit];
        _created pushBack _markerName;
    };
    _markerName setMarkerPosLocal (getPos _unit);
    _markerName setMarkerTypeLocal (_spec select 1);
    _markerName setMarkerColorLocal (_spec select 2);
    _live pushBack _markerName;
} forEach _units;

// Remove the markers for the units that left the range.
{
    if (!(_x in _live)) then {
        deleteMarkerLocal _x;
        _created deleteAt (_created find _x);
    };
} forEach (_created + []);
missionNamespace setVariable [QGVAR(symbologyUnitMarkers), _created];
