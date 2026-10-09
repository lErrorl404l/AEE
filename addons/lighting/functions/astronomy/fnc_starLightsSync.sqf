#include "..\..\script_component.hpp"

/*
 * Starfield sync, driven at 4 Hz by fnc_renderDynamicStars.
 *
 * A star is a point light at optical infinity: each visible star is a local
 * "#lightpoint" whose FLARE is the visible point.  The flare needs
 * setLightUseFlare, setLightFlareSize, setLightFlareMaxDistance and a
 * non-black setLightColor (BIKI Light Source Tutorial).  setLightAmbient
 * stays black and setLightBrightness is small, so the field does not
 * illuminate the ground - starlight at observer scale is negligible.
 * Brightness and flare size follow the magnitude via fnc_starMagnitude
 * (Pogson flux).  The direction is world-fixed (fnc_starDirection), so the
 * light is re-anchored to the camera each pass with no parallax.
 *
 * On disable, daylight or solid overcast every light is deleted and the
 * registry cleared.
 */

private _lights = missionNamespace getVariable [QGVAR(starLights), []];

// Debug hooks, set on missionNamespace:
//   aee_lighting_skyForce    Boolean, force the whole night sky on
//   aee_lighting_starsForce  Number, forced limiting magnitude; a value
//     above 0 raises the visible set so the faint bulk is catalogued
private _skyForce = missionNamespace getVariable ["aee_lighting_skyForce", false];
if !(_skyForce isEqualType false) then { _skyForce = false; };

// Disabled, daylight or solid overcast: clear and idle.  The whole-sky force
// bypasses every gate.  The NELM chain clamps at 2.0, so Sirius and Canopus
// would otherwise draw in daylight; the hard overcast gate handles the
// point-occlusion case the integrated sky model cannot (issue #122).
private _settingOn = missionNamespace getVariable [QGVAR(dynamicStars), true];
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 0];
if !(_sunElev isEqualType 0) then { _sunElev = 0; };
private _overcast = ([] call EFUNC(core,getSmoothedWeather)) select 1;
if !(_overcast isEqualType 0) then { _overcast = 0; };
if ((!_skyForce) && (!_settingOn || (_sunElev >= 0) || (_overcast >= 0.8))) exitWith {
    { deleteVehicle (_x select 1); } forEach _lights;
    missionNamespace setVariable [QGVAR(starLights), []];
};

private _stars = missionNamespace getVariable [QGVAR(visibleStars), []];
private _eyePos = ((call CBA_fnc_currentUnit) call EFUNC(core,getEyeState)) select 0;

// Forced limiting magnitude: publish the effective value and, when forced,
// the emitter count.  The emitter path still caps at STAR_LIGHT_MAX_MAG, so
// the faint bulk is left to the immediate-mode layer (fnc_drawFaintStars).
private _starsForce = missionNamespace getVariable [QGVAR(starsForce), 0];
if !(_starsForce isEqualType 0) then { _starsForce = 0; };
private _effectiveNelm = missionNamespace getVariable [QGVAR(limitingMagnitude), 6.5];
if (_starsForce > 0) then { _effectiveNelm = _starsForce; };
missionNamespace setVariable [QGVAR(effectiveNelm), _effectiveNelm];

// A real star sits at optical infinity; any far radius reproduces its
// direction.  These are render tunables for the operator's in-game eye.
private _starRadius = 5000;
private _flareMaxDist = 7500;
private _brightnessBase = 0.35;
private _flareSizeBase = 0.8;

// Desired light per visible star: [name, dir, sizeScale, alpha].
// The light-emitter path renders only the bright stars: the engine caps
// concurrent dynamic lights, so the faint bulk is left to a Draw3D
// primitive (not yet shipped).  STAR_LIGHT_MAX_MAG is that ceiling.
// The star brightness model publishes a 0..1 render scale; it multiplies
// each star's alpha in fnc_starMagnitude.
private _brightnessScale = missionNamespace getVariable [QGVAR(starBrightnessCoefficient), 1];
if !(_brightnessScale isEqualType 0) then { _brightnessScale = 1; };
private _desired = [];
{
    _x params ["_name", "_altDeg", "_azDeg", "_vmag"];
    if (_vmag > STAR_LIGHT_MAX_MAG) then { continue; };
    private _dir = [_altDeg, _azDeg] call FUNC(starDirection);
    private _mag = [_vmag, _brightnessScale] call FUNC(starMagnitude);
    _desired pushBack [_name, _dir, _mag select 0, _mag select 1];
} forEach _stars;

missionNamespace setVariable [QGVAR(starEmitterCount), count _desired];

{
    _x params ["_name", "_dir", "_size", "_alpha"];
    private _idx = _lights findIf { (_x select 0) == _name };
    private _light = if (_idx >= 0) then {
        (_lights select _idx) select 1
    } else {
        private _l = "#lightpoint" createVehicleLocal [0, 0, 0];
        _l setLightUseFlare true;
        _l setLightAmbient [0, 0, 0];
        _l setLightColor [1, 1, 1];
        _lights pushBack [_name, _l];
        _l
    };
    _light setPosASL (_eyePos vectorAdd (_dir vectorMultiply _starRadius));
    _light setLightBrightness (_brightnessBase * _alpha);
    _light setLightFlareSize (_flareSizeBase * _size);
    _light setLightFlareMaxDistance _flareMaxDist;
} forEach _desired;

// Drop lights whose star dropped below the horizon or past the NELM since
// the last catalog recompute (fnc_getStarCatalog re-runs every environment
// tick, so this is a rare no-op, not a second gate).
private _kept = _desired apply { _x select 0 };
{
    if (!((_x select 0) in _kept)) then { deleteVehicle (_x select 1); };
} forEach _lights;
missionNamespace setVariable [QGVAR(starLights), (_lights select { (_x select 0) in _kept })];
