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
 *   3. the player and each in-range unit that is alive get a real local AEE
 *      marker; a dead unit produces no marker, so the cleanup removes its
 *      marker and the next scan re-creates it on revive;
 *   4. each unit marker gets a companion echelon overlay marker at the same
 *      position, created after the frame so the overlay draws on top.
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
// Gated on the map-marker toggle; the unit pass below is gated separately by
// symbologyUnits.
if (missionNamespace getVariable [QGVAR(symbologyMarkers), true]) then {
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
};

// ── The player and the in-range units ───────────────────────────────────
if (!(missionNamespace getVariable [QGVAR(symbologyUnits), true])) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNull _player) exitWith {};

private _units = [];
if (alive _player) then {
    _units pushBack _player;
};
{
    if ((alive _x) && {(_player distance _x) <= SYMBOLOGY_UNIT_RANGE}) then {
        _units pushBack _x;
    };
} forEach allUnits;

private _created = missionNamespace getVariable [QGVAR(symbologyUnitMarkers), []];
private _echelonCreated = missionNamespace getVariable [QGVAR(symbologyUnitEchelonMarkers), []];
private _live = [];
private _echelonLive = [];
{
    private _unit = _x;
    private _markerName = "AEE_UNIT_" + (netId _unit);
    private _category = [_unit] call FUNC(symbologyUnitCategory);
    private _colourName = [side _unit, true] call BIS_fnc_sideColor;
    private _affiliation = ["", _colourName, _friendly] call FUNC(symbologyAffiliation);
    private _echelon = [_unit] call FUNC(symbologyUnitEchelon);
    private _dimension = [_unit] call FUNC(symbologyUnitDimension);
    private _spec = [
        side _unit, _category, _affiliation, _echelon, _resolvedPalette, _dimension
    ] call FUNC(symbolResolve);
    if (!(_markerName in _created)) then {
        _markerName = createMarkerLocal [_markerName, getPos _unit];
        _created pushBack _markerName;
    };
    _markerName setMarkerPosLocal (getPos _unit);
    _markerName setMarkerTypeLocal (_spec select 1);
    _markerName setMarkerColorLocal (_spec select 2);
    _live pushBack _markerName;
    // The echelon overlay is a 64 x 128 texture with the ticks in the top band.
    // The engine STRETCHES a marker texture into its box and does not keep the
    // aspect (feedback T170754), so a square marker squashes the 2:1 texture and
    // the ticks land inside the frame.  A 1:2 marker size keeps the texture
    // undistorted and the ticks sit ABOVE the frame, per APP-6 field B.  The
    // frame width is read back so the two boxes stay aligned.
    private _frameSize = markerSize _markerName;
    private _halfWidth = _frameSize select 0;
    private _echelonName = "AEE_ECH_" + (netId _unit);
    if (!(_echelonName in _echelonCreated)) then {
        _echelonName = createMarkerLocal [_echelonName, getPos _unit];
        _echelonCreated pushBack _echelonName;
    };
    _echelonName setMarkerPosLocal (getPos _unit);
    _echelonName setMarkerTypeLocal ([_echelon] call FUNC(symbologyEchelonMarker));
    _echelonName setMarkerColorLocal (_spec select 2);
    _echelonName setMarkerSize ([_halfWidth] call FUNC(symbologyEchelonSize));
    _echelonLive pushBack _echelonName;
} forEach _units;

// Remove the markers for the units that left the range.
{
    if (!(_x in _live)) then {
        deleteMarkerLocal _x;
        _created deleteAt (_created find _x);
    };
} forEach (_created + []);
missionNamespace setVariable [QGVAR(symbologyUnitMarkers), _created];

{
    if (!(_x in _echelonLive)) then {
        deleteMarkerLocal _x;
        _echelonCreated deleteAt (_echelonCreated find _x);
    };
} forEach (_echelonCreated + []);
missionNamespace setVariable [QGVAR(symbologyUnitEchelonMarkers), _echelonCreated];
