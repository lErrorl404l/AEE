#include "..\..\script_component.hpp"
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
    ["", "", "EXIT"] call FUNC(applySelectionThermal);   // restore all saved
    0
};

private _player = call CBA_fnc_currentUnit;
// Run in the player's own view: on foot (cameraOn == player) or in
// the player's vehicle (pilot/passenger/gunner - cameraOn is the
// vehicle).  Skip spectator/UAV-terminal/external cameras.
private _veh = vehicle _player;
if (isNil "_player" || !alive _player) exitWith { 0 };
if (cameraOn != _player && {cameraOn != _veh}) exitWith { 0 };

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

// ─── Apply: per-selection substrate solve per object (issue #204) ────────
// Selection discovery is DYNAMIC (fnc_getThermalSelections: Man = all
// texture slots, vehicle = config override > textureSources > all
// hiddenSelections except MFD).  The old static name-matching
// ("engine"/"wheel"/"camo") failed on modded or differently-named
// vehicles, so the engine and wheel parts never got painted.
//
// The vehicle heat is a SINGLE 0..1 value (fnc_calculateVehicleHeat,
// MKK model): engine running or moving warms toward 1 over 120 s, a
// running engine starts at 0.65 (a warm block, not cold).  Each
// selection receives heat DISTRIBUTED BY ITS MATERIAL PHYSICS - the
// conductivity k from getMaterialThermal (metal 50 conducts the
// engine heat to the skin, rubber 0.22 friction-heats when moving,
// glass 1.1 stays cold) - so every part heats correctly, no names.
private _applied = 0;
private _solarRadiation = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_solarRadiation isEqualType 0) then { _solarRadiation = 0; };

{
    if (isNull _x) then { continue; };
    private _obj = _x;

    // Dynamic thermal-selection discovery (cached per class).
    private _selNames = [_obj] call FUNC(getThermalSelections);
    if (count _selNames == 0) then { continue; };

    // Single per-vehicle heat value (MKK model) + motion state.
    private _vehicleHeat = [_obj] call FUNC(calculateVehicleHeat);
    private _isMoving = (abs (speed _obj)) > 1.5 || {vectorMagnitude (velocity _obj) > 0.5};
    private _heatTrend = _obj getVariable [QGVAR(vehicleHeatTrend), 0];

    // Selection names resolved from the indices the discovery returns.
    // getSelectionMaterials keys on NAMES - passing the raw index threw
    // "Type Number, expected String" (issue #204, the RPT error).
    private _hs = getArray (configOf _obj >> "hiddenSelections");
    private _selCount = count _selNames;
    {
        private _selIdx = _x;
        private _selName = if (_obj isKindOf "Man") then {
            private _names = selectionNames _obj;
            if (_selIdx < count _names) then { _names select _selIdx } else { "" }
        } else {
            if (_selIdx < count _hs) then { _hs select _selIdx } else { "" }
        };
        if (_selName == "") then { continue; };
        // Material physics: the conductivity k decides how the
        // vehicle heat reaches this part's skin.
        private _matClass = [_obj, _selName] call FUNC(getSelectionMaterials);
        private _matDef = _matClass call FUNC(getMaterialThermal);
        private _k = _matDef select 4;
        if !(_k isEqualType 0) then { _k = 0; };

        // Heat flux (W/m2): the vehicle heat drives metal (high k)
        // hard, low-k parts (glass, plastic) stay cool.  Metal
        // conducts the block heat; rubber friction-heats when moving.
        private _qInternal = _vehicleHeat * 770 * (_k / 50);
        private _fGround = 0.5;
        if (_k <= 1.5) then {
            // Low-k: glass/plastic/wood - reflect sky, minimal
            // conduction (the LWIR mirror result).
            _fGround = 0.2;
        };
        if (_k >= 0.2 && _k <= 2.0) then {
            // Rubber/tyre band (k ~0.22): friction heat when moving.
            if (_isMoving) then {
                _qInternal = _qInternal + 280;
            };
            _fGround = 0.7;   // tyres see mostly ground
        };
        // Heat GRADIENT across the parts (MKK wave-spread, issue #204):
        // the block heats first, the heat spreads gradually through the
        // hull as the vehicle warms - NOT a uniform glow.  The selection
        // phase (position across the part list) delays parts further
        // from the source until the heat builds; the smootherstep
        // (_heat^2 * (3 - 2*heat)) softens the edge like real diffusion.
        private _selectionPhase = if (_selCount > 1) then {
            _forEachIndex / (_selCount - 1)
        } else { 0 };
        private _waveDelay = ((_selectionPhase max 0 min 1) * 0.8) min 0.95;
        private _waveHeat = if (_heatTrend < 0) then {
            (_vehicleHeat / (1 - _waveDelay)) min 1
        } else {
            (((_vehicleHeat - _waveDelay) / (1 - _waveDelay)) max 0) min 1
        };
        _waveHeat = _waveHeat * _waveHeat * (3 - (2 * _waveHeat));
        // Rising heat warms the conductive path faster (engine warming
        // up); falling heat lingers in high-mass metal.
        if (_heatTrend > 0) then { _qInternal = _qInternal * 1.15; };

        [_obj, _selName, "", _qInternal * _waveHeat, _fGround] call FUNC(applySelectionThermal);
        _applied = _applied + 1;
    } forEach _selNames;
} forEach _objects;

// Diagnostic: confirms the physics baseline applies in-game.
if (missionNamespace getVariable [QGVAR(thermalDebug), false]) then {
    diag_log text format ["[AEE] Building thermal: %1 found, %2 selections painted (T=%3)",
        count _objects, _applied, round _airTemp];
};

missionNamespace setVariable [QGVAR(tiBldgLastTemp), _airTemp];
_applied
