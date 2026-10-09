/*
fnc_devReapplyVisual - re-run the client visual pipeline in place.

The operator edits a texture, a material or a grade value, presses the
DevReapplyVisual key and sees the change without a relaunch. Every step is
idempotent, so a second press is safe.

Pipeline:
  1. Teardown through the core registry. The "" key releases a whole scope,
     so a new key or priority can not leak an old handle.
  2. Re-create and re-apply through the owning modules. Every create routes
     through the core registry (aee_core_fnc_createPPEffect), so no raw
     ppEffectCreate appears here:
       eye grade       aee_optics_fnc_ppEffectCreate
       base grade      aee_optics_fnc_applyBaseGrade
       weather grain   aee_optics_fnc_applyWeatherGrain
       NVG grain       aee_nightvision_fnc_applyNightGrain
       thermal vision  aee_thermal_fnc_createThermalPPEffects
  3. Textures and materials: read the current values from the target and write
     them back for every selection, so an edited file is re-read.

Client only: a dedicated server renders nothing.

Arguments: none.
Return Value: BOOL - true when the pipeline ran.
*/

if (!hasInterface) exitWith { false };

private _unit = call CBA_fnc_currentUnit;

// 1. Release the affected post-process scopes through the registry.
["optics", ""] call aee_core_fnc_destroyPPEffect;
["nightvision", ""] call aee_core_fnc_destroyPPEffect;
["thermal", ""] call aee_core_fnc_destroyPPEffect;

// 2. Re-create and re-apply through the owning modules (registry-routed).
[] call aee_optics_fnc_ppEffectCreate;
[] call aee_optics_fnc_applyBaseGrade;
[] call aee_optics_fnc_applyWeatherGrain;
[] call aee_nightvision_fnc_applyNightGrain;
[] call aee_thermal_fnc_createThermalPPEffects;

// 3. Re-apply the current textures and materials on the target selections.
if (!(isNil "_unit")) then {
    private _textures = getObjectTextures _unit;
    {
        if (_x isEqualType "") then { _unit setObjectTexture [_forEachIndex, _x]; };
    } forEach _textures;
    private _materials = getObjectMaterials _unit;
    {
        if (_x isEqualType "") then { _unit setObjectMaterial [_forEachIndex, _x]; };
    } forEach _materials;
};

true
