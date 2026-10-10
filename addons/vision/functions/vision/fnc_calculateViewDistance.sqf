#include "..\..\script_component.hpp"
/*
Drive the engine's view distance from AEE's physics (issue #138).
The mod computes the full visibility state (fog, haze, rain attenuation,
NELM, thermal contrast) but nothing drives viewDistance — a soldier in
dense fog sees to the engine's default range, not the physics range.
This closes the loop: the engine renders what the eye can actually see,
and it is performance-positive (mostly LOWERS view distance in weather).

The driver (vision science):
  viewDistance = min(horizon, Koschmieder V, acuityLimit, 12000)

  sigma_total = sigma_fog + sigma_haze + sigma_rain     (per km)
    sigma_fog  = fogDensity * 10
    sigma_haze = haze * 1.0
    sigma_rain = 0.21 * rainRate^0.74                    (Atlas 1954)
  Koschmieder: V = 3.912 / sigma_total                   (km)
  Horizon: at 1.7 m eye height ~4.7 km; use the player's actual
    eye height: sqrt(2 * R_earth * eyeHeightASL)
  Acuity: the Johnson detection criterion caps useful range at
    ~6 km for a standing man (1.8 m at 1 arcmin); below that the
    eye cannot resolve the target regardless of clarity.
  Night: at NELM < 6 the eye's sensitivity limits range further:
    100 + (NELM - 2) * 300 m, applied when the sun is down.

Rate limiting: 500 m deadband + 4 s ramp, 1 Hz.  The engine fog already
fades objects at the fog range; matching view distance to it makes them
consistent and avoids streaming churn.

The scene-aware shadow distance (aee-workshop-copy item 6) is re-derived
from Adaptive Shadows (Workshop 3792830104).  The mod publishes no licence,
so this is a re-implementation, not copied code.  No mod content is copied.
The classifier is heuristic and its constants are UNSOURCED.  The shadow
target is clamped to the object target and to the engine shadow maximum; the
shadow path never calls setViewDistance and keeps its own ramp state.

Input:  none (reads the shared state and the AEE Optics > Shadows settings)
Output: none (applies setViewDistance + setObjectViewDistance on the
        local player - object distance follows terrain at 1/2, the BI
        guidance for the "CPU killer" lever, issue #139; the shadow element
        is the scene-aware target).  The shadow state is published above the
        interface gate so a headless server can observe it.

Caveat: script-driven per client, so this runs on each machine's own
view distance.  Hosts (dedicated server) have no camera; the function
guards on isMultiplayer + hasInterface for the engine calls only.
*/

params [];

// ─── Read the physics inputs ─────────────────────────────────────────────
private _fog   = missionNamespace getVariable [QEGVAR(core,currentFogDensity),      0];
private _haze  = missionNamespace getVariable [QEGVAR(core,currentHaze),             0];
private _nelm  = missionNamespace getVariable [QEGVAR(lighting,limitingMagnitude),     6.5];
private _sunDown = (parseNumber (sunOrMoon < 0));

// Rain rate from the engine weather (rain * 25 = mm/h, per the optics
// precipitation model).  Type guards against nil/string inputs.
if !(_fog  isEqualType 0) then { _fog  = 0; };
if !(_haze isEqualType 0) then { _haze = 0; };
if !(_nelm isEqualType 0) then { _nelm = 6.5; };
private _rainMMH = (rain * 25) max 0;

// ─── Extinction coefficients (per km) ────────────────────────────────────
// Atlas 1954 rain extinction is added to fog/haze sigma (spec formula):
//   sigma_fog = fogDensity * 10
//   sigma_haze = haze * 1.0
//   sigma_rain = 0.21 * R^0.74, R in mm/h
private _sigmaFog  = _fog * 10;
private _sigmaHaze = _haze * 1.0;
private _sigmaRain = if (_rainMMH > 0) then { 0.21 * (_rainMMH ^ 0.74) } else { 0 };
private _sigmaTotal = _sigmaFog + _sigmaHaze + _sigmaRain;

// ─── Koschmieder visibility ──────────────────────────────────────────────
private _visKm = if (_sigmaTotal > 0.001) then { 3.912 / _sigmaTotal } else { 300 };
private _visM = _visKm * 1000;

// ─── Horizon from the player's actual eye height ─────────────────────────
private _eye = (eyePos player) select 2;
private _eyeRel = (_eye - (getTerrainHeightASL (getPos player))) max 1.0;
private _horizonM = 1000 * sqrt (2 * 6371 * (_eyeRel / 1000));   // km -> m

// ─── Acuity: Johnson DRI is a TARGET-resolution criterion, not a scene
// view-distance cap.  A standing man is detectable to ~6.2 km but a
// vehicle to ~14 km, and the scene itself (terrain, structures) is
// resolvable much farther.  The spec's own worked example (haze 0.2 ->
// 11.3 km, the horizon) confirms the driver must NOT hard-cap at the
// human-detection range.  Johnson is documented in the issue and left
// to the player's optics; the driver caps by horizon and clarity only.
// (Optic magnification does NOT extend the scene caps: a scope does not
// see through fog or beyond the horizon - it resolves what is already
// within them.  The driver is scene physics, not target resolution.)
private _acuityM = 1e6;

// ─── Night sensitivity ───────────────────────────────────────────────────
// NELM 2 (city) -> ~100 m; NELM 6.5 (dark sky) -> ~1.45 km.
private _nightM = 1e6;   // no limit in daylight
if (_sunDown > 0 && _nelm < 6) then {
    _nightM = 100 + ((_nelm - 2) * 300);
};

// ─── Combine ─────────────────────────────────────────────────────────────
// Explicit min chain (avoids BIS_fnc_min, not compiled on all headless
// loads, and selectMin, which the HEMTT parser rejects in assignments).
private _target = _horizonM min _visM min _acuityM min _nightM min 12000;
_target = _target max 150;   // engine floor; never less than a room

// ─── Object view-distance target (issue #139) ────────────────────────────
// BI's Performance Optimisation page names OBJECT view distance "the CPU
// killer" - the dominant cost at range, and their guidance is to set it
// to 1/3 to 1/2 of terrain view distance.  Computed above the interface
// gate because the shadow conflict clamp needs it and the shadow state is
// published headless.
private _objTarget = (_target * 0.5) min 2000;   // 1/2 terrain, cap 2 km

// ─── Scene-aware shadow distance (aee-workshop-copy item 6) ──────────────
// Settings (AEE Optics > Shadows).  The values are re-derived from Adaptive
// Shadows (Workshop 3792830104); no mod content is copied.
private _shadowEnabled = missionNamespace getVariable [QGVAR(shadowAdaptiveEnabled), true];
private _shadowMinSetting = missionNamespace getVariable [QGVAR(shadowMinDistance), 50];
private _shadowMaxSetting = missionNamespace getVariable [QGVAR(shadowMaxDistance), 500];
private _shadowSampleCount = missionNamespace getVariable [QGVAR(shadowSampleCount), 13];
private _shadowUpdateInterval = missionNamespace getVariable [QGVAR(shadowUpdateInterval), 0.10];
private _shadowSensitivity = missionNamespace getVariable [QGVAR(shadowOpeningSensitivity), 12];
private _shadowFarInfluence = missionNamespace getVariable [QGVAR(shadowFarSceneInfluence), 75];
private _shadowMovementProtection = missionNamespace getVariable [QGVAR(shadowMovementProtection), 0.6];
private _shadowTurnProtection = missionNamespace getVariable [QGVAR(shadowCameraTurnProtection), 0];
private _shadowOpticsProtection = missionNamespace getVariable [QGVAR(shadowOpticsProtection), 0];
private _shadowTargetFPS = missionNamespace getVariable [QGVAR(shadowTargetFPS), 0];

// Context probe constants for the classifier (aee-workshop-copy item 6).  A
// hit at or below the close range counts as a close hit; the ceiling probe is
// ONE upward lineIntersectsSurfaces of this length.  UNSOURCED heuristics.
private _CONTEXT_CLOSE_M = 12;
private _CONTEXT_CEILING_M = 30;

private _effectiveShadowMax = ((_shadowMaxSetting max 0) min 2000) min (_objTarget max 0);
private _effectiveShadowMin = (_shadowMinSetting max 0) min _effectiveShadowMax;

private _shadowTarget = _objTarget * 0.25;   // legacy fixed element when disabled
private _shadowScene = "UNKNOWN";
private _shadowCoverage = 0;

if (_shadowEnabled && _effectiveShadowMax > 1) then {
    private _lastUpdate = missionNamespace getVariable [QGVAR(shadowLastUpdate), -1e9];
    private _now = diag_tickTime;
    private _interval = (_shadowUpdateInterval max 0.10) min 2;

    if (hasInterface && {visibleMap}) then {
        // The map is open: skip sampling and hold the last published value.
        _shadowTarget = missionNamespace getVariable [QGVAR(shadowTarget), _shadowTarget];
        _shadowScene = missionNamespace getVariable [QGVAR(shadowScene), _shadowScene];
        _shadowCoverage = missionNamespace getVariable [QGVAR(shadowCoverage), _shadowCoverage];
    } else {
        if (_now - _lastUpdate >= _interval) then {
            missionNamespace setVariable [QGVAR(shadowLastUpdate), _now];

            // Player-derived inputs.  Headless the camera and the player are
            // absent, so the sampling is skipped and the classifier falls
            // back to the minimum; the math still runs and publishes.
            private _inVehicle = false;
            private _optics = false;
            private _speed = 0;
            if (hasInterface && {!isNull player}) then {
                private _veh = vehicle player;
                _inVehicle = _veh isNotEqualTo player;
                _optics = (cameraView isEqualTo "GUNNER");
                _speed = vectorMagnitude (velocity player);
            };

            // Engine scene sampling with the pure pattern kernel.
            private _samples = [];
            private _context = [false, 0, 0, 12, 0];
            if (hasInterface && {!isNull player}) then {
                private _cameraASL = AGLToASL (positionCameraToWorld [0, 0, 0]);
                private _ignoreOne = player;
                private _ignoreTwo = vehicle player;
                if (_ignoreTwo isEqualTo _ignoreOne) then { _ignoreTwo = objNull; };
                private _pattern = [_shadowSampleCount, _optics] call FUNC(shadowSamplePattern);
                private _rayDistance = _effectiveShadowMax;

                for "_i" from 0 to ((count _pattern) - 1) do {
                    private _point = _pattern select _i;
                    private _screenX = _point select 0;
                    private _screenY = _point select 1;
                    private _weight = _point select 2;
                    private _direction = vectorNormalized (screenToWorldDirection [_screenX, _screenY]);

                    if (count _direction == 3 && {vectorMagnitude _direction > 0.5}) then {
                        private _endASL = _cameraASL vectorAdd (_direction vectorMultiply _rayDistance);
                        private _hits = lineIntersectsSurfaces [
                            _cameraASL, _endASL, _ignoreOne, _ignoreTwo,
                            true, 1, "VIEW", "NONE", true
                        ];

                        if (count _hits > 0) then {
                            private _hit = _hits select 0;
                            private _hitASL = _hit select 0;
                            private _hitObject = if (count _hit > 2) then {_hit select 2} else {objNull};
                            private _parentObject = if (count _hit > 3) then {_hit select 3} else {objNull};
                            private _distance = _cameraASL vectorDistance _hitASL;
                            private _kind = 1;
                            if (!isNull _hitObject || {!isNull _parentObject}) then { _kind = 0; };
                            _samples pushBack [_distance max 0, _weight, _screenX, _screenY, _kind];
                        } else {
                            private _kind = 3;
                            if ((_direction select 2) <= 0.18) then { _kind = 2; };
                            _samples pushBack [_rayDistance, _weight, _screenX, _screenY, _kind];
                        };
                    };
                };
            };

            // Populate the classifier context from the sample pass.  The hit
            // count and the close-hit count come free from the samples already
            // cast; the ceiling test is ONE upward lineIntersectsSurfaces.
            // The shape and the semantics match fnc_shadowClassifyScene:
            // [ceilingHit, horizontalHits, closeHits, averageContextDistance,
            // probeCount].  Populating it removes the dead interior branch the
            // earlier empty context left in the classifier.
            if (_samples isNotEqualTo []) then {
                private _hitCount = 0;
                private _closeHits = 0;
                private _hitDistanceSum = 0;
                for "_i" from 0 to ((count _samples) - 1) do {
                    private _sample = _samples select _i;
                    private _kind = _sample select 4;
                    if (_kind == 0 || _kind == 1) then {
                        private _distance = _sample select 0;
                        _hitCount = _hitCount + 1;
                        _hitDistanceSum = _hitDistanceSum + _distance;
                        if (_distance <= _CONTEXT_CLOSE_M) then {
                            _closeHits = _closeHits + 1;
                        };
                    };
                };
                private _averageContext = if (_hitCount > 0) then {
                    _hitDistanceSum / _hitCount
                } else {
                    _CONTEXT_CLOSE_M
                };
                private _ceilingHit = false;
                if (hasInterface && {!isNull player}) then {
                    private _upFrom = AGLToASL (positionCameraToWorld [0, 0, 0]);
                    private _upTo = _upFrom vectorAdd [0, 0, _CONTEXT_CEILING_M];
                    private _upHits = lineIntersectsSurfaces [
                        _upFrom, _upTo, player, objNull,
                        true, 1, "VIEW", "NONE", true
                    ];
                    _ceilingHit = count _upHits > 0;
                };
                _context = [
                    _ceilingHit, _hitCount, _closeHits, _averageContext,
                    count _samples
                ];
            };

            // Classify the scene.
            private _analysis = [
                _samples, _effectiveShadowMin, _context, _effectiveShadowMax,
                _shadowSensitivity, _shadowFarInfluence
            ] call FUNC(shadowClassifyScene);
            _analysis params [
                "_rawDepth", "_sceneType", "_nearDepth", "_farDepth",
                "_openingCoverage", "_interiorScore", "_terrainCoverage"
            ];
            _shadowScene = _sceneType;
            _shadowCoverage = _openingCoverage;

            // Stabilize the depth and the scene state (driver-owned state).
            private _state = missionNamespace getVariable [QGVAR(shadowState), ["OUTSIDE", 0, 0, 0, "NEAR", "", -1, 0]];
            private _stabilized = [
                _rawDepth, _sceneType, _now, _interiorScore, _openingCoverage,
                _shadowSensitivity, 0.3, _state
            ] call FUNC(shadowStabilizeDepth);
            _stabilized params ["_stableDepth", "_sceneState", "_fastDecrease", "_newState"];
            missionNamespace setVariable [QGVAR(shadowState), _newState];

            // Target with the protection margins.  The margin array is
            // [base, movement, vehicle, camera turn, optics].
            private _margins = [12, _shadowMovementProtection, 1.25, _shadowTurnProtection, _shadowOpticsProtection];
            private _targetDistance = [
                _stableDepth, _effectiveShadowMin, _effectiveShadowMax, 0,
                _sceneState, _speed, _inVehicle, _optics, _margins
            ] call FUNC(shadowTargetDistance);

            // Conflict detection: never above the object target or the
            // engine shadow maximum.  The shadow path never calls
            // setViewDistance.
            _targetDistance = _targetDistance min _objTarget;
            private _engineMax = 0;
            if (hasInterface) then { _engineMax = getShadowDistance; };
            if (_engineMax > 0) then { _targetDistance = _targetDistance min _engineMax; };

            // Rate limit the shadow ramp (separate from the terrain and the
            // object ramps).
            private _current = 0;
            if (hasInterface) then { _current = getShadowDistance; };
            private _deltaTime = (_now - _lastUpdate) max 0.001;
            private _candidate = [_targetDistance, _current, _deltaTime, 2000, 1000, _fastDecrease] call FUNC(shadowSmoothDistance);

            // Frame-rate governor (the driver samples the frame rate; the
            // kernel never reads diag_fps).
            private _fpsRaw = 60;
            if (hasInterface) then {
                _fpsRaw = (((diag_fps max 1) * 0.85) + ((diag_fpsMin max 1) * 0.15)) max 1;
            };
            private _fpsSmooth = missionNamespace getVariable [QGVAR(shadowFpsSmooth), 60];
            private _ceiling = missionNamespace getVariable [QGVAR(shadowFpsCeiling), _effectiveShadowMax];
            private _governed = [
                _fpsSmooth, _fpsRaw, _shadowTargetFPS, 3, _ceiling,
                _effectiveShadowMin, _effectiveShadowMax, _deltaTime, 0.5
            ] call FUNC(shadowFpsGovernor);
            _governed params ["_fpsSmoothNew", "_ceilingNew"];
            missionNamespace setVariable [QGVAR(shadowFpsSmooth), _fpsSmoothNew];
            missionNamespace setVariable [QGVAR(shadowFpsCeiling), _ceilingNew];

            _shadowTarget = ((_candidate min _ceilingNew) max 0) min _objTarget;
        } else {
            // Between updates: hold the last published value.
            _shadowTarget = missionNamespace getVariable [QGVAR(shadowTarget), _shadowTarget];
            _shadowScene = missionNamespace getVariable [QGVAR(shadowScene), _shadowScene];
            _shadowCoverage = missionNamespace getVariable [QGVAR(shadowCoverage), _shadowCoverage];
        };
    };
};

// ─── Publish the shadow state above the interface gate ───────────────────
// A dedicated server has hasInterface false, so the probe can only see a
// value published here, above the exit.
missionNamespace setVariable [QGVAR(shadowTarget), _shadowTarget];
missionNamespace setVariable [QGVAR(shadowScene), _shadowScene];
missionNamespace setVariable [QGVAR(shadowCoverage), _shadowCoverage];
// The terrain target and sigma are published here too, so a headless probe
// can derive the object target the shadow target is clamped to.
missionNamespace setVariable [QGVAR(viewDistanceTarget), _target];
missionNamespace setVariable [QGVAR(viewDistanceSigma), _sigmaTotal];

// ─── Rate limit: 500 m deadband + 4 s ramp, 1 Hz ─────────────────────────
// Client-only: the headless server has no camera to set.  The math above
// always runs (cheap, publishes diagnostics); only the engine call is
// interface-gated.
if (!hasInterface) exitWith { nil };
private _current = viewDistance;
private _new = if ((abs (_target - _current)) > 500) then {
    _current + ((_target - _current) min 500 max -500)
} else {
    _current
};
if (_new != _current) then {
    _new spawn {
        params ["_to"];
        private _from = viewDistance;
        private _t = 0;
        while {_t < 4} do {
            setViewDistance (round (_from + ((_to - _from) * (_t / 4))));
            sleep 0.1;
            _t = _t + 0.1;
        };
        setViewDistance (round _to);
    };
};

// ─── Object view distance (issue #139) ───────────────────────────────────
// BI's Performance Optimisation page names OBJECT view distance "the CPU
// killer" - the dominant cost at range, and their guidance is to set it
// to 1/3 to 1/2 of terrain view distance.  AEE drives terrain distance
// from physics (above); this drives object distance to follow, so the
// engine does not render object detail the eye cannot resolve anyway.
// The object ramp preserves the engine's own shadow element, because the
// shadow distance has its own trigger below and this ramp must not clobber
// it with a stale value.
private _objCurrent = getObjectViewDistance select 0;
private _newObj = if ((abs (_objTarget - _objCurrent)) > 200) then {
    _objCurrent + ((_objTarget - _objCurrent) min 200 max -200)
} else {
    _objCurrent
};
if (_newObj != _objCurrent) then {
    [_newObj] spawn {
        params ["_to"];
        private _from = getObjectViewDistance select 0;
        private _t = 0;
        while {_t < 4} do {
            setObjectViewDistance [
                round (_from + ((_to - _from) * (_t / 4))),
                round ((getObjectViewDistance) select 1)
            ];
            sleep 0.1;
            _t = _t + 0.1;
        };
        setObjectViewDistance [
            round _to, round ((getObjectViewDistance) select 1)
        ];
    };
};

// ─── Scene-aware shadow distance apply ───────────────────────────────────
// The shadow target has its OWN trigger, independent of the 200 m object
// deadband.  Without this the engine kept the previous shadow distance for
// the whole object deadband, so the scene-aware value was inert in steady
// state.  Only the second element is written and setViewDistance is never
// called from the shadow path.  When the feature is off this block is
// skipped, so the engine value is left in place and off restores the
// engine default.
if (_shadowEnabled) then {
    private _shadowCurrent = (getObjectViewDistance) select 1;
    if (abs (_shadowTarget - _shadowCurrent) > 25) then {
        setObjectViewDistance [
            ((getObjectViewDistance) select 0), round _shadowTarget
        ];
    };
};

// ─── Publish for diagnostics ─────────────────────────────────────────────
// (viewDistanceTarget and viewDistanceSigma are published above the
// interface gate, beside the shadow state.)

nil
