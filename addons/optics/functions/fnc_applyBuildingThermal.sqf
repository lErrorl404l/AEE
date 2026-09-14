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
// The swap is one-shot state; only rescan when ambient changes materially.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _lastTemp = missionNamespace getVariable [QGVAR(tiBldgLastTemp), -999];
if (!(_lastTemp isEqualType 0)) then { _lastTemp = -999; };
if (abs (_airTemp - _lastTemp) < 2) exitWith { 0 };
missionNamespace setVariable [QGVAR(tiBldgLastTemp), _airTemp];

// ─── Apply to nearby buildings ────────────────────────────────────────────
// Cold TI material: the same ti_cloth_cold.rvmat (real TI texture, correct
// shader/flag set).  Buildings get swapped to it so they read cold; the
// physics second sun adds warmth through the red channel in daylight.
//
// MATERIAL WEIGHTING: the swap target depends on the building's actual
// material, read from getObjectMaterials (the rvmat path).  Thermal mass
// and solar response differ:
//   concrete/brick/stone/rock   -> high thermal mass, stays cold (strong)
//   wood/fabric/tarpaulin       -> mid mass, moderate
//   metal/glass/plastic         -> low mass, responds to sun (weakest cold)
// We classify the dominant rvmat and pick a matching TI material.  The
// cold/hot textures are per-material variants; for now the base cold
// texture is used for all, and the material factor throttles how many
// selections are swapped (a high-mass building swaps more surfaces = reads
// colder overall).  This is a first pass: per-material TI textures are
// the upgrade path (ponytail: one cold TI texture, material factor only).
private _material = "\z\aee\addons\optics\data\ti_cloth_cold.rvmat";
private _saved = missionNamespace getVariable [QGVAR(tiBldgSaved), []];
private _applied = 0;

private _buildings = _player nearObjects ["House", 300];
{
    if (isNull _x) then { continue; };
    private _obj = _x;

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

    private _swapCount = count _selections;
    // Heavy-mass building: swap everything (reads coldest).  Metal/glass
    // dominant: swap half the surfaces (responds to sun, reads less cold).
    if (_heavyCount > 0 && _metalCount == 0) then {
        _swapCount = count _selections;   // full cold
    } else {
        if (_metalCount > _heavyCount) then {
            _swapCount = ceil (count _selections / 2);
        };
    };

    private _oldMats = getObjectMaterials _obj;
    for "_i" from 0 to (_swapCount - 1) do {
        _obj setObjectMaterial [_selections select _i, _material];
    };
    _saved pushBack [_obj, _oldMats, _selections];
    _applied = _applied + 1;
} forEach _buildings;

missionNamespace setVariable [QGVAR(tiBldgSaved), _saved];
_applied
