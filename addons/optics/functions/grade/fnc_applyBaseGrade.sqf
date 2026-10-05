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
ColorCorrections to the contract identity before disabling, so no graded frame
is left live.  The identity is colorize alpha 0 (BIKI Post Process Effects,
capture 20240220225631): alpha 1 is black and white, which is what drained
normal vision to grey.
  [1, 1, 0, [0,0,0,0], [1,1,1,0], [0.2126,0.7152,0.0722,0], [-1,-1,0,0,0,0,0]]

Handles are read before every guard.  The source is the core registry owner
record aee_core_ppHandle_optics_BaseGrade / ..._BaseAcuity, which
fnc_createPPEffect writes on create and fnc_destroyPPEffect resets to -1.
The addon's own QGVAR(ppHandle_BaseGrade) mirror is not written by the
registry, so reading it pinned the handle at -1 and recreated a live effect
on every tick.  A genuinely missing handle is destroyed and recreated with
the night-vision pattern
(addons/nightvision/functions/fnc_applyNVGTubeModel.sqf:958-1027), so the
effects survive alt-tab, a resize and an advanced optic.

Engines values and the per-constant source register are in the kernel header
fnc_baseGradeParams.sqf and .omo/plans/aee-image-realism.md.

Debug hooks (set on missionNamespace; debug console only, no CBA setting):
  aee_optics_baseGradeForce      Bool: force the grade on.
  aee_optics_baseGradeContrast   Number: override the contrast setting.
  aee_optics_baseGradeSharpness  Number: override the acuity sharpness setting.
  aee_optics_baseGradeGrain      Number: override the acuity grain setting.
  aee_optics_visionForce         Bool: force the human-vision model on.
  aee_optics_visionForceLux      Number: override the adapted luminance, cd/m2.
  aee_optics_visionForceMesopic  Number: override the mesopic photopic fraction.
  aee_optics_visionForceIlluminant  Array: override the scene illuminant colour.
  aee_optics_visionForceBase     Array: override the base-grade anchor [b, c, o].
  aee_optics_logDebug            Bool: log one DEBUG line per tick.

Arguments: none.

Returns:
  Nothing.
*/

// Read the handles BEFORE every guard.  A disabled module, a dead player or a
// camera change must neutralise and disable the effects, and that path needs
// the handles; reading them below the guards leaves a live grade on those
// paths.
private _hCC = missionNamespace getVariable [QEGVAR(core,ppHandle_optics_BaseGrade), -1];
private _hAcuity = missionNamespace getVariable [QEGVAR(core,ppHandle_optics_BaseAcuity), -1];

// The vanilla base-grade anchor.  The developers' default post-process grade is
// the Default class of the base-game post-process template in functions_f.pbo.
// AEE reads the loaded config once per session and caches the scalar triple
// [brightness, contrast,
// offset]; it never ships or copies the Bohemia config.  The read sits above
// every post-process adjust so the anchor is known before an adjust can run.
// Fallback [1, 1, 0] source: a3\functions_f\config.cpp line 3553 of
// functions_f.pbo, build 2025-08-11.  The fallback is a number triple with a
// source, not shipped content.
if (isNil QGVAR(visionBaseAnchor)) then {
    private _raw = getArray (configFile >> "CfgPostProcessTemplates" >> "Default" >> "colorCorrections");
    private _anchor = [1, 1, 0];
    if ((_raw isEqualType []) && ((count _raw) >= 3)) then {
        private _b = _raw select 0;
        private _c = _raw select 1;
        private _o = _raw select 2;
        if ((_b isEqualType 0) && (_c isEqualType 0) && (_o isEqualType 0) && (_b >= 0) && (_b <= 4) && (_c >= 0) && (_c <= 4) && (_o >= -1) && (_o <= 1)) then {
            _anchor = [_b, _c, _o];
        };
    };
    missionNamespace setVariable [QGVAR(visionBaseAnchor), _anchor];
};

// Debug hook: a three-number aee_optics_visionForceBase overrides the anchor.
private _baseAnchor = missionNamespace getVariable [QGVAR(visionBaseAnchor), [1, 1, 0]];
private _forceBase = missionNamespace getVariable [QGVAR(visionForceBase), []];
if ((_forceBase isEqualType []) && ((count _forceBase) >= 3)) then {
    private _fb = _forceBase select 0;
    private _fc = _forceBase select 1;
    private _fo = _forceBase select 2;
    if ((_fb isEqualType 0) && (_fc isEqualType 0) && (_fo isEqualType 0)) then {
        _baseAnchor = [_fb, _fc, _fo];
    };
};

// Neutralise, then disable, then clear the active flag.  Every adjust, enable
// and destroy sits behind a >= 0 guard.
private _standDown = {
    params ["_hCC", "_hAcuity"];
    if (_hCC >= 0) then {
        // Identity: colorize alpha 0 keeps the original colour; alpha 1 is B&W.
        _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,0], [0.2126,0.7152,0.0722,0], [-1,-1,0,0,0,0,0]];
        _hCC ppEffectCommit 0;
        _hCC ppEffectEnable false;
    };
    if (_hAcuity >= 0) then {
        _hAcuity ppEffectEnable false;
    };
    missionNamespace setVariable [QGVAR(baseGradeActive), false];
    private _logMsg = format ["base grade stand-down cc=%1 acuity=%2", _hCC, _hAcuity];
    AEE_LOG_DEBUG(_logMsg);
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

// The physical human-vision model subsumes the aesthetic base grade in place.
// The master switch is read defensively: the setting registers in a later
// commit, and a bare GVAR read can throw between the commits.  When the model
// is on, the driver reads the eye model's published adapted luminance and
// mesopic photopic fraction; it never writes the aperture.
private _useModel = missionNamespace getVariable [QGVAR(visionModelEnabled), false];

// Debug hooks: the force switch, the luminance override and the mesopic
// override.  Each is a missionNamespace variable, not a CBA setting.
private _visionForce = missionNamespace getVariable [QGVAR(visionForce), false];
if (_visionForce isEqualType true) then { _useModel = _useModel || _visionForce; };
if (_visionForce isEqualType 0) then { _useModel = _useModel || (_visionForce > 0); };

private _adaptedLux = missionNamespace getVariable [QGVAR(eyeAdaptedLux), 1];
private _mesopicW = missionNamespace getVariable [QGVAR(eyeMesopic), 1];
private _params = [];
// Performance: the model runs in the existing 1.0 s client PFH started by
// fnc_initBaseGrade.  It adds one ambient engine read per tick and the pure
// kernels are arithmetic over a few numbers.  It does not touch the 5 ms
// aee_core_fnc_updateEnvironment gate, which is a server tick on another path.
if (_useModel isEqualTo true) then {
    private _forceLux = missionNamespace getVariable [QGVAR(visionForceLux), -1];
    if (_forceLux isEqualType 0) then {
        if (_forceLux >= 0) then { _adaptedLux = _forceLux; };
    };
    private _forceMesopic = missionNamespace getVariable [QGVAR(visionForceMesopic), -1];
    if (_forceMesopic isEqualType 0) then {
        if (_forceMesopic >= 0) then { _mesopicW = _forceMesopic; };
    };
    private _toneEnabled = missionNamespace getVariable [QGVAR(visionToneEnabled), true];
    private _whiteBalance = missionNamespace getVariable [QGVAR(visionWhiteBalance), false];
    private _toneStrength = missionNamespace getVariable [QGVAR(visionToneStrength), 0.25];
    private _contrastScale = missionNamespace getVariable [QGVAR(visionContrastScale), 1];
    private _adaptDegree = missionNamespace getVariable [QGVAR(visionAdaptationDegree), 0.9];
    private _desatMax = missionNamespace getVariable [QGVAR(visionMesopicDesaturation), 0];
    private _purkinje = missionNamespace getVariable [QGVAR(visionPurkinjeStrength), 0];
    // Bounded desaturation: the mesopic setting scales with the scotopic
    // fraction, then clamps to the 0 to 0.10 bound the anchor clamp enforces.
    private _desatAlpha = (((_desatMax * (1 - _mesopicW)) max 0) min 0.10);

    // The scene illuminant: the engine ambient colour, one engine read per
    // tick.  Element 0 is the ambient light colour (BIKI capture
    // 20250120023422).  Fall back to the display white D65.
    private _illuminant = [1, 1, 1];
    private _lighting = getLightingAt _player;
    if ((_lighting isEqualType []) && ((count _lighting) >= 1)) then {
        private _ambient = _lighting select 0;
        if (_ambient isEqualType []) then {
            if ((count _ambient) == 3) then {
                _illuminant = _ambient;
            };
        };
    };

    // Debug hook: override the scene illuminant colour.
    private _forceIlluminant = missionNamespace getVariable [QGVAR(visionForceIlluminant), []];
    if (_forceIlluminant isEqualType []) then {
        if ((count _forceIlluminant) == 3) then {
            _illuminant = _forceIlluminant;
        };
    };

    _params = [
        _adaptedLux,
        _mesopicW,
        _illuminant,
        _toneEnabled,
        _whiteBalance,
        _toneStrength,
        _contrastScale,
        _adaptDegree,
        _desatMax,
        _purkinje,
        _baseAnchor,
        _desatAlpha
    ] call FUNC(perceptionParams);
} else {
    _params = [
        GVAR(baseGradeContrast),
        GVAR(baseGradeBrightness),
        GVAR(baseGradeBlackPoint),
        GVAR(baseGradeSaturation),
        GVAR(baseGradeSharpness),
        GVAR(baseGradeGrain)
    ] call FUNC(baseGradeParams);
};
private _ccParams = _params select 0;
private _grainParams = _params select 1;

private _visionLog = format ["vision model active=%1 adaptedLux=%2 mesopic=%3 contrast=%4 base=%5", _useModel isEqualTo true, _adaptedLux, _mesopicW, (_ccParams select 1), _baseAnchor];
AEE_LOG_DEBUG(_visionLog);

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
missionNamespace setVariable [QGVAR(visionModelActive), _useModel isEqualTo true];
