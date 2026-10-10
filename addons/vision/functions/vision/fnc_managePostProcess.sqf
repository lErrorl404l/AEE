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

// The three handles are read BEFORE every guard.  A disabled module, a dead
// player or a camera change must run the cleanup, and the cleanup needs the
// handles; reading them below the guards leaves live effects on those paths.
private _hChroma = missionNamespace getVariable [QGVAR(ppHandle_ChromAberration), -1];
private _hBlur   = missionNamespace getVariable [QGVAR(ppHandle_DynamicBlur), -1];
private _hCC     = missionNamespace getVariable [QGVAR(ppHandle_ColorCorrections), -1];

// Every exit below leaves no live optics effect behind, and clears the active
// flags so a re-enabled module starts from a known state instead of trusting
// a flag an earlier pass set and never cleared.
private _cleanup = {
    params ["_hChroma", "_hBlur", "_hCC"];
    if (_hChroma >= 0) then {
        _hChroma ppEffectEnable false;
    };
    if (_hBlur >= 0) then {
        _hBlur ppEffectEnable false;
    };
    if (_hCC >= 0) then {
        _hCC ppEffectEnable false;
    };
    missionNamespace setVariable [QGVAR(chromaActive), false];
    missionNamespace setVariable [QGVAR(blurActive), false];
    missionNamespace setVariable [QGVAR(ccActive), false];
};

if (!(missionNamespace getVariable [QEGVAR(core,opticsEnabled), true])) exitWith {
    [_hChroma, _hBlur, _hCC] call _cleanup;
};

private _player = call CBA_fnc_currentUnit;
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith {
    [_hChroma, _hBlur, _hCC] call _cleanup;
};
if (cameraOn != _player && {cameraOn != _veh}) exitWith {
    [_hChroma, _hBlur, _hCC] call _cleanup;
};

// ─── Persistent handles (recreate if missing/stale) ──────────────────────
// THE REGISTRY IS THE AUTHORITATIVE RECORD and the legacy mirror is only a
// cache of it, so the registry decides and the cache is refreshed from it.
// The old gate read the cache and warned "handle lost" when it was -1, and a
// live log proved that a FALSE ALARM: the registry still held the live handle
// and the very next line reported the effect already owned at that same
// handle.  A weaker record than the real one must not raise a warning, or the
// warning teaches you to ignore it.  Every tick reconciles the cache against
// the registry rather than only when a cache read looks wrong, which removes
// the coupling that produced the false alarm.
//
// THE LIMIT STAYS: there is no engine query for "is this handle alive", so an
// effect the ENGINE killed while the registry still lists it cannot be
// detected here.  The engine did log "EPE manager release" in the same
// session.  That gap is stated rather than papered over with the cache proxy
// that misreported.
{
    _x params ["_name", "_priority", "_legacy"];
    private _owner = missionNamespace getVariable [format [QEGVAR(core,ppHandle_%1_%2), "optics", _name], -1];
    if (_owner < 0) then {
        private _logMsg = format ["optics|%1 has no registry handle, creating it", _name];
        AEE_LOG_WARN(_logMsg);
        private _handle = ["optics", _name, _name, _priority, _legacy] call EFUNC(lib,createPPEffect);
        if (_handle >= 0) then { missionNamespace setVariable [_legacy, _handle]; };
    } else {
        if ((missionNamespace getVariable [_legacy, -1]) != _owner) then {
            missionNamespace setVariable [_legacy, _owner];
        };
    };
} forEach [
    // The priorities must match fnc_ppEffectCreate.  They are AEE-unique
    // values, NOT the BIS-documented base priorities (200/400/1500): a base
    // value is shared convention and is already taken by the engine's own
    // CfgOpticsEffect table or another loaded config, so the engine logs
    // "PE with same priority ... already exist" (live RPT: DynamicBlur 400).
    // Each sits just below the engine's own same-type entry (250/450/1550),
    // so the relative order is unchanged and the cockpit HUD still composites
    // over the blur.  See fnc_ppEffectCreate.
    ["ChromAberration", 210, QGVAR(ppHandle_ChromAberration)],
    ["DynamicBlur",     410, QGVAR(ppHandle_DynamicBlur)],
    ["ColorCorrections", 1510, QGVAR(ppHandle_ColorCorrections)]
];
_hChroma = missionNamespace getVariable [QGVAR(ppHandle_ChromAberration), -1];
_hBlur   = missionNamespace getVariable [QGVAR(ppHandle_DynamicBlur), -1];
_hCC     = missionNamespace getVariable [QGVAR(ppHandle_ColorCorrections), -1];

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

// Diagnostics.  A leaked effect shows up here as a true active flag in
// normal vision, and the resolved values below show what is committed.
private _diagFlags = format ["PP mode=%1 chromaActive=%2 blurActive=%3 ccActive=%4", _visionMode, missionNamespace getVariable [QGVAR(chromaActive), false], missionNamespace getVariable [QGVAR(blurActive), false], missionNamespace getVariable [QGVAR(ccActive), false]];
AEE_LOG_DEBUG(_diagFlags);

if (_visionMode == 1 || _visionMode == 2) exitWith {
    // NVG tube model uses separate ppEffect handles (NVG_CC, NVG_Bloom, NVG_Vignette)
    // and separate state variables (nvgGrainActive). This block only fades the
    // regular optical-path effects. No conflict.
    if (missionNamespace getVariable [QGVAR(chromaActive), false]) then {
        if (_hChroma >= 0) then {
            _hChroma ppEffectAdjust [0, 0, false];
            _hChroma ppEffectCommit 1;
        };
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
            };
        }, [_gen], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(chromaActive), false];
    };
    if (missionNamespace getVariable [QGVAR(blurActive), false]) then {
        if (_hBlur >= 0) then {
            _hBlur ppEffectAdjust [0];
            _hBlur ppEffectCommit 1;
        };
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
            };
        }, [_gen], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(blurActive), false];
    };
    if (missionNamespace getVariable [QGVAR(ccActive), false]) then {
        if (_hCC >= 0) then {
            // Identity: the engine's own neutral post-process
            // (CfgPostProcessTemplates >> Default >> colorCorrections =
            // {1,1,0,{0,0,0,0},{1,1,1,1},{0,0,0,0}}): colorize alpha 1, zero weights.
            _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0], [-1,-1,0,0,0,0,0]];
            _hCC ppEffectCommit 1;
        };
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
            };
        }, [_gen], 1.5] call CBA_fnc_waitAndExecute;
        missionNamespace setVariable [QGVAR(ccActive), false];
    };
};

// ─── Stored intensities (set by the apply* contributor functions) ─────────
// Defensive: a contributor that stores a string or nil (bad variable state)
// must not propagate into ppEffectAdjust — "Type Number, expected Number"
// otherwise fires every tick.  Coerce to numeric with a finite floor.
private _seeingChroma  = missionNamespace getVariable [QEGVAR(optics,seeingChroma), 0];
private _shimmerChroma = missionNamespace getVariable [QEGVAR(optics,shimmerChroma), 0];
if !(_seeingChroma isEqualType 0) then { _seeingChroma = 0; };
if !(_shimmerChroma isEqualType 0) then { _shimmerChroma = 0; };
private _dewBlur     = missionNamespace getVariable [QEGVAR(optics,dewBlur), 0];
private _rainBlur    = missionNamespace getVariable [QEGVAR(optics,rainBlur), 0];
private _glareBlur   = missionNamespace getVariable [QEGVAR(optics,glareBlur), 0];
private _severeBlur  = missionNamespace getVariable [QEGVAR(optics,severeWeatherBlur), 0];
private _heatBlur    = missionNamespace getVariable [QEGVAR(optics,heatHazeBlur), 0];
if !(_dewBlur isEqualType 0) then { _dewBlur = 0; };
if !(_rainBlur isEqualType 0) then { _rainBlur = 0; };
if !(_glareBlur isEqualType 0) then { _glareBlur = 0; };
if !(_severeBlur isEqualType 0) then { _severeBlur = 0; };
if !(_heatBlur isEqualType 0) then { _heatBlur = 0; };
private _severeCC    = missionNamespace getVariable [QEGVAR(optics,severeWeatherCC), []];
private _snowCC      = missionNamespace getVariable [QEGVAR(optics,snowBlindnessCC), []];

// ─── Resolve per effect ────────────────────────────────────────────────────
private _chromaCap = missionNamespace getVariable [QEGVAR(optics,chromaCap), 0.06];
private _chroma = (_seeingChroma + _shimmerChroma) min _chromaCap;
// Heat-haze defocus (issue #100) is a further contributor to the SAME
// single-owner DynamicBlur; the arbiter max-combines it, so no second
// DynamicBlur handle is created.
private _blur   = ((_dewBlur max _rainBlur) max (_glareBlur max _severeBlur)) max _heatBlur;

// ColorCorrections: severe weather wins the single slot when active,
// otherwise snow blindness.  Both empty → neutral.
private _ccParams = if (count _severeCC > 0) then {
    _severeCC
} else {
    if (count _snowCC > 0) then { _snowCC } else { [] };
};

// Diagnostics.  These are the values about to be committed.  A non-zero
// chroma, a non-zero blur, or a colour offset in ccParams while the player
// is in normal vision means a leaked sensor value.
private _diagCommit = format ["PP commit mode=%1 chroma=%2 blur=%3 cc=%4 seeing=%5 shimmer=%6 dew=%7 rain=%8 glare=%9 severe=%10", _visionMode, _chroma, _blur, _ccParams, _seeingChroma, _shimmerChroma, _dewBlur, _rainBlur, _glareBlur, _severeBlur];
AEE_LOG_DEBUG(_diagCommit);

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
        // Identity: the engine's own neutral post-process
        // (CfgPostProcessTemplates >> Default >> colorCorrections =
        // {1,1,0,{0,0,0,0},{1,1,1,1},{0,0,0,0}}): colorize alpha 1, zero weights.
        _hCC ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0], [-1,-1,0,0,0,0,0]];
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
