#include "..\script_component.hpp"
/*
 * aee_lib_fnc_roughnessLength
 *
 * Aerodynamic roughness length z0 of the ground at a position, from the
 * revised Davenport classification (Wieringa 1992, J Wind Eng Ind Aerodyn
 * 41:357; WMO-No. 8 Part I ch. 5 annex): sea 0.0002 m, smooth (snow, sand,
 * paving, ice) 0.005, open grass 0.03, low crops / bare soil 0.1, rough
 * (rock, scrub) 0.25, closed (forest) 1.0, matched on the surface name.
 * CfgSurfaces `rough` is the vehicle ground-bumpiness parameter, not an
 * aerodynamic roughness, so it is not used.
 *
 * Arguments: 0: position (ARRAY, ASL or AGL)
 * Return: z0, m
 */
params [["_pos", [0, 0, 0], [[]]]];
if (surfaceIsWater _pos) exitWith { 0.0002 };
private _snow = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
if !(_snow isEqualType 0) then { _snow = 0; };
if (_snow > 0.05) exitWith { 0.005 };
private _name = toLower (surfaceType _pos);
private _z0 = 0.1;
{
    if ((_name find (_x select 0)) >= 0) exitWith { _z0 = _x select 1; };
} forEach [
    ["forest", 1.0], ["wood", 1.0], ["thicket", 1.0],
    ["asphalt", 0.005], ["tarmac", 0.005], ["concrete", 0.005], ["runway", 0.005],
    ["sand", 0.005], ["beach", 0.005], ["desert", 0.005], ["ice", 0.005], ["snow", 0.005],
    ["grass", 0.03], ["meadow", 0.03], ["field", 0.03],
    ["crop", 0.1], ["dirt", 0.1], ["soil", 0.1], ["mud", 0.1], ["gravel", 0.1],
    ["rock", 0.25], ["stony", 0.25], ["bush", 0.25], ["weed", 0.25]
];
_z0
