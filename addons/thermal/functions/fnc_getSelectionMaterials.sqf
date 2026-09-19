#include "..\script_component.hpp"
/*
Per-selection material class (issue #124).

Maps ONE model selection to its AEE material class by reading the
selection's own rvmat path from hiddenSelectionsMaterials and running
it through the #96 detector.  A vehicle is not one material: body =
metal, windows = glass, tyres = rubber, wheels = rubber+metal.  A unit
is not one material either: uniform = cloth, vest = ceramic/leather,
helmet = plastic, goggles = glass, boots = leather.  Per-selection
classification is what makes the temperature solve and the thermal
image physically distinct per part.

Resolution order (mirrors fnc_getObjectMaterial's fallback chain):
  1. hiddenSelectionsMaterials[selIdx] -> the selection's own rvmat
     path -> read its surfaceInfo field -> classify the bisurf via the
     #96 detector (the engine's authoritative physics surface; works
     for ANY rvmat regardless of filename)
  2. if the rvmat has no surfaceInfo (shared/default materials), the
     selection NAME is matched against known material keywords (glass,
     wheel, tyre, engine, motor, light) - model conventions, not the
     object class
  3. fallback: the object-wide #96 classification

The result is cached per [class, selection] so the per-selection solve
runs once per tick without re-reading config every time.

Arguments:
  0: object (OBJECT)
  1: selection name (STRING)

Return Value:
  STRING material class - one of the #96 classes (ground/rock/wood/
  concrete/metal/glass/water/vegetation, plus engine/rubber/plastic/
  leather/human for the thermal registry)
*/

params [
    ["_obj", objNull, [objNull]],
    ["_selName", "", [""]]
];
if (isNull _obj || _selName == "") exitWith { "ground" };

private _cacheKey = format ["%1|%2", typeOf _obj, _selName];
private _cached = GVAR(selMaterialCache) getOrDefault [_cacheKey, ""];
if (_cached != "") exitWith { _cached };

if (isNil QGVAR(selMaterialCache)) then {
    GVAR(selMaterialCache) = createHashMap;
};

private _class = "";
private _idx = -1;
private _hsMats = getArray (configOf _obj >> "hiddenSelectionsMaterials");
private _hs = getArray (configOf _obj >> "hiddenSelections");

// ─── 1. The selection's own rvmat -> surfaceInfo -> bisurf -> class ──────
// Filenames lie (mrap_01_body.rvmat is metal, default.rvmat is any).
// The authoritative chain is: rvmat declares surfaceInfo = "...bisurf";
// the bisurf is the engine's physics surface (density, soundHit keyword);
// the #96 detector classifies that.  This works for ANY rvmat regardless
// of what the file is named.
if (_hs isNotEqualTo []) then {
    _idx = _hs find _selName;
    if (_idx >= 0 && _idx < (count _hsMats)) then {
        private _rvmat = _hsMats select _idx;
        if (_rvmat != "" && _rvmat isNotEqualTo "any") then {
            // Read the rvmat text, extract surfaceInfo, classify the bisurf.
            private _text = toLowerANSI preprocessFile _rvmat;
            if (_text != "") then {
                private _pos = _text find "surfaceinfo";
                if (_pos >= 0) then {
                    private _tail = _text select [_pos + 11, 120];
                    private _end = _tail find ">";
                    if (_end < 0) then { _end = (count _tail) - 1; };
                    private _surfRef = trim (_tail select [0, _end]);
                    if (_surfRef != "") then {
                        _class = _surfRef call EFUNC(material,getSurfaceMaterial);
                    };
                };
            };
        };
    };
};

// ─── 2. Selection-name conventions (no config materials) ─────────────────
if (_class == "") then {
    private _sel = toLower _selName;
    if (_sel find "glass" >= 0 || {_sel find "window" >= 0} || {_sel find "light" >= 0}) then {
        _class = "glass";
    } else {
        if (_sel find "wheel" >= 0 || {_sel find "tyre" >= 0} || {_sel find "tire" >= 0}) then {
            _class = "rubber";
        } else {
            if (_sel find "motor" >= 0 || {_sel find "engine" >= 0}) then {
                _class = "engine";
            };
        };
    };
};

// ─── 3. Fallback: object-wide classification ─────────────────────────────
if (_class == "") then {
    _class = _obj call EFUNC(material,getObjectMaterial);
};

GVAR(selMaterialCache) set [_cacheKey, _class];
_class
