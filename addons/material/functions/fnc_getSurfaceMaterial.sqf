#include "..\script_component.hpp"
/*
Classify a surface identifier (bisurf path or CfgSurfaces class) into
an AEE material class (issue #96, layer 3).

The surface identifier is the 6th parameter of the projectile HitPart
event: either a CfgSurfaces class name or a .bisurf file path.  This is
the ACE3 frag pattern (ace_frag_fnc_getMaterialInfo): look up the
cache, else read the config/bisurf content, extract the material via
the soundEnviron/soundHit field, and cache the result.

Fallback chain (fastest -> slowest, most specific -> default):
  1. materialCache: preloaded vanilla bisurf paths (fnc_initMaterialCache)
  2. CfgSurfaces: the class exists in CfgSurfaces -> soundEnviron (or
     soundHit) text carries the material keyword
  3. preprocessFile: read the .bisurf text, extract soundHit keyword
  4. default "ground" (ACE3 convention; safest neutral class)

Arguments:
  0: surface identifier (STRING) - CfgSurfaces class or bisurf path

Return Value:
  STRING - one of: ground, rock, wood, concrete, metal, glass, water,
  vegetation

Example:
  "a3\data_f\penetration\concrete.bisurf" call aee_material_fnc_getSurfaceMaterial
  -> "concrete"
*/

#define SOUNDHIT_SEARCH_LEN 12

params [["_surfId", "", [""]]];

if (_surfId == "" || _surfId == "any") exitWith { "ground" };

// 1. Cache hit (preloaded vanilla paths or learned classes).
private _cached = GVAR(materialCache) get _surfId;
if !(isNil "_cached") exitWith { _cached };

// 2. CfgSurfaces class - the soundEnviron/soundHit fields carry the
//    material keyword.
private _surfaceConfig = configFile >> "CfgSurfaces" >> _surfId;
private _keyword = "";
if (isClass _surfaceConfig) then {
    _keyword = toLowerANSI getText (_surfaceConfig >> "soundEnviron");
    if (_keyword == "" || _keyword == "empty") then {
        _keyword = toLowerANSI getText (_surfaceConfig >> "soundhit");
    };
} else {
    // 3. Read the bisurf file directly.  The engine resolves the path
    //    case-insensitively; preprocessFile returns the text as-is.
    //    GUARD: only a real file path is read - a bare class name
    //    (surfaceType returns e.g. 'GdtStratisConcrete' which may not
    //    be in CfgSurfaces AND is not a file) must NOT be passed to
    //    preprocessFile, or it warns 'Script X not found' (issue #204,
    //    the 'Script stratisconcrete not found' RPT error).
    if ("\\" in _surfId || {"/" in _surfId} || {".bisurf" in _surfId}) then {
        private _text = toLowerANSI preprocessFile _surfId;
        _text = _text regexReplace ["[^a-z0-9]", ""];
        private _idx = 8 + (_text find "soundhit");
        _keyword = _text select [_idx, SOUNDHIT_SEARCH_LEN];
    };
};

// 4. Classify the keyword into an AEE material class.
private _material = switch (true) do {
    case ("metal" in _keyword): { "metal" };
    case ("concrete" in _keyword): { "concrete" };
    case ("wood" in _keyword): { "wood" };
    case ("glass" in _keyword): { "glass" };
    case ("granite" in _keyword): { "rock" };
    case ("rock" in _keyword): { "rock" };
    case ("gravel" in _keyword): { "rock" };
    case ("water" in _keyword): { "water" };
    case ("foliage" in _keyword): { "vegetation" };
    case ("grass" in _keyword): { "vegetation" };
    case ("hay" in _keyword): { "vegetation" };
    case ("dirt" in _keyword): { "ground" };
    case ("ground" in _keyword): { "ground" };
    default { "ground" };
};

GVAR(materialCache) set [_surfId, _material];
_material
