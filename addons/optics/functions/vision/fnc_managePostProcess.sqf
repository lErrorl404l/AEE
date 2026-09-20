#include "..\..\script_component.hpp"

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
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith {};
if (cameraOn != _player && {cameraOn != _veh}) exitWith {};

// ─── Persistent handles (recreate if missing/stale) ──────────────────────
// The engine kills ppEffects on alt-tab, resize, AT sights and at mission
// load boundaries.  A stored positive handle then refers to a dead effect,
// and every ppEffectAdjust on it logs "Invalid post effect handle".
// There is no engine query for "is this handle alive", so the robust
// pattern is: if the stored value is -1 (or the effect was destroyed in a
// sensor exit block), recreate here before use.  This mirrors the
// create-once-recreate-when-missing pattern of the NVG/thermal models.
private _hChroma = missionNamespace getVariable [QGVAR(ppHandle_ChromAberration), -1];
private _hBlur   = missionNamespace getVariable [QGVAR(ppHandle_DynamicBlur), -1];
private _hCC     = missionNamespace getVariable [QGVAR(ppHandle_ColorCorrections), -1];

if (_hChroma < 0 || _hBlur < 0 || _hCC < 0) then {
    private _effects = [
        ["ChromAberration", 3000, QGVAR(ppHandle_ChromAberration)],
        ["DynamicBlur",     4000, QGVAR(ppHandle_DynamicBlur)],
        ["ColorCorrections", 5000, QGVAR(ppHandle_ColorCorrections)]
    ];
    {
        _x params ["_name", "_priority", "_store"];
        private _existing = missionNamespace getVariable [_store, -1];
        if (_existing < 0) then {
            private _handle = ppEffectCreate [_name, _priority];
            private _guard = 0;
            while {_handle < 0 && _guard < 100} do {
                _priority = _priority + 1;
                _handle = ppEffectCreate [_name, _priority];
                _guard = _guard + 1;
            };
            missionNamespace setVariable [_store, _handle];
            private _logMsg = format ["recreated %1 handle=%2 (was missing/stale)", _name, _handle];
            AEE_LOG_WARN(_logMsg);
        };
    } forEach _effects;
    _hChroma = missionNamespace getVariable [QGVAR(ppHandle_ChromAberration), -1];
    _hBlur   = missionNamespace getVariable [QGVAR(ppHandle_DynamicBlur), -1];
    _hCC     = missionNamespace getVariable [QGVAR(ppHandle_ColorCorrections), -1];
};

// ─── NVG tube model ──────────────────────────────────────────────────────
// Sensor modes (NVG/thermal) are owned by the fast sensor PFH in
// XEH_postInit (0.1 s tick, started by the visionMode event).  They are
// NOT called here: the 5 s environment tick is too slow for AGC lag and
// gating.  This function only manages the normal-vision optical path.
// The vision-mode exit below still fades normal-vision effects when the
// player enters a sensor mode.

// NVG (1) and thermal (2) views: the sensor produces its own image.
// Chromatic aberration from atmospheric seeing and heat shimmer, blur
// from dew/rain on a lens, and colour-correction tints all assume a
// glass optic path.  Through a sensor they do not exist.  Fade out any
// effects already active, then skip the rest of the tick.
// Vision modes verified in-game: 0 = normal, 1 = NVG, 2 = thermal.
private _visionMode = currentVisionMode _player;
if (_visionMode == 1 || _visionMode == 2) exitWith {
    // NVG tube model uses separate ppEffect handles (NVG_CC, NVG_Bloom, NVG_Vignette)
    // and separate state variables (nvgGrainActive). This block only fades the
    // regular optical-path effects. No conflict.
    if (missionNamespace getVariable [QGVAR(chromaActive), false]) then {
        if (_hChroma >= 0) then {
            _hChroma ppEffectAdjust [0, 0, false];
            _hChroma ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_ChromAberration), -1]) ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(chromaActive), false];
    };
    if (missionNamespace getVariable [QGVAR(blurActive), false]) then {
        if (_hBlur >= 0) then {
            _hBlur ppEffectAdjust [0];
            _hBlur ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_DynamicBlur), -1]) ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(blurActive), false];
    };
    if (missionNamespace getVariable [QGVAR(ccActive), false]) then {
        if (_hCC >= 0) then {
            _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0]];
            _hCC ppEffectCommit 1;
        };
        [{
            (missionNamespace getVariable [QGVAR(ppHandle_ColorCorrections), -1]) ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(ccActive), false];
    };
};

// ─── Stored intensities (set by the apply* contributor functions) ─────────
// Defensive: a contributor that stores a string or nil (bad variable state)
// must not propagate into ppEffectAdjust — "Type Number, expected Number"
// otherwise fires every tick.  Coerce to numeric with a finite floor.
private _seeingChroma  = missionNamespace getVariable [QGVAR(seeingChroma), 0];
private _shimmerChroma = missionNamespace getVariable [QGVAR(shimmerChroma), 0];
if !(_seeingChroma isEqualType 0) then { _seeingChroma = 0; };
if !(_shimmerChroma isEqualType 0) then { _shimmerChroma = 0; };
private _dewBlur     = missionNamespace getVariable [QGVAR(dewBlur), 0];
private _rainBlur    = missionNamespace getVariable [QGVAR(rainBlur), 0];
private _glareBlur   = missionNamespace getVariable [QGVAR(glareBlur), 0];
private _severeBlur  = missionNamespace getVariable [QGVAR(severeWeatherBlur), 0];
if !(_dewBlur isEqualType 0) then { _dewBlur = 0; };
if !(_rainBlur isEqualType 0) then { _rainBlur = 0; };
if !(_glareBlur isEqualType 0) then { _glareBlur = 0; };
if !(_severeBlur isEqualType 0) then { _severeBlur = 0; };
private _severeCC    = missionNamespace getVariable [QGVAR(severeWeatherCC), []];
private _snowCC      = missionNamespace getVariable [QGVAR(snowBlindnessCC), []];

// ─── Resolve per effect ────────────────────────────────────────────────────
private _chromaCap = missionNamespace getVariable [QGVAR(chromaCap), 0.06];
private _chroma = (_seeingChroma + _shimmerChroma) min _chromaCap;
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
    if (!_chromaActive && _hChroma >= 0) then {
        _hChroma ppEffectEnable true;
        missionNamespace setVariable [QGVAR(chromaActive), true];
    };
    missionNamespace setVariable [QGVAR(chromaGen), (missionNamespace getVariable [QGVAR(chromaGen), 0]) + 1];
    // ChromAberration ppEffectAdjust takes [x, y, strength] — a 3-element
    // array (pixel offset and chromatic strength).  A 6-element array
    // (copied from the pre-arbiter code) throws "6 elements, 3 expected".
    if (_hChroma >= 0) then {
        _hChroma ppEffectAdjust [_chroma, _chroma, false];
        _hChroma ppEffectCommit 2;
    };
} else {
    if (_chromaActive && _chromaOff) then {
        _hChroma ppEffectAdjust [0, 0, false];
        _hChroma ppEffectCommit 1;
        private _gen = missionNamespace getVariable [QGVAR(chromaGen), 0];
        [{
            params ["_gen"];
            if (missionNamespace getVariable [QGVAR(chromaGen), 0] == _gen) then {
                private _h = missionNamespace getVariable [QGVAR(ppHandle_ChromAberration), -1];
                if (_h >= 0) then {
                    _h ppEffectEnable false;
                } else {
                    AEE_LOG_WARN("chroma fade: handle already -1, skip disable");
                };
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
    if (!_blurActive && _hBlur >= 0) then {
        _hBlur ppEffectEnable true;
        missionNamespace setVariable [QGVAR(blurActive), true];
    };
    missionNamespace setVariable [QGVAR(blurGen), (missionNamespace getVariable [QGVAR(blurGen), 0]) + 1];
    if (_hBlur >= 0) then {
        _hBlur ppEffectAdjust [_blur];
        _hBlur ppEffectCommit 2;
    };
} else {
    if (_blurActive && _blurOff) then {
        _hBlur ppEffectAdjust [0];
        _hBlur ppEffectCommit 1;
        private _gen = missionNamespace getVariable [QGVAR(blurGen), 0];
        [{
            params ["_gen"];
            if (missionNamespace getVariable [QGVAR(blurGen), 0] == _gen) then {
                private _h = missionNamespace getVariable [QGVAR(ppHandle_DynamicBlur), -1];
                if (_h >= 0) then {
                    _h ppEffectEnable false;
                } else {
                    AEE_LOG_WARN("blur fade: handle already -1, skip disable");
                };
                missionNamespace setVariable [QGVAR(blurActive), false];
            };
        }, [_gen], 1.5] call CBA_fnc_waitAndExecute;
    };
};

// ─── ColorCorrections (single owner, engaged only when a CC is present) ────
private _ccOn = count _ccParams > 0;
private _ccActive = missionNamespace getVariable [QGVAR(ccActive), false];

if (_ccOn) then {
    if (!_ccActive && _hCC >= 0) then {
        _hCC ppEffectEnable true;
        missionNamespace setVariable [QGVAR(ccActive), true];
    };
    missionNamespace setVariable [QGVAR(ccGen), (missionNamespace getVariable [QGVAR(ccGen), 0]) + 1];
    if (_hCC >= 0) then {
        _hCC ppEffectAdjust _ccParams;
        _hCC ppEffectCommit 2;
    };
} else {
    if (_ccActive) then {
        // Fade to neutral over 5 s, then disable if still neutral
        _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0]];
        _hCC ppEffectCommit 5;
        private _gen = missionNamespace getVariable [QGVAR(ccGen), 0];
        [{
            params ["_gen"];
            if (missionNamespace getVariable [QGVAR(ccGen), 0] == _gen) then {
                private _h = missionNamespace getVariable [QGVAR(ppHandle_ColorCorrections), -1];
                if (_h >= 0) then {
                    _h ppEffectEnable false;
                } else {
                    AEE_LOG_WARN("CC fade: handle already -1, skip disable");
                };
                missionNamespace setVariable [QGVAR(ccActive), false];
            };
        }, [_gen], 5.5] call CBA_fnc_waitAndExecute;
    };
};
