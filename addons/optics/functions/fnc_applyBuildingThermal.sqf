#include "..\script_component.hpp"
/*
 * Per-building thermal material override.
 *
 * The vanilla building TI texture bakes red=128 (half sun-heating) into
 * every building, so they read grey at night.  The engine gives no
 * per-object thermal command for buildings (setVehicleTIPars is vehicles
 * only), but the MATERIAL is scriptable: swapping a building's material to
 * one whose TI stage references a cold texture makes it render cold, the
 * same mechanism the clothing override and A3TI use.
 *
 * This mirrors fnc_applyClothingThermal for buildings: same per-class
 * thermal-selection discovery, same one-shot swap, same EXIT restore.
 * Buildings within the sensor radius get the cold TI material; the
 * physics second sun still warms them through the red channel in daylight.
 *
 * Multiplayer: setObjectMaterial is LOCAL, correct for per-client thermal
 * rendering (identical physics on every client).
 */
params ["_mode"];

if (!hasInterface) exitWith { 0 };

// ─── EXIT: restore every saved material ───────────────────────────────────
if (_mode == "EXIT") then {
    private _saved = missionNamespace getVariable [QGVAR(tiBldgSaved), []];
    {
        _x params ["_o", "_oldMats", "_thermalSelections"];
        if (!isNull _o) then {
            {
                _o setObjectMaterial [_x, _oldMats select _x];
            } forEach _thermalSelections;
        };
    } forEach _saved;
    missionNamespace setVariable [QGVAR(tiBldgSaved), []];
    0
};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── Throttle ─────────────────────────────────────────────────────────────
// The swap is one-shot state; only rescan the expensive BUILDING list when
// ambient changes materially.  COLD-START: on the first ENTER
// (tiBldgLastTemp = -999) the swap ALWAYS applies — everything starts at
// the cold baseline, never at baked engine defaults.  This is the "start
// at nothing, warm from physics" design: a midnight load shows all
// buildings cold, and the physics second sun warms them in daylight.
//
// VEHICLES are NOT throttled by ambient: they are few, and a vehicle that
// spawns AFTER the boot pass (editor-placed, player-created, mission
// scripted) must get the cold swap immediately — gating it on a 2 C
// ambient change leaves it at baked white forever.  The building scan is
// expensive (near-player radius); vehicles are a short list, so check them
// every tick.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _lastTemp = missionNamespace getVariable [QGVAR(tiBldgLastTemp), -999];
if (!(_lastTemp isEqualType 0)) then { _lastTemp = -999; };
private _ambientChanged = abs (_airTemp - _lastTemp) >= 2;
if (_ambientChanged) then {
    missionNamespace setVariable [QGVAR(tiBldgLastTemp), _airTemp];
};

// Build the object list: vehicles ALWAYS (new spawns need the swap now),
// buildings only when ambient changed (expensive near-player scan).
private _objects = [];
if (_ambientChanged) then {
    if (_mode == "ENTER") then {
        _objects = allMissionObjects "";
    } else {
        private _viewDist = (getObjectViewDistance select 0) max 300;
        _objects = (_player nearObjects ["House", _viewDist])
            + (_player nearObjects ["Building", _viewDist]);
    };
};
// Vehicles are always in the list regardless of the throttle — a newly
// spawned vehicle must not sit at baked white until the ambient moves.
_objects = _objects + (vehicles - [player]);

// ─── Apply to nearby buildings AND vehicles ───────────────────────────────
// Cold TI material: the same ti_cloth_cold.rvmat (real TI texture, correct
// shader/flag set).  Buildings get swapped to it so they read cold; the
// physics second sun adds warmth through the red channel in daylight.
//
// Vehicles too: setVehicleTIPars only drives the engine/wheels/weapon
// PARTS.  The vehicle BODY thermal comes from its baked TI texture
// (red=128 in the shared default), which reads white through the AGC
// window even when parked cold.  Swapping the body material to cold TI
// makes a parked vehicle read cold like buildings — the A3TI pattern
// (they swap vehicles + allUnits; the parked-MRAP-white report is the
// body's baked TI).
//
// MATERIAL WEIGHTING: the swap target depends on the actual material,
// read from getObjectMaterials (the rvmat path).  Thermal mass and solar
// response differ:
//   concrete/brick/stone/rock   -> high thermal mass, stays cold (strong)
//   wood/fabric/tarpaulin       -> mid mass, moderate
//   metal/glass/plastic         -> low mass, responds to sun (weakest cold)
// We classify the dominant rvmat and pick a matching TI material.  The
// cold/hot textures are per-material variants; for now the base cold
// texture is used for all, and the material factor throttles how many
// selections are swapped (a high-mass building swaps more surfaces = reads
// colder overall).  This is a first pass — per-material TI textures are
// the upgrade path (ponytail: one cold TI texture, material factor only).
private _material = "\z\aee\addons\optics\data\ti_cloth_cold.rvmat";
private _materialHot = "\z\aee\addons\optics\data\ti_cloth_hot.rvmat";
private _saved = missionNamespace getVariable [QGVAR(tiBldgSaved), []];
private _applied = 0;

// A3TI pattern: vehicles + units.  Buildings come from nearObjects.
// nearObjects matches the class AND its subclasses: "House" covers
// HouseBase-derived buildings; "Building" covers the rest (some mods
// use Building as the base).  Both are queried so no building type is
// missed — the 0-swapped report was likely the class filter missing
// the actual building parent class.
//
{
    if (isNull _x) then { continue; };
    private _obj = _x;
    private _isVehicle = _obj isKindOf "AllVehicles";

    // Per-class thermal selections, cached.  Men use all texture
    // selections; buildings use the same discovery (A3TI pattern).
    private _cacheKey = format [QGVAR(tiBldgSelections_%1), typeOf _obj];
    private _selections = missionNamespace getVariable [_cacheKey, []];

    if (count _selections == 0) then {
        _selections = [];
        {
            _selections pushBack _forEachIndex;
        } forEach (getObjectTextures _obj);
        missionNamespace setVariable [_cacheKey, _selections];
    };

    // Skip if no texture selections (untexturable) or already swapped.
    if (count _selections == 0) then { continue; };
    private _already = false;
    {
        if ((getObjectMaterials _obj) select _x == _material) exitWith { _already = true; };
    } forEach _selections;
    if (_already) then { continue; };

    // ─── Per-selection thermal gradient (VEHICLES) ─────────────────────
    // A real vehicle has a temperature GRADIENT: the engine bay/exhaust
    // runs hot, the body panels stay cool, the wheels warm from friction,
    // the glass reads differently.  We classify each selection by its
    // model selection name and assign the matching TI material:
    //   engine/exhaust/radiator/motor/turret -> HOT (drives with engine)
    //   wheel/tyre/track                      -> HOT (friction, dynamic)
    //   glass/window                          -> keep engine thermal
    //   body/other                            -> COLD (parked reads cold)
    // The engine slot of setVehicleTIPars already drives the engine-area
    // brightness on top; this material gradient makes the AREA visibly
    // hotter than the body — the parked-MRAP-white was a uniform body.
    //
    // Selection names come from the model config (hiddenSelections order
    // matches getObjectTextures index).
    private _selNames = [];
    if (_isVehicle) then {
        _selNames = getArray (configOf _obj >> "hiddenSelections");
        if (_selNames isEqualTo []) then {
            // Fallback: selectionNames from the model.
            _selNames = selectionNames _obj;
        };
    };
    private _swapMats = [];  // [selectionIndex, material]
    {
        private _sel = _x;
        private _mat = _material;   // default cold
        if (_isVehicle && _sel < count _selNames) then {
            private _sn = toLower (_selNames select _sel);
            if (_sn find "engine" >= 0 || _sn find "exhaust" >= 0
                || _sn find "radiator" >= 0 || _sn find "motor" >= 0
                || _sn find "turret" >= 0 || _sn find "intake" >= 0) then {
                _mat = _materialHot;             // engine area: hot
            };
            if (_sn find "wheel" >= 0 || _sn find "tyre" >= 0
                || _sn find "track" >= 0) then {
                _mat = _materialHot;             // wheels: friction heat
            };
            if (_sn find "glass" >= 0 || _sn find "window" >= 0
                || _sn find "light" >= 0) then {
                _mat = "";                        // keep engine thermal
            };
        };
        if (_mat != "") then { _swapMats pushBack [_sel, _mat]; };
    } forEach _selections;

    // ─── Material/colour weighting ─────────────────────────────────────
    // Read the building's dominant material from its rvmat paths and
    // classify thermal mass.  Concrete/brick: heavy, stays cold.  Metal/
    // glass: light, responds to sun.  The factor scales how many
    // selections we swap: heavier mass = swap all surfaces = reads cold.
    private _mats = getObjectMaterials _obj;
    private _metalCount = 0;
    private _heavyCount = 0;
    {
        private _m = toLower (_x select [count _x - 40, 40]);  // tail of path
        if (_m find "metal" >= 0 || _m find "glass" >= 0 || _m find "plastic" >= 0
            || _m find "concrete" >= 0 || _m find "steel" >= 0) then {
            _metalCount = _metalCount + 1;
        };
        if (_m find "concrete" >= 0 || _m find "brick" >= 0 || _m find "stone" >= 0
            || _m find "rock" >= 0 || _m find "block" >= 0) then {
            _heavyCount = _heavyCount + 1;
        };
    } forEach _mats;

    // ─── Apply ─────────────────────────────────────────────────────────
    // Vehicles: use the per-selection gradient (engine area hot, body
    // cold, glass unchanged).  Buildings: mass-weighted count of the
    // cold material (concrete full, metal half).
    private _oldMats = getObjectMaterials _obj;
    if (_isVehicle && _swapMats isNotEqualTo []) then {
        {
            _x params ["_selIdx", "_selMat"];
            _obj setObjectMaterial [_selIdx, _selMat];
        } forEach _swapMats;
        _saved pushBack [_obj, _oldMats, _selections];
        _applied = _applied + 1;
    } else {
        private _swapCount = count _selections;
        // Heavy-mass building: swap everything (reads coldest).  Metal/
        // glass dominant: swap half (responds to sun, reads less cold).
        if (_heavyCount > 0 && _metalCount == 0) then {
            _swapCount = count _selections;   // full cold
        } else {
            if (_metalCount > _heavyCount) then {
                _swapCount = ceil (count _selections / 2);
            };
        };
        for "_i" from 0 to (_swapCount - 1) do {
            _obj setObjectMaterial [_selections select _i, _material];
        };
        _saved pushBack [_obj, _oldMats, _selections];
        _applied = _applied + 1;
    };
} forEach _objects;

// Diagnostic: confirms the cold baseline applies in-game (the Eden-vs-game
// question).  If _applied stays 0 in-game but buildings show warm, the
// engine's alive-heat model is overriding the swap.  The object count
// separates 'no buildings found' from 'buildings found but skipped'.
if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
    diag_log text format ["[AEE] Building thermal: %1 found, %2 swapped cold (T=%3)",
        count _objects, _applied, round _airTemp];
};

missionNamespace setVariable [QGVAR(tiBldgSaved), _saved];
_applied
