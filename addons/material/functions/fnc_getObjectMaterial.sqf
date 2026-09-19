#include "..\script_component.hpp"
/*
Get an object's material class via the fallback chain (issue #96).

Objects are MULTI-MATERIAL and the engine does not expose per-selection
materials at runtime: getObjectMaterials returns only setObjectMaterial
OVERRIDES (empty/any for default materials - verified against BIS docs),
so it cannot reveal a model's material.  The authoritative sources are:

  1. Terrain surfaceType - for ground/static objects the #gdt* class is
     the material (the map's own CfgSurfaces)
  2. Config hiddenSelectionsMaterials - for objects that declare
     per-selection materials in their config (buildings, some props)
  3. HitPart-learned surface - the bisurf path of a real impact,
     cached per surface (layer 3, the ACE3 pattern)
  4. default "ground" - the safe neutral class

Arguments:
  0: object (OBJECT)

Return Value:
  STRING - the object's dominant material class
*/

params [["_object", objNull, [objNull]]];

if (isNull _object) exitWith { "ground" };

// 1. Terrain surfaceType for ground-level objects.
if (_object isKindOf "Static" || _object isKindOf "Building") then {
    private _surface = surfaceType (getPosWorld _object);
    if (_surface != "") exitWith { _surface call FUNC(classifyBySurfaceType) };
};

// 2. Config hiddenSelectionsMaterials (per-selection, declared).
private _cfgObj = configOf _object;
private _selMats = getArray (_cfgObj >> "hiddenSelectionsMaterials");
if (_selMats isNotEqualTo []) then {
    // Classify the first real material path; majority vote if many.
    private _votes = createHashMap;
    {
        private _mat = toLower _x;
        if (_mat != "" && _mat isNotEqualTo "any") then {
            private _cls = _mat call FUNC(getSurfaceMaterial);
            _votes set [_cls, (_votes getOrDefault [_cls, 0]) + 1];
        };
    } forEach _selMats;
    private _best = "ground";
    private _bestN = 0;
    {
        if ((_y) > _bestN) then { _best = _x; _bestN = _y; };
    } forEach _votes;
    if (_bestN > 0) exitWith { _best };
};

// 3. HitPart-learned surface cache (per object class, from real impacts).
private _class = typeOf _object;
private _learned = GVAR(classCache) get _class;
if !(isNil "_learned") exitWith { _learned };

// 4. Safe default.
"ground"
