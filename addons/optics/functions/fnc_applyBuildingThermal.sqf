#include "..\script_component.hpp"
/*
 * Per-building thermal (issue #124 migration).
 *
 * The old version swapped building/vehicle materials to
 * ti_cloth_cold/hot.rvmat (the #123 bug class - material swaps that
 * break on third-party models and bake grey at 128).  This version
 * drives the per-selection thermal substrate: every building/vehicle
 * selection gets its temperature solved from physics (solar, McAdams
 * convection, Stefan-Boltzmann radiation to MRT) and painted with the
 * FLIR white-hot procedural colour.
 *
 * The engine gives no per-object thermal command for buildings
 * (setVehicleTIPars is vehicles only), but the TEXTURE channel is
 * scriptable the same way the material was: each selection's texture is
 * flattened to the physics-driven colour.  This is the A3TI pattern
 * (fn_setObjects) applied per selection with REAL per-selection
 * temperature from the substrate (issue #124).
 *
 * Multiplayer: setObjectTexture is LOCAL, correct for per-client
 * thermal rendering (identical physics on every client).
 */
params ["_mode"];

if (!hasInterface) exitWith { 0 };

// ─── EXIT: restore every saved texture ───────────────────────────────────
if (_mode == "EXIT") then {
    ["", "", "EXIT"] call EFUNC(thermal,applySelectionThermal);   // restore all saved
    0
};

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith { 0 };

// ─── Throttle ─────────────────────────────────────────────────────────────
// The solve is one-shot state; only rescan the expensive BUILDING list when
// ambient changes materially.  COLD-START: on the first ENTER
// (tiBldgLastTemp = -999) the swap ALWAYS applies — everything starts at
// the cold baseline, never at baked engine defaults.
//
// VEHICLES are NOT throttled by ambient: they are few, and a vehicle that
// spawns AFTER the boot pass (editor-placed, player-created, mission
// scripted) must get the cold swap immediately.
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _lastTemp = missionNamespace getVariable [QGVAR(tiBldgLastTemp), -999];
if (!(_lastTemp isEqualType 0)) then { _lastTemp = -999; };
private _ambientChanged = abs (_airTemp - _lastTemp) >= 2;
if (_ambientChanged) then {
    missionNamespace setVariable [QGVAR(tiBldgLastTemp), _airTemp];
};

// Build the object list: vehicles ALWAYS (new spawns need the swap now),
// buildings only when ambient changed (expensive near-player scan).
private _objects = [];
if (_ambientChanged) then {
    if (_mode == "ENTER") then {
        _objects = allMissionObjects "";
    } else {
        private _viewDist = (getObjectViewDistance select 0) max 300;
        _objects = (_player nearObjects ["House", _viewDist])
            + (_player nearObjects ["Building", _viewDist]);
    };
};
_objects = _objects + (vehicles - [player]);

// ─── Apply: per-selection substrate solve per object ──────────────────────
// Each object's thermal selections get the physics solve + FLIR paint.
// Selection names come from the model config (hiddenSelections order
// matches getObjectTextures index).  The substrate reads the per-
// selection material from hiddenSelectionsMaterials via the #96
// detector and solves solar/convection/radiation + inertia with the
// object's real mass.  Engine/wheel selections get an internal heat
// term; glass reflects the scene (its solve with emissivity 0.9 paints
// near-ambient, the correct LWIR mirror result).
private _applied = 0;
private _solarRadiation = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_solarRadiation isEqualType 0) then { _solarRadiation = 0; };

{
    if (isNull _x) then { continue; };
    private _obj = _x;

    // Per-class thermal selections, cached.  Buildings use the A3TI
    // discovery (all texture selections).
    private _cacheKey = format [QGVAR(tiBldgSelections_%1), typeOf _obj];
    private _selections = missionNamespace getVariable [_cacheKey, []];

    if (count _selections == 0) then {
        _selections = [];
        {
            _selections pushBack _forEachIndex;
        } forEach (getObjectTextures _obj);
        missionNamespace setVariable [_cacheKey, _selections];
    };

    if (count _selections == 0) then { continue; };

    // Selection names for the per-selection classification.
    private _selNames = getArray (configOf _obj >> "hiddenSelections");
    if (_selNames isEqualTo []) then { _selNames = selectionNames _obj; };

    // ─── Per-selection solve + FLIR paint ─────────────────────────────
    // Each selection: material from the #96 detector chain, q_internal
    // for engine/wheel areas, ground view factor by selection name.
    // The substrate applies the procedural white-hot colour and
    // persists the per-selection temperature for the inertia term.
    private _qInternal = 0;
    private _fGround = 0.5;
    // ─── Engine residual heat (issue #196) ──────────────────────────────
    // A real vehicle's engine block keeps tens of kelvin for about an
    // hour after shutdown; the hood/grille warm slowly as the block
    // cools (transient thermal signature literature).  The per-selection
    // solve must NOT cut engine heat the instant the engine stops - the
    // classic "everything cold the second the ignition is off" look.
    // Engine run time is accumulated while running and decays with
    // tau = 300 s after shutdown (same model as calculateObjectTemperature):
    // the internal heat gain scales with the residual, so a truck parked
    // for an hour reads ambient while one stopped for a minute still
    // glows.  Dead vehicles keep their residual (no further running).
    private _now = diag_tickTime;
    private _lastRT = _obj getVariable [QGVAR(engineRunTimeLast), _now];
    private _dtRT = ((_now - _lastRT) max 0) min 30;
    private _engRT = _obj getVariable [QGVAR(engineRunTime), 0];
    if !(_engRT isEqualType 0) then { _engRT = 0; };
    if (isEngineOn _obj) then {
        _engRT = _engRT + _dtRT;
    } else {
        _engRT = _engRT * exp (-_dtRT / 300);
    };
    _obj setVariable [QGVAR(engineRunTimeLast), _now];
    _obj setVariable [QGVAR(engineRunTime), _engRT];
    private _heatFrac = 1 - exp (-_engRT / 300);
    {
        private _selIdx = _x;
        if (_selIdx < count _selNames) then {
            private _sn = toLower (_selNames select _selIdx);
            _qInternal = 0;
            _fGround = 0.5;
            if (_sn find "engine" >= 0 || _sn find "exhaust" >= 0
                || _sn find "radiator" >= 0 || _sn find "motor" >= 0
                || _sn find "turret" >= 0 || _sn find "intake" >= 0) then {
                _qInternal = 770 * _heatFrac;   // engine area: ~+40 C at
                                                // 2 m/s wind, scaled by
                                                // residual engine heat
                                                // (q = h*dT + eps*sig*
                                                // (T^4-MRT^4), verified)
            };
            if (_sn find "wheel" >= 0 || _sn find "tyre" >= 0
                || _sn find "track" >= 0) then {
                _qInternal = 280;       // wheels: friction ~+15 C at 2 m/s
                _fGround = 0.7;         // tyres see mostly ground
            };
            if (_sn find "glass" >= 0 || _sn find "window" >= 0
                || _sn find "light" >= 0) then {
                _fGround = 0.2;         // glass reflects mostly sky
            };
            if (_sn find "roof" >= 0) then {
                _fGround = 0.2;         // roof sees mostly sky
            };
        };
        [_obj, (_selNames select _selIdx), "", _qInternal, _fGround] call EFUNC(thermal,applySelectionThermal);
        _applied = _applied + 1;
    } forEach _selections;
} forEach _objects;

// Diagnostic: confirms the physics baseline applies in-game.
if (missionNamespace getVariable [QGVAR(nvgDebug), false]) then {
    diag_log text format ["[AEE] Building thermal: %1 found, %2 selections painted (T=%3)",
        count _objects, _applied, round _airTemp];
};

missionNamespace setVariable [QGVAR(tiBldgLastTemp), _airTemp];
_applied
