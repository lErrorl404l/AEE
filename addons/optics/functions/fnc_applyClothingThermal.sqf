#include "..\script_component.hpp"
/*
 * Per-clothing thermal material override for infantry.
 *
 * The engine composites each equipped clothing item's TI texture onto the
 * wearer: the ghillie suit hides the wearer because ghillie.p3d references
 * ghillie_ti.paa (a cold TI map).  This is the per-item thermal mechanism.
 *
 * We drive it from AEE's physics: clothing insulation + ambient determine
 * whether the item reads warm (insulated, cold ambient -> body heat kept
 * in) or cold (light clothing, cold ambient -> near ambient).  The item's
 * material is swapped to one referencing a different TI texture (cold or
 * hot), exactly like a ghillie hides you.  A3TI does the material swap for
 * Man (fn_getThermalSelections + setObjectMaterial); we make it physics-
 * driven and cover ALL units, not a radius.
 *
 * Multiplayer: setObjectMaterial is LOCAL, which is correct here.  Each
 * client renders its own thermal pass and computes identical physics
 * (weather, insulation), so each client applies the same swap locally and
 * every player sees the same thermal appearance.  No network traffic.
 *
 * Cost: the swap is a one-shot state change per physics change (throttled
 * to 0.05 in tiScale), NOT per-frame.  All units are scanned because there
 * is no reason for a range limit: a one-shot swap across the whole unit
 * list is cheap, and a 150 m radius would leave far targets at vanilla
 * baked thermal for no physical reason.
 *
 * Restored on EXIT (mode "EXIT") to the saved originals.
 */
params ["_mode"];

if (!hasInterface) exitWith { 0 };

// ─── EXIT: restore every saved material ───────────────────────────────────
if (_mode == "EXIT") then {
    private _saved = missionNamespace getVariable [QGVAR(tiClothSaved), []];
    {
        _x params ["_o", "_oldMats", "_thermalSelections"];
        if (!isNull _o) then {
            {
                _o setObjectMaterial [_x, _oldMats select _x];
            } forEach _thermalSelections;
        };
    } forEach _saved;
    missionNamespace setVariable [QGVAR(tiClothSaved), []];
    missionNamespace setVariable [QGVAR(tiClothScale), -1];
    0
};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── Physics inputs ────────────────────────────────────────────────────────
// Thermal resistance: clothing insulation + ambient.  Cold ambient + heavy
// insulation -> wearer stays warm -> TI reads warm.  Cold + light clothing
// -> TI reads cold (near ambient).  Hot ambient -> everything hot.
//
// Scale model: insulation 0..1 sets the base; the ambient term shifts it
// by up to ±0.5 across the -15..45 C operating range (0.5 x 30 C span /
// 60 C range = 0.5 max).  So:
//   light clothing at 5 C     -> 0.2 - 0.17 = 0.03  (cold)
//   heavy kit at 5 C          -> 0.8 - 0.17 = 0.63  (warm, neutral band)
//   light clothing at 45 C    -> 0.2 + 0.5 = 0.70   (hot)
//   heavy kit at 45 C         -> 0.8 + 0.5 = 1.30   (hot, clamped)
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _insulation = missionNamespace getVariable [QEGVAR(physiology,clothingInsulation), 0.5];
if !(_insulation isEqualType 0) then { _insulation = 0.5; };
private _ambientTerm = (0.5 * (_airTemp - 15) / 30) min 0.5 max -0.5;
private _tiScale = _insulation + _ambientTerm;

// Throttle: only rescan all units when the physics changed materially.
private _lastScale = missionNamespace getVariable [QGVAR(tiClothScale), -1];
if (!(_lastScale isEqualType 0)) then { _lastScale = -1; };
if (abs (_tiScale - _lastScale) < 0.05) exitWith { 0 };
missionNamespace setVariable [QGVAR(tiClothScale), _tiScale];

// ─── Material selection ────────────────────────────────────────────────────
// hot: above 0.7 scale.  cold: below 0.35.  neutral: keep item's own TI.
private _material = if (_tiScale >= 0.7) then {
    "\z\aee\addons\optics\data\ti_cloth_hot.rvmat"
} else {
    ["", "\z\aee\addons\optics\data\ti_cloth_cold.rvmat"] select (_tiScale < 0.35)
};
if (_material == "") exitWith { 0 };

// ─── Apply to ALL units (no radius: one-shot swap is cheap) ──────────────
private _saved = missionNamespace getVariable [QGVAR(tiClothSaved), []];
private _applied = 0;
{
    if (isNull _x || !alive _x) then { continue; };
    private _obj = _x;

    // Per-class thermal selections, cached (A3TI fn_getThermalSelections).
    private _cacheKey = format [QGVAR(tiSelections_%1), typeOf _obj];
    private _selections = missionNamespace getVariable [_cacheKey, []];

    if (count _selections == 0) then {
        // Men: all texture selections are thermal-eligible (A3TI pattern).
        _selections = [];
        {
            _selections pushBack _forEachIndex;
        } forEach (getObjectTextures _obj);
        missionNamespace setVariable [_cacheKey, _selections];
    };

    // Skip if already swapped to this material (no redundant calls).
    private _already = false;
    {
        if ((getObjectMaterials _obj) select _x == _material) exitWith { _already = true; };
    } forEach _selections;
    if (_already) then { continue; };

    // ─── Material weighting (gear vs cloth) ────────────────────────────
    // Equipment materials respond to solar loading differently.  Metal,
    // glass and plastic (helmets, optics, armour plates, goggles) have
    // low thermal mass: they track ambient + sun quickly and read WARMER
    // than cloth.  Cloth/fabric holds body heat but also insulates.  We
    // read each selection's rvmat and only apply the cold swap to cloth-
    // dominant surfaces; metal/glass selections keep the engine's own
    // thermal (they should read slightly warm from solar, not forced
    // cold).  This gives the real per-item look: helmet warm, cloth cold,
    // the same differentiation the vanilla baked TI already shows for
    // chest rigs vs clothing: but physics-driven.
    private _mats = getObjectMaterials _obj;
    private _swapSelections = [];
    {
        private _sel = _x;
        private _m = toLower (_mats select _sel);
        // Cloth/leather/fabric dominant -> swap to our material.
        // Metal/glass/plastic -> keep engine thermal (solar-warm).
        if (_m find "cloth" >= 0 || _m find "fabric" >= 0 || _m find "leather" >= 0
            || _m find "wool" >= 0 || _m find "cotton" >= 0) then {
            _swapSelections pushBack _sel;
        } else {
            if (_m == "" || _m find "metal" < 0 && _m find "glass" < 0 && _m find "plastic" < 0) then {
                // Unknown material: swap (safe baseline: cloth assumption).
                _swapSelections pushBack _sel;
            };
        };
    } forEach _selections;

    if (_swapSelections isNotEqualTo []) then {
        private _oldMats = getObjectMaterials _obj;
        {
            _obj setObjectMaterial [_x, _material];
        } forEach _swapSelections;
        _saved pushBack [_obj, _oldMats, _swapSelections];
        _applied = _applied + 1;
    };
} forEach (allUnits);

missionNamespace setVariable [QGVAR(tiClothSaved), _saved];
_applied
