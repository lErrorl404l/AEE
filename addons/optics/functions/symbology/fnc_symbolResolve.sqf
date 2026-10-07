#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbolResolve
 *
 * Pure symbol resolver.  Maps a side, a class category, an affiliation, an
 * echelon and a palette to one symbol specification.  PURE: every input
 * arrives as an argument, so the resolver reads no marker, no unit and no
 * world.  The side is carried for the caller's symmetry; the affiliation is
 * already resolved before this call.
 *
 * The specification is the real engine marker: the CfgMarkers type from
 * FUNC(symbologyMarkerType) and the CfgMarkerColors class from
 * FUNC(symbologyMarkerColor).  The affiliation and the echelon are carried so
 * the application layer can label and size the symbol.
 *
 * Arguments:
 *   0: _side        <ANY>    the engine side, carried, not read
 *   1: _category    <STRING> a class category, for example "infantry"
 *   2: _affiliation <STRING> "friend", "hostile", "neutral" or "unknown"
 *   3: _echelon     <STRING> an echelon token, for example "squad"
 *   4: _palette     <STRING> "NATO", "OPFOR" or "Auto"
 *
 * Return: <ARRAY> [affiliation, markerType, markerColourClass, echelon]
 */
params [
    ["_side", "", []],
    ["_category", "unknown", [""]],
    ["_affiliation", "friend", [""]],
    ["_echelon", "unknown", [""]],
    ["_palette", "NATO", [""]]
];

private _markerType = [
    _affiliation, _category, "land", _echelon, _palette
] call FUNC(symbologyMarkerType);
private _markerColour = [_affiliation, _palette] call FUNC(symbologyMarkerColor);

[_affiliation, _markerType, _markerColour, _echelon]
