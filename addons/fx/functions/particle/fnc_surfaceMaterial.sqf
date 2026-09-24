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
// surfaceType returns the class name with no '#' prefix (GdtSnow);
// normalise to the bare token, then match the exact surface token.
private _s = toLower _surface;
if (_s find "#gdt" == 0) then { _s = _s select [4]; }
else { if (_s find "gdt" == 0) then { _s = _s select [3]; }; };

// [token, material, colour, density].  The token is the bare surface
// class name, matched as a PREFIX (the original '#gdt'-anchored keys were
// prefix anchors: #gdtsnow matched #gdtsnowsurface but never #gdtdrygrass).
private _TABLE = [
    // Snow and ice: white plumes, low lift.
    ["snow",        "snow",  [1.00, 1.00, 1.00], 0.55],
    ["glacier",     "snow",  [0.96, 0.98, 1.00], 0.45],
    ["ice",         "snow",  [0.90, 0.95, 1.00], 0.35],
    // Sand and desert: pale ochre, lifts freely.
    ["sand",        "sand",  [0.85, 0.76, 0.55], 1.00],
    ["dunes",       "sand",  [0.87, 0.78, 0.57], 1.00],
    ["desert",      "sand",  [0.83, 0.72, 0.52], 0.95],
    ["beach",       "sand",  [0.82, 0.76, 0.62], 0.90],
    // Vegetated ground: dark organic, low lift.
    ["forest",      "dirt",  [0.30, 0.25, 0.18], 0.25],
    ["coniferous",  "dirt",  [0.28, 0.23, 0.16], 0.25],
    ["jungle",      "dirt",  [0.26, 0.22, 0.15], 0.30],
    ["rainforest",  "dirt",  [0.26, 0.22, 0.15], 0.30],
    ["orchard",     "dirt",  [0.34, 0.28, 0.20], 0.30],
    ["vineyard",    "dirt",  [0.36, 0.30, 0.22], 0.35],
    ["crop",        "dirt",  [0.40, 0.33, 0.24], 0.40],
    ["field",       "dirt",  [0.44, 0.36, 0.26], 0.45],
    ["grass",       "dirt",  [0.42, 0.36, 0.24], 0.35],
    ["grassland",   "dirt",  [0.44, 0.38, 0.25], 0.40],
    ["prairie",     "dirt",  [0.48, 0.40, 0.27], 0.50],
    ["thistle",     "dirt",  [0.46, 0.39, 0.26], 0.45],
    ["weed",        "dirt",  [0.42, 0.35, 0.24], 0.40],
    ["wildfield",   "dirt",  [0.48, 0.40, 0.27], 0.55],
    ["dead",        "dirt",  [0.38, 0.31, 0.22], 0.45],
    // Exposed soil and dirt: brown, lifts readily.
    ["soil",        "dirt",  [0.45, 0.35, 0.24], 0.70],
    ["dirt",        "dirt",  [0.44, 0.34, 0.23], 0.75],
    ["drygrass",    "dirt",  [0.58, 0.49, 0.31], 0.80],
    // Rock, rubble and scree: grey, moderate lift.
    ["rock",        "gravel",[0.52, 0.50, 0.47], 0.60],
    ["mountain",    "gravel",[0.50, 0.48, 0.45], 0.55],
    ["stony",       "gravel",[0.54, 0.52, 0.49], 0.60],
    ["gravel",      "gravel",[0.56, 0.53, 0.49], 0.65],
    ["rubble",      "gravel",[0.58, 0.55, 0.51], 0.70],
    // Wet ground: dark, lifts little.
    ["mud",         "mud",   [0.30, 0.24, 0.17], 0.20],
    ["swamp",       "mud",   [0.26, 0.24, 0.18], 0.15],
    ["marsh",       "mud",   [0.28, 0.25, 0.19], 0.15],
    // Water feedback on a wet surface.
    ["water",       "spray", [0.72, 0.78, 0.82], 0.60],
    ["seabed",      "spray", [0.55, 0.58, 0.55], 0.20],
    // Built ground: almost no lift.
    ["concrete",    "dust",  [0.62, 0.60, 0.56], 0.25],
    ["asphalt",     "dust",  [0.35, 0.34, 0.33], 0.20],
    ["tarmac",      "dust",  [0.35, 0.34, 0.33], 0.20],
    ["road",        "dust",  [0.40, 0.38, 0.36], 0.20]
];

private _material = "dust";
private _colour = [0.55, 0.48, 0.38];
private _density = 0.60;

{
    _x params ["_key", "_mat", "_col", "_den"];
    if (_s find _key == 0) exitWith {
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
