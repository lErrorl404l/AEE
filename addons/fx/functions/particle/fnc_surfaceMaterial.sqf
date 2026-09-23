#include "..\..\script_component.hpp"

/*
Surface material from the ground the unit is standing on.

Classifies an engine surface (the lowercase CfgSurfaces type a map
declares, as fnc_calculateConcealment and fnc_calculateMudAccretion
already read) into a kickup material and its colour.  The engine config
is read-only at run time, so the map's own CfgSurfaces dust value cannot
be changed.  AEE drives its OWN particle emitters instead
(fnc_applyVehicleDust, fnc_applyAtmosphericDust), and those need to know
WHAT is being kicked up: a snow surface must throw snow, sand must throw
sand, dirt must throw dirt.

The class is derived from the surface token, so it is dynamic: a map AEE
has never seen resolves from the surface it declares.  Where the token is
unknown, the ground state and the local terrain colour decide.

Arguments:
  0: surface (STRING, an engine surfaceType, default "") - a surface type
     string, OR a position array, which is sampled
  1: position (ARRAY, PositionWorld, default []) - sampled when the first
     argument is empty

Returns [material, colourRGBA, density]:
  material - "dust" | "sand" | "dirt" | "snow" | "mud" | "spray" | "gravel"
  colour   - the RGB the particles are tinted, with alpha 1 (the caller
             scales alpha by the suppression factor and the setting)
  density  - 0..1 how readily the surface lifts (sand lifts freely, wet
             mud and hard ground lift little)
*/

params [["_surface", "", ["", []]], ["_pos", [], [[]]]];

// A position array in the first argument is the common call: read the
// surface under it.
if (_surface isEqualType []) then {
    private _p = _surface;
    if (count _p >= 3) then { _p = ASLToAGL _p; };
    _surface = surfaceType _p;
};
if (_surface == "" && {count _pos >= 2}) then {
    _surface = surfaceType _pos;
};
private _s = toLower _surface;

// [token, material, colour, density].  Order matters: the first token that
// matches wins, so forest sits above the generic grass entry and snow
// above ice.
private _TABLE = [
    // Snow and ice: white plumes, low lift.
    ["#gdtsnow",        "snow",  [1.00, 1.00, 1.00], 0.55],
    ["#gdtglacier",     "snow",  [0.96, 0.98, 1.00], 0.45],
    ["#gdtice",         "snow",  [0.90, 0.95, 1.00], 0.35],
    // Sand and desert: pale ochre, lifts freely.
    ["#gdtsand",        "sand",  [0.85, 0.76, 0.55], 1.00],
    ["#gdtdunes",       "sand",  [0.87, 0.78, 0.57], 1.00],
    ["#gdtdesert",      "sand",  [0.83, 0.72, 0.52], 0.95],
    ["#gdtbeach",       "sand",  [0.82, 0.76, 0.62], 0.90],
    // Vegetated ground: dark organic, low lift.
    ["#gdtforest",      "dirt",  [0.30, 0.25, 0.18], 0.25],
    ["#gdtconiferous",  "dirt",  [0.28, 0.23, 0.16], 0.25],
    ["#gdtjungle",      "dirt",  [0.26, 0.22, 0.15], 0.30],
    ["#gdtrainforest",  "dirt",  [0.26, 0.22, 0.15], 0.30],
    ["#gdtorchard",     "dirt",  [0.34, 0.28, 0.20], 0.30],
    ["#gdtvineyard",    "dirt",  [0.36, 0.30, 0.22], 0.35],
    ["#gdtcrop",        "dirt",  [0.40, 0.33, 0.24], 0.40],
    ["#gdtfield",       "dirt",  [0.44, 0.36, 0.26], 0.45],
    ["#gdtgrass",       "dirt",  [0.42, 0.36, 0.24], 0.35],
    ["#gdtgrassland",   "dirt",  [0.44, 0.38, 0.25], 0.40],
    ["#gdtprairie",     "dirt",  [0.48, 0.40, 0.27], 0.50],
    ["#gdtthistle",     "dirt",  [0.46, 0.39, 0.26], 0.45],
    ["#gdtweed",        "dirt",  [0.42, 0.35, 0.24], 0.40],
    ["#gdtwildfield",   "dirt",  [0.48, 0.40, 0.27], 0.55],
    ["#gdtdead",        "dirt",  [0.38, 0.31, 0.22], 0.45],
    // Exposed soil and dirt: brown, lifts readily.
    ["#gdtsoil",        "dirt",  [0.45, 0.35, 0.24], 0.70],
    ["#gdtdirt",        "dirt",  [0.44, 0.34, 0.23], 0.75],
    ["#gdtdrygrass",    "dirt",  [0.58, 0.49, 0.31], 0.80],
    // Rock, rubble and scree: grey, moderate lift.
    ["#gdtrock",        "gravel",[0.52, 0.50, 0.47], 0.60],
    ["#gdtmountain",    "gravel",[0.50, 0.48, 0.45], 0.55],
    ["#gdtstony",       "gravel",[0.54, 0.52, 0.49], 0.60],
    ["#gdtgravel",      "gravel",[0.56, 0.53, 0.49], 0.65],
    ["#gdtrubble",      "gravel",[0.58, 0.55, 0.51], 0.70],
    // Wet ground: dark, lifts little.
    ["#gdtmud",         "mud",   [0.30, 0.24, 0.17], 0.20],
    ["#gdtswamp",       "mud",   [0.26, 0.24, 0.18], 0.15],
    ["#gdtmarsh",       "mud",   [0.28, 0.25, 0.19], 0.15],
    // Water feedback on a wet surface.
    ["#gdtwater",       "spray", [0.72, 0.78, 0.82], 0.60],
    ["#gdtseabed",      "spray", [0.55, 0.58, 0.55], 0.20],
    // Built ground: almost no lift.
    ["#gdtconcrete",    "dust",  [0.62, 0.60, 0.56], 0.25],
    ["#gdtasphalt",     "dust",  [0.35, 0.34, 0.33], 0.20],
    ["#gdttarmac",      "dust",  [0.35, 0.34, 0.33], 0.20],
    ["#gdtroad",        "dust",  [0.40, 0.38, 0.36], 0.20]
];

private _material = "dust";
private _colour = [0.55, 0.48, 0.38];
private _density = 0.60;

{
    _x params ["_key", "_mat", "_col", "_den"];
    if (_s find _key >= 0) exitWith {
        _material = _mat;
        _colour = +_col;
        _density = _den;
    };
} forEach _TABLE;

// Unknown token: the ground state decides.  A snow-covered world throws
// snow whatever the surface is called; a dusty one throws dust.
private _state = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
switch (_state) do {
    case "Snow": {
        if (_density > 0.3 && _material != "spray") then {
            _material = "snow";
            _colour = [1, 1, 1];
            _density = _density min 0.55;
        };
    };
    case "Dusty": {
        if (_material == "dirt" || _material == "dust") then {
            _material = "sand";
            _colour = [0.82, 0.72, 0.52];
            _density = _density max 0.85;
        };
    };
    case "Mud": {
        if (_material == "dirt" || _material == "dust") then {
            _material = "mud";
            _colour = [0.30, 0.24, 0.17];
            _density = _density min 0.25;
        };
    };
};

[_material, [_colour select 0, _colour select 1, _colour select 2, 1], _density]
