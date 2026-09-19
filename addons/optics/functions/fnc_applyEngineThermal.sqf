#include "..\script_component.hpp"
/*
 * Drives the ENGINE's thermal display from AEE's physics model
 * (issue #124 migration).
 *
 * The per-selection substrate (applySelectionThermal, driven for
 * vehicles and buildings by applyBuildingThermal) now paints each
 * selection's texture with the FLIR white-hot procedural colour - the
 * physics surface temperature, per selection.  That supersedes the old
 * setVehicleTIPars native heat-state driving (the engine's baked
 * renderer, which could not do per-selection gradients).
 *
 * What remains here is the SENSOR layer: the display gain window
 * (setTIParameter OutputRangeStart/Width).  The engine renders thermal
 * natively from per-object heat state, then maps the result through a
 * display window:  OutputRangeStart + thermalValue * OutputRangeWidth
 * (default 0.1 + t * 0.8 -> range 0.1..0.9).  The default window is
 * compressed, so per-object thermal differences clip to the same
 * brightness - the "everything is white" report.
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
 * The engine still owns the render pass and the palette.  We only supply
 * the display window.  A custom renderer is not possible (the thermal
 * pass is not interceptable), so this is the maximum physical control
 * the engine exposes for the display, on top of the per-selection
 * procedural textures.
 *
 * Reapplied every tick while thermal is active; the settings are not saved
 * in savegames and must be reapplied after loading (BIKI).
 */
params [""];

if (!hasInterface) exitWith { 0 };

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── Display window: faithful pass-through + stable blowout guard ──────────
// ENGINE CONSTRAINT (verified): the window maps
//     output = OutputRangeStart + thermalValue * OutputRangeWidth
// with width > 0 && width < 1 and start >= 0.  It can only COMPRESS and
// OFFSET - it CANNOT stretch a narrow band to full range (that would need
// width > 1 or start < 0, both rejected by the engine).  So a true
// contrast-boosting AGC is IMPOSSIBLE here; the engine's own thermalValue
// is already the normalized scene mapping, and start=0/width=1 passes it
// through faithfully (the maximum contrast the engine allows).
//
// What the window CAN usefully do is BLOWOUT PREVENTION: when a very hot
// object (a running engine at full heat) would saturate the top of the
// range, narrow the width so it maps to ~0.9 and the rest of the scene
// keeps its relative contrast.  When nothing is near saturation, width
// stays 1.0 (no change).
//
// STABILITY (the old AGC's fatal flaw): an auto-window that re-maps every
// frame reads as a "flashlight / exposure keeps adjusting" and makes
// hot-vs-cold comparison impossible.  Two guards fix that:
//   - FREEZE while panning: if the gaze is moving fast, hold the window.
//     A real FLIR locks its AGC during a sweep and re-evaluates when the
//     view settles.
//   - EASE when settled: a slow EMA (~1.5 s), not a per-frame jump.
// start is ALWAYS 0 - we never lift the black level (the "flashlight in
// the face" the user saw came from start=0.5, never from width).
private _eyeState = [_player] call FUNC(getEyeState);
private _fwd = _eyeState select 1;

// Gaze angular velocity: angle between this frame's forward and the last.
private _prevFwd = missionNamespace getVariable [QGVAR(agcPrevFwd), _fwd];
if !(_prevFwd isEqualType [] && {count _prevFwd == 3}) then { _prevFwd = _fwd; };
private _cosA = (_prevFwd vectorDotProduct _fwd) max -1 min 1;
private _angVel = (acos _cosA) / (diag_deltaTime max 0.001);   // rad/s
missionNamespace setVariable [QGVAR(agcPrevFwd), _fwd];

// Freeze threshold: ~25 deg/s (0.44 rad/s).  Below = settled, adapt.
// Above = sweeping, hold the window steady.
private _settled = _angVel < 0.44;

// Blowout guard: narrow only when the scene's hottest object would clip.
// _sceneMaxHeat is the max physics temperature fraction from the thermal
// state (set by the per-selection substrate, read below); 0.05 floor for
// an all-cold scene.
private _sceneMaxHeat = missionNamespace getVariable [QGVAR(tiSceneMaxHeat), 0.5];
if !(_sceneMaxHeat isEqualType 0) then { _sceneMaxHeat = 0.5; };
private _outStart = 0.0;
private _targetWidth = if (_sceneMaxHeat > 0.9) then {
    (0.9 / _sceneMaxHeat) min 1.0 max 0.35
} else {
    1.0
};

// Applied width: hold while panning, ease toward target when settled.
private _outWidth = missionNamespace getVariable [QGVAR(tiOutWidth), _targetWidth];
if !(_outWidth isEqualType 0 && _outWidth > 0) then { _outWidth = _targetWidth; };
if (_settled && diag_deltaTime > 0) then {
    private _a = diag_deltaTime / (diag_deltaTime + 1.5);
    _outWidth = _outWidth + (_targetWidth - _outWidth) * _a;
};
missionNamespace setVariable [QGVAR(tiOutWidth), _outWidth];

// Apply only when the value changed materially (setTIParameter forces a
// histogram update; no need to spam it).
private _lastW = missionNamespace getVariable [QGVAR(tiAppliedWidth), -1];
private _lastS = missionNamespace getVariable [QGVAR(tiAppliedStart), -1];
if (abs (_outWidth - _lastW) > 0.01 || abs (_outStart - _lastS) > 0.01) then {
    setTIParameter ["OutputRangeStart", _outStart];
    setTIParameter ["OutputRangeWidth", _outWidth];
    missionNamespace setVariable [QGVAR(tiAppliedWidth), _outWidth];
    missionNamespace setVariable [QGVAR(tiAppliedStart), _outStart];
};

// ─── Ambient state (declared here: used by the per-vehicle heat pass
// below AND the scene-max pass after it) ───────────────────────────────────
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };

// ─── Per-vehicle heat state: physics -> engine thermal (issue #196) ───────
// The engine renders a vehicle's thermal image from its HEAT STATE
// (setVehicleTIPars [engine, wheels, weapon], each 0..1 on the engine's
// scale: ambient = 0, ambient + 50 C = 1).  The old surface path
// abandoned this lever in the #124 migration; the result was that every
// vehicle rendered from the engine's BAKED thermal state - white-hot at
// midnight regardless of actual temperature.  Driving the state from
// AEE's two-node per-selection temperatures makes the physics visible in
// EVERY thermal device (nods, turrets, drones, vehicle optics): a cold
// parked truck reads dark, a hot engine bay reads bright, and the whole
// vehicle responds to sun, wind and ambient through the same physics as
// the per-selection solve.
//
// Engine/wheels/weapon temperatures come from the two-node state map
// (thermal fnc_applySelectionThermal, keyed "obj|selection").  Selections
// matching engine/motor drive the engine channel; wheel/tyre drive the
// wheels channel; the vehicle weapon (turret) drives the weapon channel.
// A vehicle with no matches (no engine selection in the map) keeps the
// default 0 - the engine's own ambient baseline.
private _selTemps = missionNamespace getVariable [QEGVAR(thermal,selTemperature), createHashMap];
private _engineMax = 0.0;
private _wheelMax = 0.0;
private _weaponMax = 0.0;
{
    if (isNull _x || !alive _x) then { continue; };
    if !(_x isKindOf "AllVehicles") then { continue; };
    private _objKey = str _x;
    private _engineC = -1e10;
    private _wheelC = -1e10;
    private _weaponC = -1e10;
    {
        _x params ["_sel", "_t"];
        if !(_t isEqualType 0 && {finite _t}) then { continue; };
        private _ls = toLower _sel;
        if (_ls find "engine" >= 0 || {_ls find "motor" >= 0}) then {
            if (_t > _engineC) then { _engineC = _t; };
        };
        if (_ls find "wheel" >= 0 || {_ls find "tyre" >= 0} || {_ls find "tire" >= 0}) then {
            if (_t > _wheelC) then { _wheelC = _t; };
        };
        if (_ls find "weapon" >= 0 || {_ls find "turret" >= 0} || {_ls find "barrel" >= 0}) then {
            if (_t > _weaponC) then { _weaponC = _t; };
        };
    } forEach (_selTemps getOrDefault [_objKey, []]);

    // Engine-scale fraction: (T - ambient) / 50, clamped 0..1.
    private _fEngine = ((_engineC - _airTemp) / 50) max 0 min 1;
    private _fWheels = ((_wheelC - _airTemp) / 50) max 0 min 1;
    private _fWeapon = ((_weaponC - _airTemp) / 50) max 0 min 1;
    if (_engineC > -1e9) then { _engineMax = _engineMax max _fEngine; };
    if (_wheelC > -1e9) then { _wheelMax = _wheelMax max _fWheels; };
    if (_weaponC > -1e9) then { _weaponMax = _weaponMax max _fWeapon; };

    // Apply only when the state changed materially (setVehicleTIPars is
    // cheap but pointless to spam on an idle vehicle).
    private _lastPars = _x getVariable [QGVAR(tiLastPars), [-1, -1, -1]];
    if (_lastPars isEqualTo [_fEngine, _fWheels, _fWeapon]) then { continue; };
    _x setVehicleTIPars [_fEngine, _fWheels, _fWeapon];
    _x setVariable [QGVAR(tiLastPars), [_fEngine, _fWheels, _fWeapon]];
} forEach (_player nearEntities [["Car", "Tank", "Motorcycle", "Helicopter", "Plane", "Ship"], 150]);

// ─── Scene max heat from the physics model ─────────────────────────────────
// The per-selection substrate (applyBuildingThermal) paints vehicle and
// building selections from the physics surface temperature.  The AGC
// window needs the scene's hottest fraction to prevent blowout: read it
// from the physics state (thermalState), the same model the substrate
// solves from.  ambient = 0, ambient + 50 C = 1 on the engine's scale.
private _thermalState = missionNamespace getVariable [QEGVAR(thermal,thermalState), createHashMap];
private _vehicles = _player nearEntities [["Car", "Tank", "Motorcycle", "Helicopter", "Plane", "Ship"], 150];
private _sceneMax = 0.05;
{
    if (isNull _x || !alive _x) then { continue; };
    private _state = _thermalState getOrDefault [str _x, []];
    private _surfaceTemp = _airTemp;
    if (count _state >= 1) then {
        private _t = _state select 0;
        if (_t isEqualType 0) then { _surfaceTemp = _t; };
    };
    private _fraction = ((_surfaceTemp - _airTemp) / 50) min 1 max 0;
    if (_fraction > _sceneMax) then { _sceneMax = _fraction; };

    // Damage/burning state still saturates the signature.
    if (!alive _x) then { _sceneMax = 1; };
} forEach _vehicles;

// Feed the scene max from the per-selection physics heat (the hottest
// engine/wheel/weapon channel across vehicles), matching the engine's
// scale (ambient = 0, ambient + 50 C = 1).  A hot engine bay in the
// physics state must saturate the AGC guard the same way a damage state
// does - otherwise the display window compresses a scene the physics
// already sees as hot.
_sceneMax = _sceneMax max (_engineMax max _wheelMax max _weaponMax);

// Decay the scene max toward ambient over ~30 s so the gain relaxes when
// the hot source leaves view (a FLIR does not hold max gain forever).
private _prevMax = missionNamespace getVariable [QGVAR(tiSceneMaxHeat), 0.5];
if !(_prevMax isEqualType 0) then { _prevMax = 0.5; };
_sceneMax = (_sceneMax max _prevMax - 0.2 * (diag_deltaTime / 30)) max 0.05;
missionNamespace setVariable [QGVAR(tiSceneMaxHeat), _sceneMax];

count _vehicles
