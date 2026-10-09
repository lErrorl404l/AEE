#include "..\..\script_component.hpp"

/*
Player-perception driver (human-vision model, local player only).

Each tick this driver reads the state other modules already publish, folds
it into the perception schema and calls the pure kernel
FUNC(perceptionSample).  It then publishes the aggregate and its named
fields, emits one human line, and calls FUNC(perceptionDetectDeviation) to
set the deviation flags.

Client only.  It gates on hasInterface, on a living local player and on the
player's own camera, exactly as fnc_updateEyeAdaptation does.  On a
dedicated server it no-ops and publishes nothing: a server has no local
player and no client render state.

Published inputs, by module (each read with a safe default):
  core         aee_core_illuminanceLux, aee_core_ambientLux,
               aee_core_currentUVIndex, aee_core_currentWBGT,
               aee_core_windChillTemp, aee_core_currentHypothermiaRisk
  optics       aee_optics_eyeSceneLux, aee_optics_eyeAdaptedLux,
               aee_optics_eyeAperture, aee_optics_eyePupilMm,
               aee_optics_eyeMesopic, aee_optics_eyeRawSunElev,
               aee_optics_baseGradeActive, aee_optics_baseGradeCC,
               aee_vision_baseGradeGrain, aee_optics_solarGlareIntensity,
               aee_optics_mirageIntensity, aee_optics_snowBlindness,
               aee_optics_dewOnOptics, aee_optics_rainOnOptics
  nightvision  aee_nightvision_nvgGain, aee_nightvision_nvgTubeTier,
               aee_nightvision_nvgPerceived, aee_nightvision_nvgGateActive
  thermal      aee_thermal_display_thermalActive, aee_thermal_selTemperature
  eye fix      aee_optics_eyeAdaptState, aee_optics_eyeAdaptTargetLux,
               aee_optics_eyeAdaptDirection, aee_optics_eyeAdaptTau,
               aee_optics_eyeAdaptTimeToAdapt

The published aee_optics_baseGradeCC and aee_vision_baseGradeGrain are
ppEffect handles, not channel arrays.  The applied grade the deviation
kernel needs is reconstructed from the vision settings and the published
adapted luminance; the handles are read only to confirm the grade is live.

Force hooks (set on missionNamespace; debug console only, no CBA setting):
  aee_optics_perceptionForceLux      Number >= 0: replaces the scene lux.
  aee_optics_perceptionForceGrade    Array: replaces the applied grade.
  aee_optics_perceptionForceNvg      Array: replaces the NVG state.
  aee_optics_perceptionForceThermal  Array: replaces the thermal state.

Settings read:
  aee_vision_perceptionMonitor       Bool: publish and log when true.
  aee_vision_perceptionHud           Bool: show the overlay when true.
  aee_vision_perceptionInterval      Number: minimum seconds between samples.

Publishes:
  aee_optics_perceptionState         Array: the kernel result, 14 fields.
  aee_optics_perceptionLine          String: the one-line human state.
  aee_optics_perceptionLux           Number: the scene illuminance, lux.
  aee_optics_perceptionAperture      Number: the applied aperture.
  aee_optics_perceptionGrade         Array: the applied grade channels.
  aee_optics_perceptionFlags         Array: the deviation flags.

Arguments: none.

Returns: nothing.
*/

if (!hasInterface) exitWith {};

// The monitor switch.  The debug surface registers the setting; the driver
// is valid before it, so the default is on.
if (!(missionNamespace getVariable [QGVAR(perceptionMonitor), true])) exitWith {};

private _player = call CBA_fnc_currentUnit;
if ((isNil "_player") || (isNull _player) || (!alive _player)) exitWith {};

private _veh = vehicle _player;
if ((cameraOn != _player) && (cameraOn != _veh)) exitWith {};

// Sample throttle.  The PFH ticks at 0.5 s, so the effective floor is 0.5 s.
private _interval = missionNamespace getVariable [QGVAR(perceptionInterval), 0.5];
if !(_interval isEqualType 0) then { _interval = 0.5; };
private _last = missionNamespace getVariable [QGVAR(perceptionLast), -1];
if !(_last isEqualType 0) then { _last = -1; };
if ((_last >= 0) && (CBA_missionTime - _last < _interval)) exitWith {};
missionNamespace setVariable [QGVAR(perceptionLast), CBA_missionTime];

// ── Eye and scene state ─────────────────────────────────────────────────────
private _sceneLux = missionNamespace getVariable [QEGVAR(eye,eyeSceneLux), 1];
if !(_sceneLux isEqualType 0) then { _sceneLux = 1; };
private _coreLux = missionNamespace getVariable ["aee_core_illuminanceLux", -1];
if ((_sceneLux <= 0) && (_coreLux isEqualType 0) && (_coreLux > 0)) then { _sceneLux = _coreLux; };
private _forceLux = missionNamespace getVariable [QGVAR(perceptionForceLux), -1];
if ((_forceLux isEqualType 0) && (_forceLux >= 0)) then { _sceneLux = _forceLux; };

private _adaptedLux = missionNamespace getVariable [QEGVAR(eye,eyeAdaptedLux), 1];
if !(_adaptedLux isEqualType 0) then { _adaptedLux = 1; };
private _aperture = missionNamespace getVariable [QEGVAR(eye,eyeAperture), 8];
if !(_aperture isEqualType 0) then { _aperture = 8; };
private _pupil = missionNamespace getVariable [QEGVAR(eye,eyePupilMm), 4.9];
if !(_pupil isEqualType 0) then { _pupil = 4.9; };
private _mesopic = missionNamespace getVariable [QEGVAR(eye,eyeMesopic), 1];
if !(_mesopic isEqualType 0) then { _mesopic = 1; };
private _sunElev = missionNamespace getVariable [QEGVAR(eye,eyeRawSunElev), -90];
private _ambientLux = missionNamespace getVariable ["aee_core_ambientLux", 0];

// The applied grade.  The render reads the same pure model, so the expected
// grade is the applied grade unless a hook overrides it.
private _toneStrength = missionNamespace getVariable [QGVAR(visionToneStrength), 0.25];
private _contrastScale = missionNamespace getVariable [QGVAR(visionContrastScale), 1];
private _desatMax = missionNamespace getVariable [QGVAR(visionMesopicDesaturation), 0];
private _desatAlpha = ((_desatMax * (1 - _mesopic)) max 0) min 0.10;
private _tone = [_adaptedLux, 100, _toneStrength, _contrastScale] call FUNC(perceptionToneResponse);
private _expectedGrade = [_tone, [1, 1, 0], _toneStrength, _desatAlpha] call FUNC(perceptionBaseGrade);

// The published base-grade handles say whether a grade is live.  When the
// base grade stands down (a sensor mode, death or the module off) no grade
// is applied, so the expectation is the identity and the deviation stays
// clear.
private _baseGradeCC = missionNamespace getVariable [QGVAR(baseGradeCC), -1];
private _baseGradeGrain = missionNamespace getVariable [QGVAR(baseGradeGrain), -1];
private _gradeActive = (_baseGradeCC isEqualType 0) && (_baseGradeCC >= 0);
if (!_gradeActive) then { _expectedGrade = [1, 1, 0, 0]; };

private _appliedGrade = _expectedGrade;
private _forceGrade = missionNamespace getVariable [QGVAR(perceptionForceGrade), []];
if ((_forceGrade isEqualType []) && ((count _forceGrade) >= 3)) then { _appliedGrade = _forceGrade; };

// ── Eye adaptation temporal state (T10) ─────────────────────────────────────
private _adaptRaw = missionNamespace getVariable [QEGVAR(eye,eyeAdaptState), [0, 0]];
private _adaptTargetLux = missionNamespace getVariable [QEGVAR(eye,eyeAdaptTargetLux), 1];
private _adaptDirection = missionNamespace getVariable [QEGVAR(eye,eyeAdaptDirection), 0];
private _adaptTau = missionNamespace getVariable [QEGVAR(eye,eyeAdaptTau), 0];
private _adaptTime = missionNamespace getVariable [QEGVAR(eye,eyeAdaptTimeToAdapt), 0];
private _adaptState = [
    _adaptRaw, _adaptTargetLux, _mesopic,
    _adaptDirection, _adaptTau, _adaptTime,
    EGVAR(eye,eyeReflectance)
] call FUNC(perceptionAdaptState);

// ── NVG and thermal state ───────────────────────────────────────────────────
private _nvgGain = missionNamespace getVariable ["aee_nightvision_nvgGain", 0];
private _nvgTier = missionNamespace getVariable ["aee_nightvision_nvgTubeTier", "NONE"];
private _nvgPerceived = missionNamespace getVariable ["aee_nightvision_nvgPerceived", 0];
private _nvgGate = missionNamespace getVariable ["aee_nightvision_nvgGateActive", false];
private _nvgActive = (_nvgGain isEqualType 0) && (_nvgGain > 0);
private _nvgState = [_nvgActive, _nvgGain, _nvgTier, _nvgPerceived, _nvgGate];
private _forceNvg = missionNamespace getVariable [QGVAR(perceptionForceNvg), []];
if ((_forceNvg isEqualType []) && ((count _forceNvg) >= 5)) then { _nvgState = _forceNvg; };

private _thermalActive = missionNamespace getVariable ["aee_thermal_display_thermalActive", false];
private _selTempRaw = missionNamespace getVariable ["aee_thermal_selTemperature", 0];
private _selTempC = 0;
if (_selTempRaw isEqualType 0) then {
    _selTempC = _selTempRaw;
} else {
    private _vals = values _selTempRaw;
    if ((_vals isEqualType []) && (_vals isNotEqualTo [])) then {
        private _sum = 0;
        private _n = 0;
        { if (_x isEqualType 0) then { _sum = _sum + _x; _n = _n + 1; }; } forEach _vals;
        if (_n > 0) then { _selTempC = _sum / _n; };
    };
};
private _thermalState = [_thermalActive, 0, 0, _selTempC, 0];
private _forceThermal = missionNamespace getVariable [QGVAR(perceptionForceThermal), []];
if ((_forceThermal isEqualType []) && ((count _forceThermal) >= 5)) then { _thermalState = _forceThermal; };

// ── Environment and stress ──────────────────────────────────────────────────
private _uvIndex = missionNamespace getVariable ["aee_core_currentUVIndex", 0];
if !(_uvIndex isEqualType 0) then { _uvIndex = 0; };
private _wbgt = missionNamespace getVariable ["aee_core_currentWBGT", 0];
private _windChill = missionNamespace getVariable ["aee_core_windChillTemp", 0];
private _hypo = missionNamespace getVariable ["aee_core_currentHypothermiaRisk", 0];
private _stressState = [_wbgt, _windChill, _hypo, 0];

private _effects = [];
private _glare = missionNamespace getVariable [QEGVAR(optics,solarGlareIntensity), 0];
if ((_glare isEqualType 0) && (_glare > 0)) then { _effects pushBack "solarGlare"; };
private _mirage = missionNamespace getVariable [QEGVAR(optics,mirageIntensity), 0];
if ((_mirage isEqualType 0) && (_mirage > 0)) then { _effects pushBack "mirage"; };
private _snow = missionNamespace getVariable [QEGVAR(optics,snowBlindness), 0];
if ((_snow isEqualType 0) && (_snow > 0)) then { _effects pushBack "snowBlindness"; };
private _dew = missionNamespace getVariable [QEGVAR(optics,dewOnOptics), 0];
if ((_dew isEqualType 0) && (_dew > 0)) then { _effects pushBack "dew"; };
private _rain = missionNamespace getVariable [QEGVAR(optics,rainOnOptics), 0];
if ((_rain isEqualType 0) && (_rain > 0)) then { _effects pushBack "rain"; };

// ── Aggregate ───────────────────────────────────────────────────────────────
private _map = [
    ["sceneLux", _sceneLux],
    ["adaptedLux", _adaptedLux],
    ["eyeAperture", _aperture],
    ["pupilMm", _pupil],
    ["mesopicWeight", _mesopic],
    ["appliedGrade", _appliedGrade],
    ["cameraTint", [1, 1, 1, 1]],
    ["nvgState", _nvgState],
    ["thermalState", _thermalState],
    ["uvIndex", _uvIndex],
    ["stressState", _stressState],
    ["injuryState", [0, 0]],
    ["activeEffects", _effects],
    ["eyeAdaptationState", _adaptState]
];
private _state = [_map] call FUNC(perceptionSample);

// ── Deviation flags (T11) ───────────────────────────────────────────────────
// SOURCED clamp ends: aperture night anchor 8 and daylight anchor 50
// (fnc_eyeAperture); pupil 1.9 to 8.0 mm (fnc_eyePupilSteady).
private _prevTime = missionNamespace getVariable [QGVAR(perceptionPrevTimeToAdapt), -1];
private _flags = [
    _expectedGrade, _appliedGrade, _adaptState,
    _aperture, _pupil, 8, 50, 1.9, 8.0,
    _sceneLux, _adaptedLux, _prevTime
] call FUNC(perceptionDetectDeviation);
missionNamespace setVariable [QGVAR(perceptionPrevTimeToAdapt), _adaptState select 3];

// ── Publish ─────────────────────────────────────────────────────────────────
private _line = "perception scene=" + (str _sceneLux)
    + " lx ambient=" + (str _ambientLux)
    + " sunElev=" + (str _sunElev)
    + " adapted=" + (str _adaptedLux)
    + " aperture=" + (str _aperture)
    + " pupil=" + (str _pupil)
    + " mm mesopic=" + (str _mesopic)
    + " nvg=" + (str (_nvgState select 0))
    + " effects=" + (str _effects)
    + " grade=" + (str _appliedGrade)
    + " baseCC=" + (str _baseGradeCC)
    + " baseGrain=" + (str _baseGradeGrain)
    + " adapt=" + (str _adaptState)
    + " flags=" + (str _flags);

missionNamespace setVariable [QGVAR(perceptionState), _state];
missionNamespace setVariable [QGVAR(perceptionLine), _line];
missionNamespace setVariable [QGVAR(perceptionLux), _sceneLux];
missionNamespace setVariable [QGVAR(perceptionAperture), _aperture];
missionNamespace setVariable [QGVAR(perceptionGrade), _appliedGrade];
missionNamespace setVariable [QGVAR(perceptionFlags), _flags];

// One INFO line on the first sample, DEBUG after.  AEE_LOG_DEBUG is gated by
// the module trace switch.
private _logged = missionNamespace getVariable [QGVAR(perceptionLogged), false];
if (_logged) then {
    AEE_LOG_DEBUG(_line);
} else {
    missionNamespace setVariable [QGVAR(perceptionLogged), true];
    AEE_LOG_INFO(_line);
};

// ── Debug HUD ───────────────────────────────────────────────────────────────
if (missionNamespace getVariable [QGVAR(perceptionHud), false]) then {
    private _layer = ["aee_optics_perception"] call BIS_fnc_rscLayer;
    private _display = uiNamespace getVariable [QGVAR(perceptionHudDisplay), displayNull];
    if (isNull _display) then {
        _layer cutRsc [QGVAR(perceptionHud), "PLAIN", -1, false];
        _display = uiNamespace getVariable [QGVAR(perceptionHudDisplay), displayNull];
    };
    if (!isNull _display) then {
        (_display displayCtrl 10811) ctrlSetText _line;
    };
};
