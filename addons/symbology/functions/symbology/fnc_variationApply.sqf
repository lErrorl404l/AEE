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

// The markers the apply pass resolved from the family entry; their recorded
// original type is AEE_Variation, so the live re-type finds them after they
// have already taken a concrete type.
private _cache = missionNamespace getVariable [QGVAR(symbologyMarkerCache), []];
private _familyNames = _cache select { (_x select 1) isEqualTo "AEE_Variation" } apply {
    _x select 0
};

{
    private _name = _x;
    if ((markerType _name) isEqualTo "AEE_Variation" || {_name in _familyNames}) then {
        _name setMarkerTypeLocal _type;
        _name setMarkerColorLocal _colour;
    };
} forEach allMapMarkers;
