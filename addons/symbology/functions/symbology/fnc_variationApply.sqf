#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationApply
 *
 * Re-types the dynamic variation family markers from the active option state.
 * The active state is the aee_symbology_variationState global; the CBA LIST
 * settings and the selector dialog write it, so one state drives every surface.
 * The kernel resolves the state through FUNC(variationResolve) and applies the
 * result to every marker whose type is the family entry AEE_Variation, and to
 * every marker the apply pass recorded as originating from AEE_Variation.
 *
 * The resolved echelon (spec element 3) drives a companion echelon overlay
 * marker above each family marker, exactly as FUNC(symbologyMarkersApply)
 * draws it for a unit: the overlay class comes from
 * FUNC(symbologyEchelonMarker) and the 1:2 box from FUNC(symbologyEchelonSize),
 * so the ticks sit ABOVE the frame (APP-6 field B, ADR-028 defect 4).  A
 * family marker with no live overlay is given one, and an overlay whose family
 * marker is gone is deleted.  Issue #242: the echelon selector changes the
 * drawn symbol.
 *
 * CLIENT-LOCAL only: it calls setMarkerTypeLocal and setMarkerColorLocal, never
 * a global marker command, so a mission marker is never broadcast or changed on
 * another machine.  FUNC(symbologyMarkersRestore) reverts the markers on map
 * close from the recorded original type.
 *
 * Returns: nothing.
 */
private _state = missionNamespace getVariable [QGVAR(variationState), []];
private _spec = ["symbol", _state] call FUNC(variationResolve);
private _type = _spec select 1;
private _colour = _spec select 2;
private _echelon = _spec select 3;

// The markers the apply pass resolved from the family entry; their recorded
// original type is AEE_Variation, so the live re-type finds them after they
// have already taken a concrete type.
private _cache = missionNamespace getVariable [QGVAR(symbologyMarkerCache), []];
private _familyNames = _cache select { (_x select 1) isEqualTo "AEE_Variation" } apply {
    _x select 0
};

private _echelonCreated = missionNamespace getVariable [QGVAR(symbologyVariationEchelonMarkers), []];
private _echelonLive = [];

{
    private _name = _x;
    if ((markerType _name) isEqualTo "AEE_Variation" || {_name in _familyNames}) then {
        _name setMarkerTypeLocal _type;
        _name setMarkerColorLocal _colour;

        // The echelon overlay draws above the frame; its box is 1:2 so the
        // engine does not stretch the 64 x 128 texture (feedback T170754).
        private _echelonName = "AEE_ECHV_" + _name;
        if (!(_echelonName in _echelonCreated)) then {
            _echelonName = createMarkerLocal [_echelonName, getMarkerPos _name];
            _echelonCreated pushBack _echelonName;
        };
        _echelonName setMarkerPosLocal (getMarkerPos _name);
        _echelonName setMarkerTypeLocal ([_echelon] call FUNC(symbologyEchelonMarker));
        _echelonName setMarkerColorLocal _colour;
        private _frameSize = markerSize _name;
        _echelonName setMarkerSize ([_frameSize select 0] call FUNC(symbologyEchelonSize));
        _echelonLive pushBack _echelonName;
    };
} forEach allMapMarkers;

{
    if (!(_x in _echelonLive)) then {
        deleteMarkerLocal _x;
        _echelonCreated deleteAt (_echelonCreated find _x);
    };
} forEach (_echelonCreated + []);
missionNamespace setVariable [QGVAR(symbologyVariationEchelonMarkers), _echelonCreated];
