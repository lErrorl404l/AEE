#include "..\..\script_component.hpp"
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
private _cached = (missionNamespace getVariable [QGVAR(selMaterialCache), createHashMap]) getOrDefault [_cacheKey, ""];
if (_cached != "") exitWith { _cached };

if (isNil QGVAR(selMaterialCache)) then {
    missionNamespace setVariable [QGVAR(selMaterialCache), createHashMap];
};

// ─── Signal gathering + weighted vote (issue #204) ───────────────────────
// The user's requirement: pull EVERYTHING about the part, then sort
// through what is found - do not grab the first match or bias one
// signal.  Each signal votes for a material with a weight:
//   surfaceInfo (rvmat -> bisurf)  weight 3 - the engine's authoritative
//                                     physics surface, when readable
//   hit-point (damage model)        weight 3 - HitLFWheel is guaranteed
//   texture-path keyword            weight 2 - the model's own part names
//   selection-name convention       weight 1 - last resort
// The highest weighted vote wins; ties resolved by the strongest
// source.  This removes the first-match bias entirely.
private _idx = -1;
private _hsMats = getArray (configOf _obj >> "hiddenSelectionsMaterials");
private _hs = getArray (configOf _obj >> "hiddenSelections");

// Full part tree: every model exposes its parts at runtime even when the
// config omits hiddenSelections/hiddenSelectionsMaterials.
private _runtimeNames = selectionNames _obj;
private _runtimeMats = getObjectMaterials _obj;
if (_hs isEqualTo [] && {_runtimeNames isNotEqualTo []}) then {
    _hs = _runtimeNames;
    if (count _runtimeMats >= count _hs) then { _hsMats = _runtimeMats; };
};

// The vote ledger: material -> total weight.
private _votes = createHashMap;

// ─── Signal 1: the rvmat surfaceInfo (weight 3) ──────────────────────────
private _rvmat = "";
if (_hs isNotEqualTo []) then {
    _idx = _hs find _selName;
    if (_idx >= 0 && _idx < (count _hsMats)) then {
        _rvmat = _hsMats select _idx;
        if (_rvmat != "" && _rvmat isNotEqualTo "any") then {
            private _text = toLowerANSI preprocessFile _rvmat;
            if (_text != "") then {
                private _pos = _text find "surfaceinfo";
                if (_pos >= 0) then {
                    private _tail = _text select [_pos + 11, 120];
                    private _end = _tail find ">";
                    if (_end < 0) then { _end = (count _tail) - 1; };
                    private _surfRef = trim (_tail select [0, _end]);
                    if (_surfRef != "") then {
                        private _m = _surfRef call EFUNC(material,getSurfaceMaterial);
                        if (_m != "ground") then {
                            _votes set [_m, (_votes getOrDefault [_m, 0]) + 3];
                        };
                    };
                };
            };
        };
    };
};

// ─── Signal 2: the texture path (weight 2, binary-rvmat friendly) ────────
// The Stage1 texture path carries the model's part names.  For binary
// rvmats (all vanilla) this is the only readable rvmat signal.
private _texPath = if (_idx >= 0) then { (getObjectTextures _obj) param [_idx, ""] } else { "" };
if (_texPath == "" && _idx >= 0) then {
    _texPath = getText (configOf _obj >> "hiddenSelectionsTextures" >> _selName);
};
private _tl = toLower _texPath;
if (_tl != "") then {
    private _tMat = "";
    if (_tl find "glass" >= 0 || {_tl find "window" >= 0} || {_tl find "screen" >= 0} || {_tl find "light" >= 0}) then {
        _tMat = "glass";
    } else {
        if (_tl find "wheel" >= 0 || {_tl find "tyre" >= 0} || {_tl find "tire" >= 0} || {_tl find "track" >= 0}) then {
            _tMat = "rubber";
        } else {
            if (_tl find "engine" >= 0 || {_tl find "motor" >= 0} || {_tl find "radiator" >= 0}) then {
                _tMat = "engine";
            } else {
                if (_tl find "int" >= 0) then { _tMat = "plastic"; }
                else { if (_tl find "wood" >= 0) then { _tMat = "wood"; }; };
            };
        };
    };
    if (_tMat != "") then {
        _votes set [_tMat, (_votes getOrDefault [_tMat, 0]) + 2];
    } else {
        // No keyword: a vehicle exterior defaults to metal (the survey:
        // ext/body textures are bright-red TI maps = metal panels).
        if !(_obj isKindOf "Man") then {
            _votes set ["metal", (_votes getOrDefault ["metal", 0]) + 2];
        };
    };
};

// ─── Signal 3: the hit-point verification (weight 3, guaranteed) ─────────
if (_obj isKindOf "AllVehicles") then {
    private _hpMap = [_obj] call FUNC(getHitPointMaterials);
    if (count _hpMap > 0) then {
        private _hpMat = _hpMap getOrDefault [_selName, ""];
        if (_hpMat != "") then {
            _votes set [_hpMat, (_votes getOrDefault [_hpMat, 0]) + 3];
        };
    };
};

// ─── Signal 4: the selection-name convention (weight 1, last resort) ─────
private _sel = toLower _selName;
private _nMat = "";
if (_sel find "glass" >= 0 || {_sel find "window" >= 0} || {_sel find "light" >= 0}) then {
    _nMat = "glass";
} else {
    if (_sel find "wheel" >= 0 || {_sel find "tyre" >= 0} || {_sel find "tire" >= 0}) then {
        _nMat = "rubber";
    } else {
        if (_sel find "motor" >= 0 || {_sel find "engine" >= 0}) then { _nMat = "engine"; };
    };
};
if (_nMat != "") then {
    _votes set [_nMat, (_votes getOrDefault [_nMat, 0]) + 1];
};

// ─── Decide: the highest weighted vote wins ───────────────────────────────
private _class = "";
private _bestN = 0;
{
    if ((_y) > _bestN) then { _class = _x; _bestN = _y; };
} forEach _votes;
if (_class == "") then { _class = _obj call EFUNC(material,getObjectMaterial); };
if (_class == "") then { _class = "ground"; };

(missionNamespace getVariable [QGVAR(selMaterialCache), createHashMap]) set [_cacheKey, _class];
_class
