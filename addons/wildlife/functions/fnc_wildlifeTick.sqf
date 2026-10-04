#include "..\script_component.hpp"

/*
The single wildlife client tick.

Builds the local disturbance field from the local unit's movement and the
nearby units, samples it at the listener, selects the ambient bed and the
silence, applies the force hooks and plays the bed.  The whole layer is
client-local cosmetic ecology.  A machine with no player computes the state
and then stops before any sound or object.

Arguments:
  0: Array - an optional anchor position, empty means the local unit
  1: Bool  - dry run, compute the state and skip every sound and object

Returns:
  Array - [bedKey, gain, disturbance, spook, spookRange]
*/

params [
    ["_anchor", [], [[]]],
    ["_dryRun", false, [false]]
];

private _unit = objNull;
if (hasInterface) then {
    _unit = call CBA_fnc_currentUnit;
};
private _hasUnit = !(isNull _unit);

private _position = _anchor;
if ((count _position) < 2) then {
    if (_hasUnit) then {
        _position = getPos _unit;
    } else {
        _position = [0, 0, 0];
    };
};

// Guarded reads: a nil read that falls through to a default is the #154 bug.
private _biome = missionNamespace getVariable [QEGVAR(environmental,localBiome), ""];
if !(_biome isEqualType "") then { _biome = ""; };

private _forceBiome = missionNamespace getVariable ["aee_wildlife_forceBiome", ""];
if !(_forceBiome isEqualType "") then { _forceBiome = ""; };
if (_forceBiome != "") then { _biome = _forceBiome; };

private _isNight = sunOrMoon < 0.5;
private _forceNight = missionNamespace getVariable ["aee_wildlife_forceNight", nil];
if (_forceNight isEqualType false) then { _isNight = _forceNight; };

private _nearWater = 0;
if (_hasUnit) then {
    private _coast = [_position, 200] call EFUNC(environmental,getCoastDistance);
    if (_coast isEqualType 0) then {
        _nearWater = 1 - ((_coast / 200) min 1);
    };
};

private _windVector = wind;
private _wind = (((_windVector select 0) ^ 2) + ((_windVector select 1) ^ 2)) ^ 0.5;

private _field = missionNamespace getVariable [QEGVAR(ai,disturbance), []];
if !(_field isEqualType []) then { _field = []; };

private _now = CBA_missionTime;
private _key = [_position] call EFUNC(ai,disturbanceKey);
private _disturbance = [_field, _key, _now, 45] call EFUNC(ai,disturbanceSample);

// Raise the field from the listener's own movement.  A quiet walk leaves no
// trace.  This runs only with a live local unit and only outside dry run.
if (_hasUnit) then {
    if (!_dryRun) then {
        private _speed = speed _unit;
        if (_speed > 1.5) then {
            private _magnitude = ((_speed / 8) max 0) min 1;
            _field = [_field, _key, _magnitude, _now] call EFUNC(ai,disturbanceApply);
            missionNamespace setVariable [QEGVAR(ai,disturbance), _field];
        };
    };
};

private _manifest = missionNamespace getVariable [GVAR(manifest), []];
if !(_manifest isEqualType []) then { _manifest = []; };

private _bed = [_biome, _isNight, _nearWater, _wind, _disturbance, _manifest] call FUNC(soundBedForContext);
private _bedKey = _bed select 0;
private _bedGain = _bed select 1;

private _decay = missionNamespace getVariable [QGVAR(silenceDecay), 0.05];
if !(_decay isEqualType 0) then { _decay = 0.05; };

private _silence = [_disturbance, _decay] call FUNC(disturbanceSilence);
private _forceSilence = missionNamespace getVariable ["aee_wildlife_forceSilence", -1];
if !(_forceSilence isEqualType 0) then { _forceSilence = -1; };
if (_forceSilence >= 0) then { _silence = ((_forceSilence max 0) min 1); };

private _gain = ((_bedGain * _silence) max 0) min 1;

private _spook = false;
private _spookPosition = _position;
private _forceSpook = missionNamespace getVariable ["aee_wildlife_forceSpook", []];
if (_forceSpook isEqualType []) then {
    if ((count _forceSpook) >= 2) then {
        _spook = true;
        _spookPosition = _forceSpook;
    };
} else {
    if (_disturbance > 0.6) then { _spook = true; };
};

private _spookRange = 0;
if (_spook) then {
    private _sensitivity = missionNamespace getVariable [QGVAR(spookSensitivity), 1];
    if !(_sensitivity isEqualType 0) then { _sensitivity = 1; };
    _spookRange = [_disturbance, _sensitivity, 20] call FUNC(spookRange);
};

private _state = [_bedKey, _gain, _disturbance, _spook, _spookRange];

if (_dryRun) exitWith { _state };
if (!_hasUnit) exitWith { _state };

private _enabled = missionNamespace getVariable [QGVAR(enabled), true];
if !(_enabled isEqualType true) then { _enabled = true; };
if (!_enabled) exitWith { _state };

private _ambient = missionNamespace getVariable [QGVAR(ambientEnabled), true];
if !(_ambient isEqualType true) then { _ambient = true; };

if (_spook) then {
    [_spookPosition, 0.9] call FUNC(spookWave);
};

if (_ambient) then {
    if (_gain > 0.01) then {
        private _source = "";
        for "_i" from 0 to ((count _manifest) - 1) do {
            private _row = _manifest select _i;
            if ((_row select 0) == _bedKey) then {
                if (_source == "") then { _source = _row select 1; };
            };
        };
        if (_source != "") then {
            [_source, _position, _gain] call FUNC(playAmbientBed);
        };
    };
};

private _logMsg = format ["bed %1 gain %2 disturbance %3 spook %4", _bedKey, _gain, _disturbance, _spook];
AEE_LOG_DEBUG(_logMsg);

_state
