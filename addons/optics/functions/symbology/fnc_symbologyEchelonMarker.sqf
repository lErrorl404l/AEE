#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_symbologyEchelonMarker
 *
 * Pure echelon-marker kernel.  Maps an echelon token to the CfgMarkers class
 * that carries the echelon overlay.  PURE: the token arrives as an argument,
 * so the kernel reads no config, no marker, no unit and no world.
 *
 * The class name is "AEE_Ech_<Name>".  The overlay is a 64 x 128 texture with
 * the ticks in the top band, so the caller places it above the frame marker.
 *
 * Arguments:
 *   0: _echelon <STRING> an echelon token, for example "squad"
 *
 * Return: <STRING> the CfgMarkers class, for example "AEE_Ech_Squad".
 */
params [
    ["_echelon", "team", [""]]
];

private _names = [
    ["team", "Team"],
    ["squad", "Squad"],
    ["section", "Section"],
    ["platoon", "Platoon"],
    ["company", "Company"],
    ["battalion", "Battalion"],
    ["regiment", "Regiment"],
    ["brigade", "Brigade"],
    ["division", "Division"],
    ["corps", "Corps"],
    ["army", "Army"],
    ["army_group", "Army_Group"],
    ["region", "Region"]
];

private _name = "Team";
private _found = false;
for "_i" from 0 to ((count _names) - 1) do {
    if (!_found && (_echelon isEqualTo ((_names select _i) select 0))) then {
        _name = (_names select _i) select 1;
        _found = true;
    };
};

"AEE_Ech_" + _name
