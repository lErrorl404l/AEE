// ---- camera ---------------------------------------------------------------
private _cam = "camera" camCreate [0, 0, 0];
_cam cameraEffect ["Internal", "BACK"];
_cam camSetFov 9;                                  // CAM001 (range) + CAM002 (no camCommit in this file)
_cam cameraEffect ["Wobble", "SIDEWAYS"];          // CAM003 twice (effect + position)
_cam cameraEffect ["terminate", "back"];           // fine: case-insensitive
true setCamUseTI 1;                                // fine: camera is created in this addon -> no NV003

// ---- thermal ----------------------------------------------------------------
setTIParameter ["OutputRangeStart", 0.3];          // TI008 (non-default) + TI003 (no Loaded handler anywhere)
player disableTIEquipment 1;                       // TI009
player disableTIEquipment (_set > 0);              // fine: expression
tank setVehicleTIPars [2, 0, 0];                   // TI010 (range)
tank setVehicleTIPars [1, 0];                      // TI010 (shape)

// ---- tone mapping: not present in Arma 3 per wiki ------------------------
setToneMapping "Filmic";                           // TM001
"Filmic" setToneMappingParams [0.2, 0.3, 0.2, 0.3, 0.01, 3.75, 6, 4];   // TM001

// ---- templates -----------------------------------------------------------
["BlackAndWhite", 0] call BIS_fnc_setPPeffectTemplate;     // built in
["DemoGrade", 1] call BIS_fnc_setPPeffectTemplate;         // defined in CfgPostProcessTemplates
["NoSuchTemplate", 1] call BIS_fnc_setPPeffectTemplate;    // TPL001
[] call BIS_fnc_ambientPostprocess;                        // TPL002 (once per file)

// ---- ppEffectForceInNVG needs a boolean -----------------------------------
private _g = ppEffectCreate ["FilmGrain", 2000];
_g ppEffectEnable true;
_g ppEffectAdjust [0.2, 2, 2, 0.5, 1, 0];
_g ppEffectCommit 0;
_g ppEffectForceInNVG 1;                           // NV004
ppEffectDestroy _g;
