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

private _dt = (diag_deltaTime max 0.01) min 0.5;

private _sample = call FUNC(eyeSampleScene);
if (_sample isEqualTo []) exitWith {};

private _sceneLux = _sample select 0;
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
private _flashUntil = missionNamespace getVariable [QGVAR(eyeFlashUntil), 0];
private _flashLux = missionNamespace getVariable [QGVAR(eyeFlashLux), 0];
if ((_flashUntil isEqualType 0) && CBA_missionTime < _flashUntil) then {
    if (_flashLux isEqualType 0) then { _sceneLux = _sceneLux + _flashLux; };
} else {
    if ((_flashLux isEqualType 0) && _flashLux != 0) then {
        missionNamespace setVariable [QGVAR(eyeFlashLux), 0];
    };
};

_sceneLux = _sceneLux max 1e-6;

// Reflectance assumption rho: luminance = rho * E / pi (mid-grey, UNSOURCED).
private _rho = GVAR(eyeReflectance);
private _lumScene = (_rho * _sceneLux) / pi;
private _xTarget = log (_lumScene max 1e-9);

// Fast pupil branch. The pupil sets the retinal illuminance, so its current
// diameter is the fast estimate of the scene light.
private _dSteady = [_lumScene] call FUNC(eyePupilSteady);
private _dPrev = missionNamespace getVariable [QGVAR(eyePupil), -1];
if (!(_dPrev isEqualType 0) || _dPrev <= 0) then { _dPrev = _dSteady; };
private _d = [_dPrev, _dSteady, _dt, GVAR(eyePupilTauConstrict), GVAR(eyePupilTauDilate)] call FUNC(eyePupilStep);

// Invert the steady fit to read the luminance the pupil's diameter implies.
private _u = ((4.9 - _d) / 3.0) max (-0.999) min 0.999;
private _logB = ((0.5 * (ln ((1 + _u) / (1 - _u)))) / 0.4) - 0.5;
private _xFast = log (3.183 * (10 ^ _logB));

// Slow pools.
private _state = missionNamespace getVariable [QGVAR(eyeState), []];
if (!(_state isEqualType []) || {(count _state) != 2}) then { _state = [_xTarget, _xTarget]; };
private _step = [_state, _xTarget, _dt, GVAR(eyeTauLight), GVAR(eyeTauDarkCone), GVAR(eyeTauDarkRod), 0] call FUNC(eyeAdaptStep);

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
private _w = [_lumScene, GVAR(eyeMesopicLow), GVAR(eyeMesopicHigh)] call FUNC(eyeMesopicWeight);
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

GVAR(eyeState) = _step;
GVAR(eyePupil) = _d;
GVAR(eyeFast) = _xFast;

missionNamespace setVariable [QGVAR(eyeSceneLux), _sceneLux];
missionNamespace setVariable [QGVAR(eyeAdaptedLux), _adaptedLux];
missionNamespace setVariable [QGVAR(eyeAperture), _v];
missionNamespace setVariable [QGVAR(eyePupilMm), _d];
missionNamespace setVariable [QGVAR(eyeMesopic), _w];
missionNamespace setVariable [QGVAR(eyeSkyFraction), _sky];
