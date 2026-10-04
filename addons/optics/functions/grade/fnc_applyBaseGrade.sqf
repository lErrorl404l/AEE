#include "..\..\script_component.hpp"

/*
Normal-vision base grade and acuity driver (image realism).

Owns two effects through the core registry under the "optics" scope, so it
never touches fnc_managePostProcess's single-slot severe-weather
ColorCorrections:

  "BaseGrade"  ColorCorrections, priority 1505.  Tone separation, black point
               and colour weights from the Rec.709 luma the ASC CDL uses.
               The engine desaturates only; it cannot oversaturate, so the
               saturation weight stays in [0, 0.5].
  "BaseAcuity" FilmGrain, priority 2505.  The engine has NO "Sharpen"
               ppEffect: the creatable set is RadialBlur, ChromAberration,
               WetDistortion, ColorCorrections, DynamicBlur, FilmGrain,
               ColorInversion, SSAO and Resolution (BIKI ppEffectCreate,
               capture 2024-10-06).  Scene sharpening is the built-in VIDEO
               OPTION "Sharpen Filter", which a mod cannot set.  This is the
               scriptable compromise at high sharpness and low intensity; the
               operator also raises the video option.  It is display
               aesthetic, not added human acuity (Campbell and Robson 1968).

Gate: normal vision only.  NVG (1) and thermal (2) produce their own image and
own their own handles, so this stands down there.  Stand-down also covers
death, respawn, a camera change and the module disable, and it neutralises the
ColorCorrections to [1,1,0,[0,0,0,0],[1,1,1,1],[0,0,0,0]] before disabling,
so no graded frame is left live.

Handles are read before every guard.  A missing handle is destroyed and
recreated with the night-vision pattern
(addons/nightvision/functions/fnc_applyNVGTubeModel.sqf:958-1027), so the
effects survive alt-tab, a resize and an advanced optic.

Engines values and the per-constant source register are in the kernel header
fnc_baseGradeParams.sqf and .omo/plans/aee-image-realism.md.

Arguments: none.

Returns:
  Nothing.
*/

// Read the handles BEFORE every guard.  A disabled module, a dead player or a
// camera change must neutralise and disable the effects, and that path needs
// the handles; reading them below the guards leaves a live grade on those
// paths.
private _hCC = missionNamespace getVariable [QGVAR(ppHandle_BaseGrade), -1];
private _hAcuity = missionNamespace getVariable [QGVAR(ppHandle_BaseAcuity), -1];

// Neutralise, then disable, then clear the active flag.  Every adjust, enable
// and destroy sits behind a >= 0 guard.
private _standDown = {
    params ["_hCC", "_hAcuity"];
    if (_hCC >= 0) then {
        _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0]];
        _hCC ppEffectCommit 0;
        _hCC ppEffectEnable false;
    };
    if (_hAcuity >= 0) then {
        _hAcuity ppEffectEnable false;
    };
    missionNamespace setVariable [QGVAR(baseGradeActive), false];
};

if (!hasInterface) exitWith {
    [_hCC, _hAcuity] call _standDown;
};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {
    [_hCC, _hAcuity] call _standDown;
};

private _veh = vehicle _player;
if ((cameraOn != _player) && (cameraOn != _veh)) exitWith {
    [_hCC, _hAcuity] call _standDown;
};

// A vision sensor owns the image.  The gate must come before the first adjust.
if (currentVisionMode _player != 0) exitWith {
    [_hCC, _hAcuity] call _standDown;
};

private _force = missionNamespace getVariable [QGVAR(baseGradeForce), false];
private _forced = false;
if (_force isEqualType true) then { _forced = _force; };
if (_force isEqualType 0) then { _forced = _force > 0; };

private _enabled = GVAR(baseGradeEnabled) || _forced;
private _acuityOn = GVAR(baseGradeAcuityEnabled) || _forced;
if (!_enabled) exitWith {
    [_hCC, _hAcuity] call _standDown;
};

// A missing handle is recreated with the night-vision pattern: destroy any
// live registry entry first (a stale handle the engine killed on alt-tab must
// not be handed back), then create a fresh one.
if (_hCC < 0) then {
    ["optics", "BaseGrade"] call EFUNC(core,destroyPPEffect);
    _hCC = ["optics", "BaseGrade", "ColorCorrections", 1505, QGVAR(ppHandle_BaseGrade)] call EFUNC(core,createPPEffect);
};
if (_hAcuity < 0) then {
    ["optics", "BaseAcuity"] call EFUNC(core,destroyPPEffect);
    _hAcuity = ["optics", "BaseAcuity", "FilmGrain", 2505, QGVAR(ppHandle_BaseAcuity)] call EFUNC(core,createPPEffect);
};

private _params = [
    GVAR(baseGradeContrast),
    GVAR(baseGradeBrightness),
    GVAR(baseGradeBlackPoint),
    GVAR(baseGradeSaturation),
    GVAR(baseGradeSharpness),
    GVAR(baseGradeGrain)
] call FUNC(baseGradeParams);
private _ccParams = _params select 0;
private _grainParams = _params select 1;

if (_hCC >= 0) then {
    _hCC ppEffectAdjust _ccParams;
    _hCC ppEffectCommit 0;
    _hCC ppEffectEnable true;
};
if (_hAcuity >= 0) then {
    if (_acuityOn) then {
        _hAcuity ppEffectAdjust _grainParams;
        _hAcuity ppEffectCommit 0;
        _hAcuity ppEffectEnable true;
    } else {
        _hAcuity ppEffectEnable false;
    };
};

missionNamespace setVariable [QGVAR(baseGradeActive), true];
missionNamespace setVariable [QGVAR(baseGradeCC), _hCC];
missionNamespace setVariable [QGVAR(baseGradeGrain), _hAcuity];
