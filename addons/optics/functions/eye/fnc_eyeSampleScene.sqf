#include "..\..\script_component.hpp"

/*
Sample the scene luminance for the eye model.

Three sources are combined:

  - The core illuminance model publishes aee_core_ambientLux and
    aee_core_dynamicLux (lamps, fires, flares, vehicle lights and the
    weapon light).
  - getLightingAt returns the engine's local dynamic light at the player.
    It folds local light into one value, but it has no documented unit and
    it is gated by the local player's night-vision state, so it enters only
    through a tunable scale (UNSOURCED).
  - apertureParams exposes the engine's own estimated luminance and
    blinding term, read for diagnostics and through an off-by-default
    blinding scale (UNSOURCED).

The sky fraction scales the ambient term only. A local light is not scaled
by the sky: a torch lights the scene in a closed room.

Arguments: none.

Returns:
  Array [sceneLux, localLux, skyFraction, engineLuminance, blinding], or an
  empty array when the sampler cannot run (no interface, no unit).
*/

if (!hasInterface) exitWith { [] };

private _player = call CBA_fnc_currentUnit;
if (isNull _player) exitWith { [] };

private _physAmbient = missionNamespace getVariable [QEGVAR(core,ambientLux), 0];
if !(_physAmbient isEqualType 0) then { _physAmbient = 0; };
private _coreLocal = missionNamespace getVariable [QEGVAR(core,dynamicLux), 0];
if !(_coreLocal isEqualType 0) then { _coreLocal = 0; };

private _engAmbient = 0;
private _engLocal = 0;
private _lighting = getLightingAt _player;
if ((_lighting isEqualType []) && {(count _lighting) >= 4}) then {
    _engAmbient = _lighting select 1;
    _engLocal = _lighting select 3;
    if !(_engAmbient isEqualType 0) then { _engAmbient = 0; };
    if !(_engLocal isEqualType 0) then { _engLocal = 0; };
};

private _engineLum = 0;
private _blinding = 0;
private _params = apertureParams;
if ((_params isEqualType []) && {(count _params) >= 10}) then {
    _engineLum = _params select 3;
    _blinding = _params select 9;
    if !(_engineLum isEqualType 0) then { _engineLum = 0; };
    if !(_blinding isEqualType 0) then { _blinding = 0; };
};

private _ambient = _physAmbient max (_engAmbient * GVAR(eyeAmbientLuxScale));
private _local = _coreLocal max ((_engLocal * GVAR(eyeLocalLuxScale)) + (_blinding * GVAR(eyeBlindingLuxScale)));

// Sky directions: straight up plus four at 45 degrees, one per compass
// quadrant. The 200 m range is UNSOURCED; it only has to clear the geometry
// that can stand between the eye and open sky.
private _range = 200;
private _dirs = [
    [0, 0, 1],
    [0.7071, 0.7071, 0.7071],
    [-0.7071, 0.7071, 0.7071],
    [-0.7071, -0.7071, 0.7071],
    [0.7071, -0.7071, 0.7071]
];
private _ignore = [objNull, objNull];
private _vehicle = vehicle _player;
if (_vehicle != _player) then { _ignore = [_vehicle, objNull]; };
private _sky = [[getPosASL _player, _dirs, _ignore, _range] call FUNC(eyeSkyCast)] call FUNC(eyeSkyFraction);

// Publish every raw input for calibration.
missionNamespace setVariable [QGVAR(eyeRawAmbient), _ambient];
missionNamespace setVariable [QGVAR(eyeRawLocal), _local];
missionNamespace setVariable [QGVAR(eyeRawCoreLocal), _coreLocal];
missionNamespace setVariable [QGVAR(eyeRawEngineAmbient), _engAmbient];
missionNamespace setVariable [QGVAR(eyeRawEngineLocal), _engLocal];
missionNamespace setVariable [QGVAR(eyeRawEngineLum), _engineLum];
missionNamespace setVariable [QGVAR(eyeRawBlinding), _blinding];
missionNamespace setVariable [QGVAR(eyeRawSky), _sky];

[[_ambient, _local, _sky] call FUNC(eyeSceneLux), _local, _sky, _engineLum, _blinding]
