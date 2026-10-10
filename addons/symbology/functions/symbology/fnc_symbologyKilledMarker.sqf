#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyKilledMarker
 *
 * Pure kernel.  Maps a live unit's resolved marker specification to the
 * LAST-KNOWN specification the layer keeps after the unit dies.
 *
 * The resolved spec is [affiliation, markerType, markerColour, echelon], the
 * shape FUNC(symbolResolve) returns.  The last-known contact keeps the SAME
 * affiliation and the SAME category, so the operator still reads whose side
 * it was and what it was; only the position changes, to the recorded death
 * position the EntityKilled handler holds.  The kernel reads no unit and no
 * world: the spec arrives as an argument.
 *
 * CEILING: the shipped APP-6 catalogue carries no dedicated destroyed or
 * damaged unit-status symbol.  The only "Neutralized" art (AEE_FU_Neutralized
 * and its siblings) is the sea-mine subsurface-weapon symbol, a specific
 * track, not a general status overlay for an arbitrary unit.  A killed unit
 * therefore keeps its LAST-KNOWN symbol rather than a destroyed symbol.  This
 * kernel is the single seam a future destroyed-status symbol would change.
 * No symbol is invented here.
 *
 * Arguments:
 *   0: _spec <ARRAY> the live resolved spec [affiliation, markerType,
 *      markerColour, echelon]
 *
 * Return: <ARRAY> the last-known spec, the same four fields.  A malformed or
 * short spec falls back to the unknown affiliation, so a caller never draws
 * a bad marker.
 */
params [
    ["_spec", [], [[]]]
];

private _affiliation = "unknown";
private _markerType = "";
private _markerColour = "ColorUNKNOWN";
private _echelon = "unknown";
if ((count _spec) >= 4) then {
    _affiliation = _spec select 0;
    _markerType = _spec select 1;
    _markerColour = _spec select 2;
    _echelon = _spec select 3;
};

[_affiliation, _markerType, _markerColour, _echelon]
