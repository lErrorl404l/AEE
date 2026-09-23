#include "..\script_component.hpp"

/*
Terrain speed factor for the surface under a vehicle (issue #117).

The published cross-country speed classes, as a fraction of the road speed.
A surface is classified from the engine's own CfgSurfaces data, so a new
terrain or a modded map resolves without a code change.

  The class list is the published military band (FM 5-430-00-1 Ch. 7 and
  the standard cross-country planning figures):
    road 1.00, trail/gravel 0.60-0.75, field 0.40-0.55,
    woodland 0.25-0.40, swamp/marsh 0.10-0.20, sand 0.15-0.30,
    snow/ice 0.10-0.50.

  Classification order (most specific first):
    1. Water: surfaceIsWater, or a marsh/seabed surface class.
    2. The CfgSurfaces surfaceFriction, when the class carries one.
    3. The surface CLASS NAME, matched by keyword (Marsh, Mud, Sand,
       Grass, Forest, Rock, Concrete, Asphalt, Snow, Ice, ...).
    4. The material class from fnc_classifyBySurfaceType (the repo's own
       taxonomy), which already resolves a surface token across the maps.

  The engine's surfaceFriction runs the opposite way to the speed factor
  (lower friction = more grip in the Arma convention), so it is mapped,
  not used directly.

Arguments:
  0: position (ARRAY) - the [x, y] or PositionASL to classify

Return Value: NUMBER - the speed factor, 0.05 to 1.0
Example: [getPos player] call aee_mobility_fnc_getTerrainSpeedFactor
Public: No
*/

params [["_pos", [], [[]]]];

if (_pos isEqualTo []) exitWith { 1 };

// ─── Water ───────────────────────────────────────────────────────────────
private _pos2D = if ((count _pos) >= 2) then { [_pos select 0, _pos select 1] } else { _pos };
if (surfaceIsWater _pos2D) exitWith { 0.05 };

// ─── The surface class ───────────────────────────────────────────────────
// surfaceType returns the class name; the Arma 3 names are capitalised and
// carry no '#' prefix (verified against the ACE wiki).  Normalise first.
private _raw = toLower (surfaceType _pos2D);
private _name = _raw;
if (_name find "#gdt" == 0) then { _name = _name select [4]; }
else { if (_name find "gdt" == 0) then { _name = _name select [3]; }; };

// ─── Keyword match on the class name ─────────────────────────────────────
// Ordered most restrictive first: a soft surface must win over the material
// keyword that follows it in the name (SoftMud before Mud).
private _factor = 0;
{
    if (_name find (_x select 0) >= 0) exitWith {
        _factor = _x select 1;
    };
} forEach [
    ["marsh",    0.15],
    ["swamp",    0.10],
    ["seabed",   0.05],
    ["mud",      0.25],
    ["clay",     0.25],
    ["sand",     0.25],
    ["beach",    0.30],
    ["snow",     0.35],
    ["ice",      0.15],
    ["glacier",  0.15],
    ["tundra",   0.40],
    ["rock",     0.45],
    ["stony",    0.45],
    ["gravel",   0.60],
    ["forest",   0.35],
    ["weed",     0.55],
    ["field",    0.50],
    ["grass",    0.55],
    ["dirt",     0.65],
    ["soil",     0.65],
    ["asphalt",  1.00],
    ["tarmac",   1.00],
    ["concrete", 0.90],
    ["cobble",   0.85],
    ["road",     1.00],
    ["runway",   1.00],
    ["default",  0.70]
];

// ─── Surface friction, when the class carries one ────────────────────────
// CfgSurfaces is read-only at run time, so this is a read, not a write.
// The engine convention is that a LOWER surfaceFriction gives MORE grip, so
// a high friction value means a slippery surface and a lower speed.
if (_factor == 0 && _name != "") then {
    // Rebuild the config class name: the engine class is the original with
    // its case, which the lower-case form cannot address, so try both.
    private _cfg = configFile >> "CfgSurfaces" >> _name;
    if (!isClass _cfg && {count _raw > 0}) then {
        _cfg = configFile >> "CfgSurfaces" >> _raw;
    };
    if (isClass _cfg) then {
        private _sf = getNumber (_cfg >> "surfaceFriction");
        if (_sf > 0) then {
            // 1.0 nominal -> 0.7; 2.5 tarmac -> 1.0; 0.5 soft -> 0.4.
            _factor = ((_sf / 2.5) max 0.1 min 1.0);
        };
    };
};

// ─── The material taxonomy, if the name told us nothing ──────────────────
if (_factor == 0) then {
    private _mat = [_name] call EFUNC(material,classifyBySurfaceType);
    _factor = switch (_mat) do {
        case "asphalt":    { 1.00 };
        case "concrete":   { 0.90 };
        case "water":      { 0.10 };
        case "vegetation": { 0.50 };
        case "rock":       { 0.45 };
        case "wood":       { 0.60 };
        case "metal":      { 0.90 };
        default            { 0.70 };
    };
};

// ─── Ground state override ───────────────────────────────────────────────
// The five-state classifier already collapses the surface into the states
// that matter for traction, so it caps the factor.
private _ground = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
_factor = switch (_ground) do {
    case "Mud":    { _factor min 0.35 };
    case "Snow":   { _factor min 0.35 };
    case "Frozen": { _factor min 0.45 };
    case "Dusty":  { _factor min 0.70 };
    default        { _factor };
};

_factor = _factor max 0.05 min 1.0;
_factor
