#include "..\..\script_component.hpp"
/*
 * aee_symbology_fnc_variationResolve
 *
 * Pure variation resolver.  Maps a family id and a selected state to one
 * concrete artifact.  A state is [[optionId, valueId], ...]; every missing
 * option is filled from the family default (the option's first value).  PURE:
 * every input arrives as an argument and the family table is loaded data, so
 * the kernel reads no marker, no unit, no setting and no world.
 *
 * For the symbol family the kernel delegates to FUNC(symbolResolve) with
 * sideUnknown and the mapped affiliation, function (class category), echelon,
 * palette and dimension.  FUNC(symbolResolve) and FUNC(symbologyMarkerType)
 * stay the single source of truth for the marker type and colour; the
 * variation layer only selects their inputs.
 *
 * Arguments:
 *   0: _familyId <STRING> the family id, for example "symbol"
 *   1: _state    <ARRAY>  [[optionId, valueId], ...]
 *
 * Return: <ARRAY> [affiliation, markerType, markerColourClass, echelon].
 */
params [
    ["_familyId", "", [""]],
    ["_state", [], [[]]]
];

private _pairs = [];
if ((count _state) == 0) then {
    // Seed the family id so every option defaults even for an empty state.
    _pairs pushBack [_familyId, "", ""];
} else {
    {
        _pairs pushBack [_familyId, (_x select 0), (_x select 1)];
    } forEach _state;
};

private _normal = [_pairs] call FUNC(variationState);

private _affiliation = "";
private _dimension = "";
private _category = "";
private _echelon = "";
private _palette = "";
{
    private _optionId = _x select 0;
    private _valueId = _x select 1;
    if (_optionId isEqualTo "affiliation") then { _affiliation = _valueId; };
    if (_optionId isEqualTo "dimension") then { _dimension = _valueId; };
    if (_optionId isEqualTo "function") then { _category = _valueId; };
    if (_optionId isEqualTo "echelon") then { _echelon = _valueId; };
    if (_optionId isEqualTo "palette") then { _palette = _valueId; };
} forEach _normal;

[sideUnknown, _category, _affiliation, _echelon, _palette, _dimension] call FUNC(symbolResolve)
