#include "..\..\script_component.hpp"

/*
 * Meteor render worker, driven at 4 Hz by fnc_renderMeteors.
 *
 * On a night inside a shower's activity window, meteors streak from the
 * radiant at a rate set by fnc_meteorState (IMO ZHR reduced by radiant
 * altitude and the current limiting magnitude).  A meteor is a local light
 * emitter plus a particle trail, carried by a local "Land_Battery_F" that
 * moves away from the radiant.  The mechanism is copied from the
 * falling-star mod (star_lumina particle and light block, alias_fallingstar
 * carrier).
 *
 * The worker is client-only and cosmetic: no sound, no explosion, no ground
 * impact, no damage, no server object.  It reuses the starfield's night gate
 * (QEGVAR(core,currentSunElevation)) and the overcast gate.  Lifetime is
 * arithmetic: each tick decays the light intensity and deletes the objects
 * once diag_tickTime passes the despawn stamp.  No sleep loop.
 */

private _meteors = missionNamespace getVariable [QGVAR(meteors), []];

// ── Gates: setting, night, overcast.  Any gate-off clears the sky. ───────
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), 0];
if !(_sunElev isEqualType 0) then { _sunElev = 0; };
private _overcast = ([] call EFUNC(core,getSmoothedWeather)) select 1;
private _disabled = !(missionNamespace getVariable [QGVAR(dynamicMeteors), true]);

if (_disabled || _sunElev >= 0 || _overcast >= 0.8) exitWith {
    {
        _x params ["_carrier", "_light", "_trail"];
        deleteVehicle _carrier;
        deleteVehicle _light;
        deleteVehicle _trail;
    } forEach _meteors;
    missionNamespace setVariable [QGVAR(meteors), []];
};

// ── Decay and despawn the active meteors. ────────────────────────────────
private _now = diag_tickTime;
private _alive = [];
{
    _x params ["_carrier", "_light", "_trail", "_intensity", "_despawnAt"];
    if (_now >= _despawnAt) then {
        deleteVehicle _carrier;
        deleteVehicle _light;
        deleteVehicle _trail;
    } else {
        _intensity = (_intensity - METEOR_LIGHT_DECAY) max 0;
        _x set [3, _intensity];
        _light setLightIntensity _intensity;
        _alive pushBack _x;
    };
} forEach _meteors;
_meteors = _alive;

// ── Spawn new meteors at the expected rate. ──────────────────────────────
private _date = date;
private _lat = ([] call EFUNC(core,getWorldLocation)) select 1;
if (_lat == 0) then { _lat = 40; };
private _mLim = missionNamespace getVariable [QGVAR(limitingMagnitude), 6.5];
private _eyePos = ((call CBA_fnc_currentUnit) call EFUNC(core,getEyeState)) select 0;
private _showers = [] call FUNC(meteorShowers);
private _spawns = 0;

{
    private _state = [_date, _lat, _mLim, _x] call FUNC(meteorState);
    _state params ["_active", "_altDeg", "_azDeg", "_rate"];
    if (_active && _rate > 0) then {
        // The rate is meteors per hour; this tick lasts METEOR_TICK seconds.
        private _p = _rate * METEOR_TICK / 3600;
        if (random 1 < _p) then {
            private _dir = [_altDeg, _azDeg] call FUNC(starDirection);
            private _radius = METEOR_SPAWN_RADIUS_MIN + random (METEOR_SPAWN_RADIUS_MAX - METEOR_SPAWN_RADIUS_MIN);
            private _origin = _eyePos vectorAdd (_dir vectorMultiply _radius);
            private _jitter = 200;
            private _carrier = "Land_Battery_F" createVehicleLocal (_origin vectorAdd [((random _jitter) - (_jitter / 2)), ((random _jitter) - (_jitter / 2)), ((random _jitter) - (_jitter / 2))]);

            private _trail = "#particlesource" createVehicleLocal (getPosATL _carrier);
            _trail setParticleCircle [0, [0, 0, 0]];
            _trail setParticleRandom [3, [0.25, 0.25, 0.25], [0, 0, 0], 0, 0.25, [0, 0, 0, 0.5], 0, 0];
            _trail setParticleParams [["\A3\data_f\cl_basic", 1, 0, 1], "", "Billboard", 1, 2, [0, 0, 0], [0, 0, 0.75], 30, 10, 7.9, 0, [1.2, 4, 1], [[1, 1, 1, 1], [0.25, 0.25, 0.25, 0.5]], [0.08], 1, 0, "", "", _carrier];
            _trail setDropInterval 0.002;

            private _light = "#lightpoint" createVehicleLocal [0, 0, 0];
            _light lightAttachObject [_carrier, [0, 0, 0]];
            _light setLightIntensity METEOR_LIGHT_BRIGHTNESS;
            _light setLightAttenuation [500, 300, 3000, 0, 5, 500];
            _light setLightUseFlare true;
            _light setLightFlareSize 10;
            _light setLightFlareMaxDistance 2000;
            _light setLightAmbient [1, 0.8, 0.7];
            _light setLightColor [1, 1, 1];

            // Move away from the radiant.  The visual speed scales the
            // published V-infinity by a declared cosmetic factor (UNSOURCED:
            // chosen for the eye, not a physical value).
            private _speed = (_x select 11) * METEOR_SPEED_FACTOR;
            _carrier setVelocity (_dir vectorMultiply (-_speed));

            private _despawnAt = diag_tickTime + METEOR_LIFETIME;
            _meteors pushBack [_carrier, _light, _trail, METEOR_LIGHT_BRIGHTNESS, _despawnAt];
            _spawns = _spawns + 1;
        };
    };
} forEach _showers;

missionNamespace setVariable [QGVAR(meteors), _meteors];

// ── Windowed trace so the event reads in an .rpt. ────────────────────────
private _logAt = missionNamespace getVariable [QGVAR(meteorLogAt), -1e9];
if !(_logAt isEqualType 0) then { _logAt = -1e9; };
if (diag_tickTime >= _logAt) then {
    missionNamespace setVariable [QGVAR(meteorLogAt), diag_tickTime + 5];
    private _logMsg = format ["meteor: %1 active, %2 spawns", count _meteors, _spawns];
    AEE_LOG_DEBUG(_logMsg);
};
