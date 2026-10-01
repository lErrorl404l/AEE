#include "..\..\script_component.hpp"
/*
 * Drives the engine's SUN term for thermal rendering from AEE's physics.
 *
 * The engine renders buildings/terrain from baked TI textures.  The TI
 * red channel encodes "how much an object heats up from the sun", and the
 * engine applies a SUN-LIGHT contribution to that channel during the
 * thermal pass.  A3TI controls this with a static "second sun" lightpoint
 * (brightness 200, always on) — which is why their buildings always glow
 * white regardless of actual sunlight.
 *
 * We do the PHYSICS-CORRECT version: the fake sun's brightness follows
 * our real solar radiation model (fnc_calculateSolarRadiation, 0..1 from
 * day-of-year, hour angle, latitude, overcast transmission).
 *
 *   Day (radiation 1)  -> fake sun full: the engine sun-heats buildings,
 *                         matching real physics (surfaces ARE warm).
 *   Night (radiation 0) -> fake sun OFF: no sun term, so buildings render
 *                         cold — the inverse of the static-white default.
 *   Overcast             -> attenuated, matching the radiation model.
 *
 * This is a LIGHTPOINT attached to the player's camera direction (the
 * engine keys the TI sun term to directional light), local, hidden,
 * non-simulated, daylight-enabled.  It affects ONLY the engine's thermal
 * sun term — the normal visible scene is untouched because the light is
 * hidden and its brightness is zero when it would matter for visible
 * rendering (the visible sun is the engine's own).
 *
 * Buildings/terrain cannot be driven per-object (no runtime command), so
 * this is the only lever for them: the SUN contribution.  Per-object
 * vehicles are driven separately by fnc_applyEngineThermal.
 */
params ["_mode"];   // "ENTER" | "TICK" | "EXIT"

if (!hasInterface) exitWith { 0 };

// The handle read and the EXIT branch sit ABOVE the player guard on purpose.
// The sensor teardown calls this on death, and call CBA_fnc_currentUnit still
// returns the dead unit then, so a guard here would skip the destroy and
// leave the lightpoint alive.  Same shape as the setAperture restore in
// fnc_teardownSensors.
private _sun = missionNamespace getVariable [QGVAR(tiSecondSun), objNull];

// ─── EXIT: destroy the lightpoint ────────────────────────────────────────
// Destroy, then STOP.  Without exitWith the run falls through into the
// ENTER and tick paths below and recreates the lightpoint it just deleted.
if (_mode == "EXIT") exitWith {
    if !(isNull _sun) then {
        deleteVehicle _sun;
        missionNamespace setVariable [QGVAR(tiSecondSun), objNull];
    }
};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };

// ─── ENTER: create the lightpoint once ────────────────────────────────────
if (_mode == "ENTER") then {
    if (isNull _sun) then {
        _sun = "#lightpoint" createVehicleLocal [0, 0, 0];
        _sun hideObject true;
        _sun enableSimulation false;
        _sun setLightDayLight true;         // affects the TI day-light term
        missionNamespace setVariable [QGVAR(tiSecondSun), _sun];
    };
};

// ─── TICK: brightness = physics radiation, scaled to engine range ─────────
// A3TI (the reference for this mechanism) uses STATIC brightness 13 in all
// TI modes, which SATURATES the scene to flat white - it masks per-object
// heat (in-game proven: the whole image darkens when this drops, and
// vehicles lose all contrast at 13).  A3TI wanted everything warm (its
// fusion look); we want CONTRAST.  The engine's thermal sun term expects
// lightpoint brightness in that order of magnitude; a value in 0..1 is
// ~30x below the visible threshold, so the sun term does nothing and
// buildings fall back to their baked alive-heat.  We keep the
// PHYSICS-CORRECT day/night variation but scale into a NON-SATURATING
// range: brightness = radiation * 6, so full sun = 6 (half A3TI - enough
// to heat terrain/buildings, low enough that vehicles keep their
// setVehicleTIPars contrast) and night = 0 (no sun term).
private _radiation = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_radiation isEqualType 0) then { _radiation = 0; };
_radiation = _radiation max 0 min 1;
// Second sun (TI sun term, issue #204): the engine's TI mode renders
// the terrain's heat from the SUN term - day ground is warm, night
// ground is cold.  The second sun must TRACK the solar radiation so the
// terrain darkens at night: a constant brightness 13 at midnight made
// the ground glow white-hot (the 'cold tyres on white ground' report -
// the vehicles were correctly dark, the terrain was over-heated).
// Peak 13 is an engine brightness-unit calibration (A3TI
// DEFAULT_SECONDSUN_BRIGHTNESS); no published source exists for that unit,
// so it is labelled unauthenticated rather than presented as physics. The
// physical content is the radiation tracking below. No floor: at night
// radiation is 0, so the fake sun is genuinely OFF. Attenuation is engine units.
private _lightBrightness = 13 * _radiation;

// The TI sun term is DIRECTIONAL (issue #204): a real scene heats the
// faces of objects facing the sun - morning thermals warm the east
// faces, afternoon the west.  The second sun must follow the REAL sun's
// bearing, not sit at the camera.  Position the lightpoint 150 m along
// the sun's azimuth (from the core solar position model) so the light
// direction from the scene matches the sun.  At night the moon bearing
// drives the (dim) reflected term.
private _azimuth = missionNamespace getVariable [QEGVAR(core,currentSunAzimuth), 180];
if !(_azimuth isEqualType 0) then { _azimuth = 180; };
if (_radiation <= 0.02) then {
    private _moonAz = missionNamespace getVariable [QEGVAR(core,currentMoonAzimuth), _azimuth];
    if (_moonAz isEqualType 0) then { _azimuth = _moonAz; };
};
// Engine work here is the expensive part, not the arithmetic.  Every
// setPosASL and every setLight* on a live dynamic light makes the engine
// re-evaluate scene lighting for every lit object, so this ran 4 engine calls
// 10 times a second.  Two of the four are CONSTANTS and are now written once
// at creation.  The other two are written only when the physics value has
// actually moved, and the sun's bearing changes over hours, not per frame.
_sun setLightAmbient [0.5, 0.5, 0.5];
_sun setLightAttenuation [10e10, 150, 4.3e-5, 4.3e-5];

private _sunPos = AGLToASL ((_player getRelPos [150, _azimuth]) vectorAdd [0, 0, 20]);
private _lastPos = missionNamespace getVariable [QGVAR(tiSecondSunPos), [0, 0, 0]];
if ((_sunPos distance _lastPos) > 1) then {
    _sun setPosASL _sunPos;
    missionNamespace setVariable [QGVAR(tiSecondSunPos), _sunPos];
};

private _lastBright = missionNamespace getVariable [QGVAR(tiSecondSunBright), -1];
if (abs (_lightBrightness - _lastBright) > 0.001) then {
    _sun setLightBrightness _lightBrightness;
    missionNamespace setVariable [QGVAR(tiSecondSunBright), _lightBrightness];
};

// Trace the sun term every 5 s so day/night behaviour is verifiable in
// the RPT without the nvgDebug flag (issue #204: 'second sun on at night'
// report).  Throttled to one line per 5 s.
// Gated on the module flag. This trace was ungated, so it wrote to the RPT on
// every install whether or not any diagnostic was switched on.
private _lastTrace = missionNamespace getVariable [QGVAR(sunTraceTime), -1];
if (missionNamespace getVariable [QGVAR(thermalDebug), false]
    && {diag_tickTime - _lastTrace > 5}) then {
    missionNamespace setVariable [QGVAR(sunTraceTime), diag_tickTime];
    diag_log format ["[AEE] SecondSun: rad=%1 bright=%2 dayTime=%3",
        _radiation, _lightBrightness, dayTime];
};

// Debug: log the radiation and the scaled brightness the engine's sun term
// sees, with dayTime, so day/night behaviour is traceable.
if (missionNamespace getVariable [QGVAR(thermalDebug), false]) then {
    diag_log text format ["[AEE] SecondSun: rad=%1 brightness=%2 dayTime=%3 date=%4",
        _radiation, _lightBrightness, dayTime, date];
};

_radiation
