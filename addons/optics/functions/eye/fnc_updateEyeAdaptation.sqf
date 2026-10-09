#include "..\..\script_component.hpp"

/*
Per-frame eye adaptation driver (issue #141).

The engine can be told an aperture range and it then adapts at its own rate.
That rate is not human. This driver computes the adapted aperture each frame
and pins it, so AEE owns the rate and the engine cannot move the exposure.

The model runs in base-10 log-luminance. A fast pupil branch lags a slow cone
and rod pair. The CIE 191:2010 mesopic photopic fraction picks the mix.

Engine facts (from the retired bridge and the BI wiki):
  - setApertureNew has effect only when HDR is enabled.
  - The engine resets the aperture at mission start, so this must run after
    mission start. The starter runs from postInit and the PFH then holds it.
  - The command is client-side: the starter gates on hasInterface.

When a vision sensor is active the sensor owns the exposure, so this driver
stands down WITHOUT writing the aperture. On any stand-down it hands the
camera back to the engine with setAperture -1.

Debug hooks, set on missionNamespace:
  - aee_optics_eyeForceLux  Number > 0: replaces the scene illuminance.
  - aee_optics_eyeFreeze    Bool: holds the adapted state.
  - aee_optics_eyeForceMode "NIGHT" or "DAY": forces a dark or bright scene.
*/

private _player = call CBA_fnc_currentUnit;

// Missing, dead, or looking through a camera that is not the player's view:
// hand the camera back.
if (isNil "_player" || {isNull _player} || {!alive _player}) exitWith {
    if (!isNil QGVAR(eyePinned)) then {
        setAperture -1;
        GVAR(eyePinned) = nil;
    };
};

private _veh = vehicle _player;
if ((cameraOn != _player) && {cameraOn != _veh}) exitWith {
    if (!isNil QGVAR(eyePinned)) then {
        setAperture -1;
        GVAR(eyePinned) = nil;
    };
};

// A vision sensor owns the exposure.  The gate must come before any write.
if (currentVisionMode _player != 0) exitWith {};

// The operator turned the model off: hand the camera back once.
if (!GVAR(eyeAdaptationEnabled)) exitWith {
    if (!isNil QGVAR(eyePinned)) then {
        setAperture -1;
        GVAR(eyePinned) = nil;
    };
};

// The step is the REAL elapsed time between driver ticks, read from the one
// real-time clock (aee_core_simTime).  The driver runs on a 0.1 s PFH, and the
// scheduler services it at its own cadence, so a FRAME delta (diag_deltaTime)
// is smaller than the tick interval and would under-integrate the adaptation
// (the reported eye ran ~8x slower than its taus).  The clock is monotonic real
// time, so its delta is the true step.  It does NOT move on a skipTime, which
// the world clock below handles.  The first tick has no previous sample, so
// _dt = 0 and the model does not integrate.
private _now = missionNamespace getVariable [QEGVAR(core,simTime), diag_tickTime];
private _lastTick = missionNamespace getVariable [QGVAR(eyeLastTick), -1];
private _dt = 0;
if ((_lastTick isEqualType 0) && (_lastTick >= 0)) then {
    _dt = ((_now - _lastTick) max 0.01) min 0.5;
};
missionNamespace setVariable [QGVAR(eyeLastTick), _now];

// A time skip (skipTime, setDate, an Eden time change) jumps the world clock
// (dayTime) while the real clock and the mission `time` do not.  The eye must
// ARRIVE adapted to the new scene,
// exactly as at mission start (ADR-007), or it chases the jumped scene over the
// slow dark tau and the aperture is wrong for minutes.
private _hour = dayTime;
private _lastHour = missionNamespace getVariable [QGVAR(eyeLastHour), -1];
private _skipped = ["eyeTimeSkip", [_lastHour, _hour]] call EFUNC(core,dispatchKernel);
if (_skipped isEqualType "") then { _skipped = (_skipped == "true"); };
// The one clock owns the jump detector: when it raises clockJump for this
// tick, the eye re-seeds even if its own sample missed the edge.
if (missionNamespace getVariable [QEGVAR(core,clockJump), false]) then { _skipped = true; };
missionNamespace setVariable [QGVAR(eyeLastHour), _hour];

private _sample = call FUNC(eyeSampleScene);
if (_sample isEqualTo []) exitWith {};

private _sceneLux = _sample select 0;
private _localLux = _sample select 1;
private _sky = _sample select 2;

private _forceLux = missionNamespace getVariable [QGVAR(eyeForceLux), 0];
if ((_forceLux isEqualType 0) && _forceLux > 0) then { _sceneLux = _forceLux; };
private _forceMode = missionNamespace getVariable [QGVAR(eyeForceMode), ""];
if ((_forceMode isEqualType "") && _forceMode != "") then {
    if (_forceMode == "NIGHT") then { _sceneLux = 0.001; };
    if (_forceMode == "DAY") then { _sceneLux = 100000; };
};

// Muzzle-flash term: a separate additive term while the window is open. It
// is not folded into the engine dynamic term, so it cannot double-count.
// The transient raises only the luminance the eye ADAPTS to.  It is not part
// of the physical-sky model the core illuminance carries, so it stays OUT of
// the PUBLISHED scene (aee_optics_eyeSceneLux).  The cross-module invariant
// INV-1 (night_scene_agreement) compares the published scene against the core
// illuminance, so a shot must not move it (a 5.56 flash of 4500 lx raised a
// false warning: drift 4499.97 at a published scene of 4500.5 lx).
private _flashUntil = missionNamespace getVariable [QGVAR(eyeFlashUntil), 0];
private _flashLux = missionNamespace getVariable [QGVAR(eyeFlashLux), 0];
private _steadySceneLux = _sceneLux;
private _flashScene = [_sceneLux, _flashLux, _flashUntil, CBA_missionTime] call FUNC(eyeFlashScene);
_sceneLux = _flashScene select 1;
if ((_flashUntil isEqualType 0) && (CBA_missionTime >= _flashUntil)) then {
    if ((_flashLux isEqualType 0) && _flashLux != 0) then {
        missionNamespace setVariable [QGVAR(eyeFlashLux), 0];
    };
};

private _rawSceneLux = _sceneLux;
_sceneLux = _sceneLux max 1e-6;

// Reflectance assumption rho: luminance = rho * E / pi (mid-grey, UNSOURCED).
private _rho = GVAR(eyeReflectance);
private _lumScene = (_rho * _sceneLux) / pi;
private _xTarget = log (_lumScene max 1e-9);

// Fast pupil branch. The pupil sets the retinal illuminance, so its current
// diameter is the fast estimate of the scene light.
private _dSteady = ["eyePupilSteady", [_lumScene]] call EFUNC(core,dispatchKernel);
if (_dSteady isEqualType "") then { _dSteady = parseNumber _dSteady; };
private _dPrev = missionNamespace getVariable [QGVAR(eyePupil), -1];
if (!(_dPrev isEqualType 0) || _dPrev <= 0) then { _dPrev = _dSteady; };
// A skip re-seeds the fast pupil branch with the eye, so the first frame after
// the jump shows the new scene at its adapted diameter, not the old one.
if (_skipped) then { _dPrev = _dSteady; };
private _d = ["eyePupilStep", [_dPrev, _dSteady, _dt, GVAR(eyePupilTauConstrict), GVAR(eyePupilTauDilate)]] call EFUNC(core,dispatchKernel);
if (_d isEqualType "") then { _d = parseNumber _d; };

// Invert the steady fit to read the luminance the pupil's diameter implies.
private _u = ((4.9 - _d) / 3.0) max (-0.999) min 0.999;
private _logB = ((0.5 * (ln ((1 + _u) / (1 - _u)))) / 0.4) - 0.5;
private _xFast = log (3.183 * (10 ^ _logB));

// Slow pools.  On the first VALID sample the eye arrives ADAPTED: a night
// start is already dark-adapted and a day start light-adapted, so the state
// is the scene's own log-luminance and there is no warm-up from a fixed
// default (the operator requirement).  A zero scene means the illuminance
// layer has not published yet, so wait for a valid sample rather than
// initialise dark at noon.
private _state = missionNamespace getVariable [QGVAR(eyeAdaptState), []];
private _initialised = missionNamespace getVariable [QGVAR(eyeAdaptInitialised), false];
private _haveState = (_state isEqualType []) && {(count _state) == 2};
// A skip invalidates the adapted state: drop it and fall through to the
// arrive-adapted seed, the same rule the mission start uses (eyeAdaptInit).
if (_skipped) then {
    _state = [];
    _haveState = false;
    _initialised = false;
    missionNamespace setVariable [QGVAR(eyeAdaptState), []];
};
if (!_initialised) then {
    if (_haveState) then {
        _initialised = true;
    } else {
        if (_rawSceneLux > 0) then {
            _state = [_xTarget] call FUNC(eyeAdaptInit);
            _initialised = true;
        };
    };
};
if (!_initialised) exitWith {};
missionNamespace setVariable [QGVAR(eyeAdaptInitialised), _initialised];
private _step = ["eyeAdaptStep", [_state, _xTarget, _dt, GVAR(eyeTauLight), GVAR(eyeTauDarkCone), GVAR(eyeTauDarkRod), 0]] call EFUNC(core,dispatchKernel);
if (_step isEqualType "") then { _step = parseSimpleArray _step; };

// The freeze hook holds the adapted state while the scene moves.
private _freeze = missionNamespace getVariable [QGVAR(eyeFreeze), false];
if (_freeze) then {
    _step = _state;
    _d = _dPrev;
    _xFast = missionNamespace getVariable [QGVAR(eyeFast), _xFast];
};

private _xCone = _step select 0;
private _xRod = _step select 1;

// _w is the CIE 191:2010 photopic fraction: near 1 the cones carry vision,
// near 0 the rods do, so _w weights the cone pool.
private _w = ["eyeMesopicWeight", [_lumScene, GVAR(eyeMesopicLow), GVAR(eyeMesopicHigh)]] call EFUNC(core,dispatchKernel);
if (_w isEqualType "") then { _w = parseNumber _w; };
private _xSlow = (_w * _xCone) + ((1 - _w) * _xRod);
private _kp = GVAR(eyeFastBlend);
private _x = ((1 - _kp) * _xSlow) + (_kp * _xFast);

private _adaptedLux = (pi / _rho) * (10 ^ _x);
private _v = [_adaptedLux] call FUNC(eyeAperture);

// Pin only on a meaningful change (the engine rounds the aperture anyway).
private _lastV = missionNamespace getVariable [QGVAR(eyeLastV), -1];
if ((isNil QGVAR(eyePinned)) || {abs(_v - _lastV) > 0.02}) then {
    setApertureNew [_v, _v, _v, 1];
    GVAR(eyeLastV) = _v;
    GVAR(eyePinned) = true;
};

GVAR(eyeAdaptState) = _step;
GVAR(eyePupil) = _d;
GVAR(eyeFast) = _xFast;

// Publish the adaptation state for the player-perception monitor: the level
// and the target, the direction, the effective tau and the time to adapt.
private _adaptState = [_step, _xTarget, _w, GVAR(eyeTauLight), GVAR(eyeTauDarkCone), GVAR(eyeTauDarkRod)] call FUNC(eyeAdaptState);

// Human-vision limits: the scotopic acuity and colour loss, the dark noise and
// the scattered glare.  Published for the render and the perception monitor.
// The glare angle is the angle from the view to the primary light source, and
// the fog drives the atmospheric in-scatter.  A local-source angle (headlights
// off to the side) needs the light scan to return the brightest direction; the
// sun/moon angle is available now.
private _viewAz = getDirVisual _player;
private _srcAz = missionNamespace getVariable [QEGVAR(core,lightAzimuth), _viewAz];
private _srcAngle = abs(_viewAz - _srcAz);
if (_srcAngle > 180) then { _srcAngle = 360 - _srcAngle; };
private _fogNow = ([] call EFUNC(core,getSmoothedWeather)) select 2;
if !(_fogNow isEqualType 0) then { _fogNow = 0; };
private _limits = [_adaptedLux, _w, _localLux, _srcAngle, _fogNow] call FUNC(eyeLimits);

missionNamespace setVariable [QGVAR(eyeSceneLux), _steadySceneLux];
missionNamespace setVariable [QGVAR(eyeAdaptedLux), _adaptedLux];
missionNamespace setVariable [QGVAR(eyeAperture), _v];
missionNamespace setVariable [QGVAR(eyePupilMm), _d];
missionNamespace setVariable [QGVAR(eyeMesopic), _w];
missionNamespace setVariable [QGVAR(eyeSkyFraction), _sky];
missionNamespace setVariable [QGVAR(eyeAdaptTargetLux), _sceneLux];
missionNamespace setVariable [QGVAR(eyeAdaptDirection), _adaptState select 0];
missionNamespace setVariable [QGVAR(eyeAdaptTau), _adaptState select 1];
missionNamespace setVariable [QGVAR(eyeAdaptTimeToAdapt), _adaptState select 2];
missionNamespace setVariable [QGVAR(eyeAcuity), _limits select 0];
missionNamespace setVariable [QGVAR(eyeColourLoss), _limits select 1];
missionNamespace setVariable [QGVAR(eyeDarkNoise), _limits select 2];
missionNamespace setVariable [QGVAR(eyeGlare), _limits select 3];
