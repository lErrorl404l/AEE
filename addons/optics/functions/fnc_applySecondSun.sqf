#include "..\script_component.hpp"
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

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith { 0 };

private _sun = missionNamespace getVariable [QGVAR(tiSecondSun), objNull];

// ─── EXIT: destroy the lightpoint ────────────────────────────────────────
if (_mode == "EXIT") then {
    if !(isNull _sun) then {
        deleteVehicle _sun;
        missionNamespace setVariable [QGVAR(tiSecondSun), objNull];
    };
    0
};

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

// ─── TICK: brightness = physics solar radiation ──────────────────────────
// 0 = no sun (night) -> no sun term, buildings cold.
// 1 = full sun       -> full engine sun-heating of the TI red channel.
// Overcast already folded into currentSolarRadiation.
private _radiation = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_radiation isEqualType 0) then { _radiation = 0; };
_radiation = _radiation max 0 min 1;

// Attach to the camera so the light direction follows the view (the TI
// sun term is directional).  Constant-brightness light; the engine
// multiplies it through the thermal pass.
_sun attachTo [_player, [0, 0, 0], "head"];
_sun setLightBrightness _radiation;
_sun setLightAmbient [0.5, 0.5, 0.5];
_sun setLightAttenuation [1e10, 1, 0, 0];

// Debug: log the actual radiation the engine's sun term sees, with the
// date/time inputs, so an inverted day/night reading is traceable.
if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
    diag_log text format ["[AEE] SecondSun: rad=%1 dayTime=%2 date=%3",
        _radiation, dayTime, date];
};

_radiation
