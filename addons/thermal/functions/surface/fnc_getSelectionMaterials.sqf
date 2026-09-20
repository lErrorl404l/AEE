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

private _class = "";
private _idx = -1;
private _hsMats = getArray (configOf _obj >> "hiddenSelectionsMaterials");
private _hs = getArray (configOf _obj >> "hiddenSelections");

// Full part tree (issue #204): every model exposes its parts at runtime
// even when the config omits hiddenSelections/hiddenSelectionsMaterials.
// selectionNames + getObjectMaterials give the runtime part tree; index
// into them the same way the config path does.  This is the "always has
// a full tree of textures and materials" guarantee.
private _runtimeNames = selectionNames _obj;
private _runtimeMats = getObjectMaterials _obj;
if (_hs isEqualTo [] && {_runtimeNames isNotEqualTo []}) then {
    _hs = _runtimeNames;
    // getObjectMaterials returns one rvmat per hiddenSelection in order.
    if (count _runtimeMats >= count _hs) then {
        _hsMats = _runtimeMats;
    };
};

// ─── 1. The selection's own rvmat -> surfaceInfo -> bisurf -> class ──────
// Filenames lie (mrap_01_body.rvmat is metal, default.rvmat is any).
// The authoritative chain is: rvmat declares surfaceInfo = "...bisurf";
// the bisurf is the engine's physics surface (density, soundHit keyword);
// the #96 detector classifies that.  This works for ANY rvmat regardless
// of what the file is named.
private _rvmat = "";
if (_hs isNotEqualTo []) then {
    _idx = _hs find _selName;
    if (_idx >= 0 && _idx < (count _hsMats)) then {
        _rvmat = _hsMats select _idx;
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

// ─── 1b. rvmat-content classification (issue #204) ────────────────────────
// Every part of every object has its OWN rvmat (hiddenSelectionsMaterials
// gives the full tree).  When the rvmat has no surfaceInfo (shared or
// procedural materials), classify the part from the rvmat's own rendering
// properties - NOT the selection name.  Glass rvmats carry a high
// specular term and translucent Stage1; rubber is dark low-specular;
// metal has a strong specularPower; emissive parts (lights, gauges) glow.
// This is the rvmat-driven classification the user asked for: the
// material comes from the part's actual rendering, so any object - any
// mod, any model - resolves its parts by what they are, not what they
// are named.
if (_class == "" && _rvmat != "" && _rvmat isNotEqualTo "any") then {
    private _text = toLowerANSI preprocessFile _rvmat;
    // Binary rvmat detection: the vanilla game ships compiled rvmats
    // ("raP" magic bytes - the RV binary config format).  preprocessFile
    // returns the raw bytes, which contain no text keywords, so the
    // TEXT branch would find nothing and the part would fall to ground.
    // Detect the magic and route to the texture-path classification.
    private _isBinary = (_text find "rap" >= 0) || {_text find "staget1" < 0 && _text find "ambient[]" < 0};
    if (_text == "" || _isBinary) then {
        // BINARY rvmat: the material signal survives in the Stage1
        // TEXTURE PATH, which getObjectTextures returns at runtime as
        // readable text.  The texture path carries the material keyword
        // (offroad_01_EXT_co = metal exterior, offroad_01_GLASS = glass,
        // *_int = interior, *_wheel/tyre = rubber).
        private _texPath = (getObjectTextures _obj) param [_idx, ""];
        if (_texPath == "") then {
            _texPath = getText (configOf _obj >> "hiddenSelectionsTextures" >> format ["%1", _idx]);
        };
private _tl = toLower _texPath;
        if (_tl != "") then {
            // Explicit material keywords from the texture path (the
            // model's own part names - dynamic per model, not the
            // selection-name heuristic).
            if (_tl find "glass" >= 0 || {_tl find "window" >= 0} || {_tl find "screen" >= 0} || {_tl find "light" >= 0}) then {
                _class = "glass";
            } else {
                if (_tl find "wheel" >= 0 || {_tl find "tyre" >= 0} || {_tl find "tire" >= 0} || {_tl find "track" >= 0}) then {
                    _class = "rubber";
                } else {
                    if (_tl find "engine" >= 0 || {_tl find "motor" >= 0} || {_tl find "radiator" >= 0}) then {
                        _class = "engine";
                    } else {
                        if (_tl find "int" >= 0) then {
                            _class = "plastic";   // interior trim
                        } else {
                            if (_tl find "wood" >= 0) then { _class = "wood"; };
                        };
                    };
                };
            };
            // DEFAULT for vehicle exterior parts (the survey: ext/body/
            // door/hood/roof textures are metal - bright red TI maps).
            // A binary rvmat with no explicit keyword and no interior/
            // glass/wheel marker is a metal panel.  This is what makes
            // the Offroad/MRAP hulls read as metal instead of ground.
            if (_class == "" && !(_obj isKindOf "Man")) then {
                _class = "metal";
            };
        };
    } else {
        // TEXT rvmat: parse the rendering properties.
        // Emissive: lights, displays, heated elements - the material
        // glows (a strong thermal signature even cold).
        if (_text find "emmisive" >= 0) then {
            private _em = _text find "emmisive";
            private _tail2 = _text select [_em + 9, 60];
            // emissive {0,0,0,...} = dark/off; emissive with a real
            // value = a light source.
            if (_tail2 find "0,0,0" < 0) then { _class = "engine"; };
        };
        // Glass: translucent - Stage1 has an alpha blend, specular
        // present, no metal specularPower.  "glass" rvmats carry
        // specular[] with alpha and a low specularPower.
        if (_class == "" && {_text find "specular" >= 0}) then {
            private _sp = _text find "specularpower";
            private _spVal = if (_sp >= 0) then {
                private _t = _text select [_sp + 13, 30];
                private _e = _t find ";";
                if (_e < 0) then { _e = count _t - 1; };
                parseNumber (_t select [0, _e])
            } else { 0 };
            if (_spVal < 5 && {_text find "diffuse" >= 0}) then {
                _class = "glass";
            };
        };
        // Rubber/plastic: low specularPower, dark diffuse.
        if (_class == "" && {_text find "specularpower" >= 0}) then {
            private _sp = _text find "specularpower";
            private _t = _text select [_sp + 13, 30];
            private _e = _t find ";";
            if (_e < 0) then { _e = count _t - 1; };
            private _spVal = parseNumber (_t select [0, _e]);
            if (_spVal < 20 && {_text find "diffuse" >= 0}) then {
                _class = "rubber";
            };
        };
    };
};

// ─── 1c. Hit-point verification (issue #204) ──────────────────────────────
// The vehicle's DAMAGE MODEL guarantees what its parts are: HitLFWheel
// can only exist on a wheel, HitEngine on the engine, HitGlass on
// glass.  The hit-point map (cached per class) is the engine's own
// part labels - more authoritative than a texture path.  Consult it
// before the name-matching fallback.
if (_class == "" && {_obj isKindOf "AllVehicles"}) then {
    private _hpMap = [_obj] call FUNC(getHitPointMaterials);
    if (count _hpMap > 0) then {
        private _hpMat = _hpMap getOrDefault [_selName, ""];
        if (_hpMat != "") then { _class = _hpMat; };
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

(missionNamespace getVariable [QGVAR(selMaterialCache), createHashMap]) set [_cacheKey, _class];
_class
