#include "..\script_component.hpp"
/*
 * Drives the ENGINE's thermal display from AEE's physics model.
 *
 * The engine renders thermal natively from per-object heat state, then maps
 * the result through a display window:  OutputRangeStart + thermalValue *
 * OutputRangeWidth (default 0.1 + t * 0.8 -> range 0.1..0.9).  The default
 * window is compressed, so the engine's per-object thermal differences all
 * clip to the same brightness — the "everything is white" report.
 *
 * Two levers, both scriptable since 2.10 (SPOTREP #00106):
 *
 *  1. setTIParameter  - the DISPLAY GAIN.  Widening OutputRangeWidth and
 *     lowering OutputRangeStart spreads the engine's thermal values across
 *     the full screen range, exactly like a real FLIR's AGC/level controls
 *     (or dark-adapted eyes: the window defines what is visible).  Driven
 *     from our contrast model: clear scene -> full width, crossover/rain
 *     -> narrowed (the scene's meaningful spread is smaller).
 *
 *  2. setVehicleTIPars - the per-vehicle INPUT heat state 0..1, read from
 *     our object-temperature model (engineRunTime -> engine heat, speed ->
 *     wheel heat).  The engine then renders running vs parked vehicles
 *     differently, which its baked static heatmaps cannot.
 *
 * The engine still owns the render pass and the palette.  We only supply
 * the input heat state and the display window.  A custom renderer is not
 * possible (the thermal pass is not interceptable), so this is the maximum
 * physical control the engine exposes.
 *
 * Reapplied every tick while thermal is active; the settings are not saved
 * in savegames and must be reapplied after loading (BIKI).
 */
params [""];

if (!hasInterface) exitWith { 0 };

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── 1. Display gain (AGC) from the SCENE temperature range ───────────────
// A real FLIR auto-gain scales the display to what is actually in view:
// the coldest part maps to dark, the hottest part maps near full bright,
// and everything in between spreads across the screen.  This is driven by
// the ENVIRONMENT — a cold night scene with only a warm engine reads with
// the engine bright and everything else dark; a hot day with sun-warmed
// vehicles reads everything brighter.  No static values.
//
// We compute the scene's hottest heat fraction from the vehicles we drive
// (section 2 runs first in the real flow? No — section 2 runs after; so
// gather the max heat here in the same pass).  To keep this simple and
// stateless, read the hottest heat fraction we LAST applied from
// missionNamespace (updated by section 2), falling back to a sane 0.5
// (a half-warm scene) on the first tick.
private _sceneMaxHeat = missionNamespace getVariable [QGVAR(tiSceneMaxHeat), 0.5];
if !(_sceneMaxHeat isEqualType 0) then { _sceneMaxHeat = 0.5; };
_sceneMaxHeat = _sceneMaxHeat max 0.2 min 1;

// Output window: start 0 (cold = dark, physically right for a cool night)
// and width so the scene's hottest object maps near full bright without
// clipping.  width = 0.9 / maxHeat, capped at 1.0.  When nothing is hot
// (all vehicles ambient), maxHeat ~ 0 -> floor keeps the window wide
// enough to still resolve small differences (the NETD floor).
private _outStart = 0.0;
private _outWidth = (0.9 / _sceneMaxHeat) min 1.0 max 0.35;

// Only call when the window actually changes: setTIParameter forces a
// histogram update, and spamming it every tick is wasted work and can
// cause visible flicker.  Store the last-applied window in missionNamespace.
private _lastStart = missionNamespace getVariable [QGVAR(tiOutStart), -1];
private _lastWidth = missionNamespace getVariable [QGVAR(tiOutWidth), -1];
if (abs (_outStart - _lastStart) > 0.01 || abs (_outWidth - _lastWidth) > 0.01) then {
    setTIParameter ["OutputRangeStart", _outStart];
    setTIParameter ["OutputRangeWidth", _outWidth];
    missionNamespace setVariable [QGVAR(tiOutStart), _outStart];
    missionNamespace setVariable [QGVAR(tiOutWidth), _outWidth];
};

// ─── 2. Per-vehicle heat state from our physics model ─────────────────────
// setVehicleTIPars is a LOCAL command (no _Global variant exists; it is
// registered client-side in the engine).  That is correct for our design:
// the thermal image is rendered per-client, each client runs this PFH, and
// each client's own thermal view reads the heat state it set locally.
// The physics inputs (weather, engine state) are identical across clients,
// so every client computes the same heat values for the same vehicles.
//
// DESIGN: drive the heat state from our PHYSICS TEMPERATURE for ALL
// vehicles, engine on or off.  The vanilla engine's own model (afMax/
// htMax static timers) is unrealistic — that is the exact thing mods
// exist to replace.  Our fnc_calculateObjectTemperature already computes
// the equilibrium surface temperature from EVERYTHING:
//   air temp + solar absorption (0.7 x 15 C) + engine heat (40 C, tau
//   300 s) + exhaust share (200 C, tau 60 s) + wind convective cooling
//   + thermal inertia (tau 120 s) + emissivity
// That IS the heat fraction, mapped to the engine's 0..1 scale:
//   0 = ambient, 1 = ambient + 50 C (a hard-running engine on a hot
//   day).  The engine renders THIS, so sun, ambient, wind, and engine
//   state all move the image — no static timers.
//
// Read QGVAR(thermalState): key str object, value [temp, engineRunTime,
// now, acclimatisation, obj].  temp is the equilibrium surface temp C.
private _thermalState = missionNamespace getVariable [QGVAR(thermalState), createHashMap];
private _vehicles = _player nearEntities [["Car", "Tank", "Motorcycle", "Helicopter", "Plane", "Ship"], 150];
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };

{
    if (isNull _x || !alive _x) then { continue; };
    private _objKey = str _x;
    private _state = _thermalState getOrDefault [_objKey, []];

    // Physics surface temperature (C).  Falls back to ambient + solar on
    // a fresh spawn (no state yet) so the vehicle is not instantly cold.
    private _surfaceTemp = _airTemp;
    if (count _state >= 1) then {
        private _t = _state select 0;
        if (_t isEqualType 0) then { _surfaceTemp = _t; };
    };
    // Heat fraction on the engine's 0..1 scale: ambient = 0, +50 C = 1.
    // A parked vehicle at ambient reads 0 (dark); a running engine at
    // +40 C reads 0.8 (bright).  Clamped to the engine's range.
    private _engineHeat = ((_surfaceTemp - _airTemp) / 50) min 1 max 0;

    // Wheel heat: friction from motion.  Real tyres warm with speed and
    // driving time; simple model: speed fraction of a threshold.
    private _speed = abs speed _x;
    private _wheelHeat = (_speed / 30) min 1;

    // Weapon heat: skip (barrel heat is a weapon-state system we do not
    // model per-shot yet; keep the engine's own handling).
    //
    // Change guard: setVehicleTIPars is a real engine call (network +
    // heat-state update).  Only invoke it when a value moved materially;
    // otherwise a convoy of parked vehicles would spam the call every
    // 0.1 s tick.  Store the last-applied triple per vehicle in
    // missionNamespace so it survives tick-to-tick.
    private _lastTriple = missionNamespace getVariable [format [QGVAR(tiVeh_%1), _objKey], [-1, -1, -1]];
    if (_lastTriple isEqualType []) then {
        if (count _lastTriple < 3) then { _lastTriple = [-1, -1, -1]; };
    } else {
        _lastTriple = [-1, -1, -1];
    };
    private _changed = false;
    if (abs ((_lastTriple select 0) - _engineHeat) > 0.02) then { _changed = true; };
    if (abs ((_lastTriple select 1) - _wheelHeat) > 0.02) then { _changed = true; };
    if (_changed) then {
        _x setVehicleTIPars [_engineHeat, _wheelHeat, 0];
        missionNamespace setVariable [format [QGVAR(tiVeh_%1), _objKey], [_engineHeat, _wheelHeat, 0]];
    };

    // Debug: one line per vehicle, throttled — confirms the engine is
    // being driven from physics.
    if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
        diag_log text format ["[AEE] TI drive: %1 T=%2 air=%3 heat=%4 wheels=%5 speed=%6",
            typeOf _x, round (_surfaceTemp * 10) / 10, round (_airTemp * 10) / 10,
            _engineHeat, _wheelHeat, round _speed];
    };

    // Track the scene's hottest heat fraction for the AGC window (section
    // 1 reads it next tick).  This makes the display gain follow the
    // environment: a scene with a running engine brightens against cold
    // ambient; an empty cold scene stays dark.
    if (_engineHeat > (missionNamespace getVariable [QGVAR(tiSceneMaxHeat), 0.5])) then {
        missionNamespace setVariable [QGVAR(tiSceneMaxHeat), _engineHeat];
    };
} forEach _vehicles;

// Decay the scene max toward ambient over ~30 s so the gain relaxes when
// the hot source leaves view (a FLIR does not hold max gain forever).
private _sceneMax = missionNamespace getVariable [QGVAR(tiSceneMaxHeat), 0.5];
if !(_sceneMax isEqualType 0) then { _sceneMax = 0.5; };
_sceneMax = _sceneMax - 0.2 * (diag_deltaTime / 30);
missionNamespace setVariable [QGVAR(tiSceneMaxHeat), _sceneMax max 0.05];

count _vehicles
