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

// Disabled: clear and idle.
if (!(missionNamespace getVariable [QGVAR(dynamicStars), true])) exitWith {
    { deleteVehicle (_x select 1); } forEach _lights;
    missionNamespace setVariable [QGVAR(starLights), []];
};

// Night gate: the NELM chain clamps at 2.0, so Sirius and Canopus would
// otherwise draw in daylight; stars appear only once the sun is down.
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 0];
if !(_sunElev isEqualType 0) then { _sunElev = 0; };
if (_sunElev >= 0) exitWith {
    { deleteVehicle (_x select 1); } forEach _lights;
    missionNamespace setVariable [QGVAR(starLights), []];
};

// Solid overcast occludes every star regardless of integrated sky light.
// The declared threshold is 8/10 cloud.  The NELM chain (fnc_calculate
// LimitingMagnitude) already folds cloud into the limiting magnitude, so
// the catalog drops most stars; this hard gate handles the point-occlusion
// case the integrated sky model cannot (issue #122 cloud gate).
private _overcast = ([] call EFUNC(core,getSmoothedWeather)) select 1;
if (_overcast >= 0.8) exitWith {
    { deleteVehicle (_x select 1); } forEach _lights;
    missionNamespace setVariable [QGVAR(starLights), []];
};

private _stars = missionNamespace getVariable [QGVAR(visibleStars), []];
private _eyePos = ((call CBA_fnc_currentUnit) call EFUNC(core,getEyeState)) select 0;

// A real star sits at optical infinity; any far radius reproduces its
// direction.  These are render tunables for the operator's in-game eye.
private _starRadius = 5000;
private _flareMaxDist = 7500;
private _brightnessBase = 0.35;
private _flareSizeBase = 0.8;

// Desired light per visible star: [name, dir, sizeScale, alpha].
private _desired = [];
{
    _x params ["_name", "_altDeg", "_azDeg", "_vmag"];
    private _dir = [_altDeg, _azDeg] call FUNC(starDirection);
    private _mag = [_vmag] call FUNC(starMagnitude);
    _desired pushBack [_name, _dir, _mag select 0, _mag select 1];
} forEach _stars;

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

// One summary line per 5 s window through AEE_LOG_DEBUG (the module trace
// switch), so the field can be read in an .rpt without a per-tick cost.
private _logAt = missionNamespace getVariable [QGVAR(starLogAt), -1e9];
if !(_logAt isEqualType 0) then { _logAt = -1e9; };
if (diag_tickTime >= _logAt) then {
    missionNamespace setVariable [QGVAR(starLogAt), diag_tickTime + 5];
    private _lightCount = count (missionNamespace getVariable [QGVAR(starLights), []]);
    private _logMsg = format ["starfield: %1 stars visible, %2 light emitters", count _stars, _lightCount];
    AEE_LOG_DEBUG(_logMsg);
};
