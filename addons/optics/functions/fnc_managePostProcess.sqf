#include "..\script_component.hpp"

/*
Central post-process arbiter — single owner of the shared ppEffects.

Owns ChromAberration, DynamicBlur and ColorCorrections.  Each
contributing function stores its desired intensity in a mission
variable; this function resolves the per-effect value every tick and
applies it once.  Last-writer-wins flicker is impossible because no
other function touches these effects.

Resolution rules:
  ChromAberration   — additive: seeing + heat shimmer, capped 0.06
  DynamicBlur       — max of dew / rain / glare / severe weather
  ColorCorrections  — priority: severe weather > snow blindness
                      (single-slot effect, one visible owner)

Anti-flicker:
  Hysteresis — an effect engages above its on-threshold and only
  disengages below its off-threshold (off < on), so a value hovering
  at the boundary does not toggle every tick.
  Generation guard — a deferred disable captures the current
  generation; if the effect re-engages before the disable fires, the
  generation changes and the stale disable is skipped.

Gates on EGVAR(core,opticsEnabled).  Sets nothing except the effects.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

// NVG (1) and thermal (2) views: the sensor produces its own image.
// Chromatic aberration from atmospheric seeing and heat shimmer, blur
// from dew/rain on a lens, and colour-correction tints all assume a
// glass optic path.  Through a sensor they do not exist.  Fade out any
// effects already active, then skip the rest of the tick.
// Vision modes verified in-game: 0 = normal, 1 = NVG, 2 = thermal.
private _visionMode = currentVisionMode _player;
if (_visionMode == 1 || _visionMode == 2) exitWith {
    if (missionNamespace getVariable [QGVAR(chromaActive), false]) then {
        "ChromAberration" ppEffectAdjust [0, 0, 0];
        "ChromAberration" ppEffectCommit 1;
        [{
            "ChromAberration" ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(chromaActive), false];
    };
    if (missionNamespace getVariable [QGVAR(blurActive), false]) then {
        "DynamicBlur" ppEffectAdjust [0];
        "DynamicBlur" ppEffectCommit 1;
        [{
            "DynamicBlur" ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(blurActive), false];
    };
    if (missionNamespace getVariable [QGVAR(ccActive), false]) then {
        "ColorCorrections" ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0]];
        "ColorCorrections" ppEffectCommit 1;
        [{
            "ColorCorrections" ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(ccActive), false];
    };
};

// ─── Stored intensities (set by the apply* contributor functions) ─────────
private _seeingChroma = missionNamespace getVariable [QGVAR(seeingChroma), 0];
private _shimmerChroma = missionNamespace getVariable [QGVAR(shimmerChroma), 0];
private _dewBlur     = missionNamespace getVariable [QGVAR(dewBlur), 0];
private _rainBlur    = missionNamespace getVariable [QGVAR(rainBlur), 0];
private _glareBlur   = missionNamespace getVariable [QGVAR(glareBlur), 0];
private _severeBlur  = missionNamespace getVariable [QGVAR(severeWeatherBlur), 0];
private _severeCC    = missionNamespace getVariable [QGVAR(severeWeatherCC), []];
private _snowCC      = missionNamespace getVariable [QGVAR(snowBlindnessCC), []];

// ─── Resolve per effect ────────────────────────────────────────────────────
private _chroma = (_seeingChroma + _shimmerChroma) min 0.06;
private _blur   = (_dewBlur max _rainBlur) max (_glareBlur max _severeBlur);

// ColorCorrections: severe weather wins the single slot when active,
// otherwise snow blindness.  Both empty → neutral.
private _ccParams = if (count _severeCC > 0) then {
    _severeCC
} else {
    if (count _snowCC > 0) then { _snowCC } else { [] };
};

// ─── ChromAberration (hysteresis on > 0.01, off < 0.005) ───────────────────
private _chromaOn  = _chroma > 0.01;
private _chromaOff = _chroma < 0.005;
private _chromaActive = missionNamespace getVariable [QGVAR(chromaActive), false];

if (_chromaOn) then {
    if (!_chromaActive) then {
        "ChromAberration" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(chromaActive), true];
    };
    missionNamespace setVariable [QGVAR(chromaGen), (missionNamespace getVariable [QGVAR(chromaGen), 0]) + 1];
    // ChromAberration ppEffectAdjust takes [x, y, strength] — a 3-element
    // array (pixel offset and chromatic strength).  A 6-element array
    // (copied from the pre-arbiter code) throws "6 elements, 3 expected".
    "ChromAberration" ppEffectAdjust [0, 0, _chroma];
    "ChromAberration" ppEffectCommit 2;
} else {
    if (_chromaActive && _chromaOff) then {
        "ChromAberration" ppEffectAdjust [0, 0, 0];
        "ChromAberration" ppEffectCommit 1;
        private _gen = missionNamespace getVariable [QGVAR(chromaGen), 0];
        [{
            params ["_gen"];
            if (missionNamespace getVariable [QGVAR(chromaGen), 0] == _gen) then {
                "ChromAberration" ppEffectEnable false;
                missionNamespace setVariable [QGVAR(chromaActive), false];
            };
        }, [_gen], 1.5] call CBA_fnc_waitAndExecute;
    };
};

// ─── DynamicBlur (hysteresis on > 0.01, off < 0.005) ───────────────────────
private _blurOn  = _blur > 0.01;
private _blurOff = _blur < 0.005;
private _blurActive = missionNamespace getVariable [QGVAR(blurActive), false];

if (_blurOn) then {
    if (!_blurActive) then {
        "DynamicBlur" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(blurActive), true];
    };
    missionNamespace setVariable [QGVAR(blurGen), (missionNamespace getVariable [QGVAR(blurGen), 0]) + 1];
    "DynamicBlur" ppEffectAdjust [_blur];
    "DynamicBlur" ppEffectCommit 2;
} else {
    if (_blurActive && _blurOff) then {
        "DynamicBlur" ppEffectAdjust [0];
        "DynamicBlur" ppEffectCommit 1;
        private _gen = missionNamespace getVariable [QGVAR(blurGen), 0];
        [{
            params ["_gen"];
            if (missionNamespace getVariable [QGVAR(blurGen), 0] == _gen) then {
                "DynamicBlur" ppEffectEnable false;
                missionNamespace setVariable [QGVAR(blurActive), false];
            };
        }, [_gen], 1.5] call CBA_fnc_waitAndExecute;
    };
};

// ─── ColorCorrections (single owner, engaged only when a CC is present) ────
private _ccOn = count _ccParams > 0;
private _ccActive = missionNamespace getVariable [QGVAR(ccActive), false];

if (_ccOn) then {
    if (!_ccActive) then {
        "ColorCorrections" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(ccActive), true];
    };
    missionNamespace setVariable [QGVAR(ccGen), (missionNamespace getVariable [QGVAR(ccGen), 0]) + 1];
    "ColorCorrections" ppEffectAdjust _ccParams;
    "ColorCorrections" ppEffectCommit 2;
} else {
    if (_ccActive) then {
        // Fade to neutral over 5 s, then disable if still neutral
        "ColorCorrections" ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0]];
        "ColorCorrections" ppEffectCommit 5;
        private _gen = missionNamespace getVariable [QGVAR(ccGen), 0];
        [{
            params ["_gen"];
            if (missionNamespace getVariable [QGVAR(ccGen), 0] == _gen) then {
                "ColorCorrections" ppEffectEnable false;
                missionNamespace setVariable [QGVAR(ccActive), false];
            };
        }, [_gen], 5.5] call CBA_fnc_waitAndExecute;
    };
};
