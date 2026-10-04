#include "..\..\script_component.hpp"

/*
Aurora curtain render worker, driven at 2 Hz by fnc_renderAurora.

The space-weather model (fnc_calculateSpaceWeather) publishes
QGVAR(auroraVisibility) and QGVAR(auroraIntensity) from the Kp index, the
observer latitude, the night window and the cloud cover.  This worker draws
that state as a particle curtain in the northern sky.  The two oxygen
emission lines are colour-coded: 557.7 nm green at the base band and 630.0 nm
red above it (NOAA SWPC Aurora Tutorial).

The curtain is a client-only cosmetic effect: it uses no dynamic light beyond
the starfield's budget, no texture asset beyond the vanilla particle texture,
and no server object.

Debug hooks, set on missionNamespace:
  - aee_environmental_skyForce     Boolean, force the whole night sky on
  - aee_environmental_auroraForce  Number, -1 off, 0..1 forces that intensity
*/

private _sources = missionNamespace getVariable [QGVAR(auroraSources), []];

// ─── Gates and force hooks ────────────────────────────────────────────────
private _skyForce = missionNamespace getVariable ["aee_environmental_skyForce", false];
if !(_skyForce isEqualType false) then { _skyForce = false; };
private _auroraForce = missionNamespace getVariable ["aee_environmental_auroraForce", -1];
if !(_auroraForce isEqualType 0) then { _auroraForce = -1; };
private _settingOn = missionNamespace getVariable [QGVAR(dynamicAurora), true];
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 0];
if !(_sunElev isEqualType 0) then { _sunElev = 0; };
private _overcast = ([] call EFUNC(core,getSmoothedWeather)) select 1;
if !(_overcast isEqualType 0) then { _overcast = 0; };
private _visibility = missionNamespace getVariable [QGVAR(auroraVisibility), false];
private _intensity = missionNamespace getVariable [QGVAR(auroraIntensity), 0];
if !(_intensity isEqualType 0) then { _intensity = 0; };

// Effective state: whole-sky force first, then the aurora force, then the
// physics visibility.  The unforced path still honours the night and cloud
// gates; the forces bypass them.
private _active = false;
private _effIntensity = 0;
if (_skyForce) then {
    _active = true;
    _effIntensity = 0.6;
} else {
    if (_auroraForce >= 0) then {
        _active = _settingOn;
        _effIntensity = _auroraForce;
    } else {
        _active = _settingOn && _visibility;
        _effIntensity = _intensity;
        if ((_sunElev >= 0) || (_overcast >= 0.3)) then { _active = false; };
    };
};

if (!_active) exitWith {
    {
        deleteVehicle _x;
    } forEach (missionNamespace getVariable [QGVAR(auroraSources), []]);
    missionNamespace setVariable [QGVAR(auroraSources), []];
    missionNamespace setVariable [QGVAR(auroraActive), false];
    missionNamespace setVariable [QGVAR(auroraSourceCount), 0];
};

// ─── Build or refresh the curtains ────────────────────────────────────────
private _eyePos = ((call CBA_fnc_currentUnit) call EFUNC(core,getEyeState)) select 0;
private _origin = _eyePos vectorAdd ([0, 1, 0] vectorMultiply AURORA_RENDER_RADIUS);

private _green = _sources param [0, objNull];
if (isNull _green) then {
    _green = "#particlesource" createVehicleLocal [0, 0, 0];
    _sources set [0, _green];
};
private _red = _sources param [1, objNull];
if (isNull _red) then {
    _red = "#particlesource" createVehicleLocal [0, 0, 0];
    _sources set [1, _red];
};

private _greenColour = AURORA_GREEN;
private _redColour = AURORA_RED;
private _greenAlpha = (_effIntensity * 0.5) min 1;
private _redAlpha = (((_effIntensity - 0.6) / 0.4) max 0) min 1;

_green setPosASL (_origin vectorAdd [0, 0, AURORA_BASE_ALT_M]);
_green setParticleCircle [0, [0, 0, 0]];
_green setParticleRandom [2, [0, 0, 0], [0, 0, 0], 0, 0.1, [0, 0, 0, 0], 0, 0];
_green setParticleParams [["\A3\data_f\cl_basic", 1, 0, 1], "", "Billboard", 1, 8, [0, 0, 0], [0, 0, 1], 0, 10, 8, 0, [8000, AURORA_BAND_ALT_M, 0.1], [_greenColour + [_greenAlpha], _greenColour + [0]], [0.02], 1, 0, "", "", _green];
_green setDropInterval 0.05;

private _redInterval = 1e10;
if (_effIntensity > 0.6) then { _redInterval = 0.05; };
_red setPosASL (_origin vectorAdd [0, 0, AURORA_BASE_ALT_M + AURORA_BAND_ALT_M]);
_red setParticleCircle [0, [0, 0, 0]];
_red setParticleRandom [2, [0, 0, 0], [0, 0, 0], 0, 0.1, [0, 0, 0, 0], 0, 0];
_red setParticleParams [["\A3\data_f\cl_basic", 1, 0, 1], "", "Billboard", 1, 8, [0, 0, 0], [0, 0, 1], 0, 10, 8, 0, [8000, AURORA_BAND_ALT_M, 0.1], [_redColour + [_redAlpha], _redColour + [0]], [0.02], 1, 0, "", "", _red];
_red setDropInterval _redInterval;

missionNamespace setVariable [QGVAR(auroraSources), _sources];
missionNamespace setVariable [QGVAR(auroraActive), true];
missionNamespace setVariable [QGVAR(auroraSourceCount), ({ !isNull _x } count _sources)];
