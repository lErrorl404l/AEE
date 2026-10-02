#include "..\..\script_component.hpp"
#include "\z\aee\addons\main\script_debug.hpp"
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
// Restore, then STOP.  Without exitWith the run falls through into the
// apply path below and re-commits the selection textures it just undid.
if (_mode == "EXIT") exitWith {
    ["", "", "EXIT"] call FUNC(applySelectionThermal)
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

// Build the SOLVE set for this pass.  DISCOVERY (which objects exist) is now
// separate from the SOLVE (which get painted this pass): discovery ENQUEUES
// into a persistent pending list and the pass takes a bounded batch from it
// (fnc_takeThermalSweep).  Solving the whole discovered set in one call was a
// single-frame hitch: the operator's run logged about 700 objects and the
// per-selection solve measured about 1 ms each, so a full pass cost roughly
// half a second in one frame.  A full sweep now spreads across ticks.
// Hoisted out of the ambient block so the vehicle filter below can reach it.
// A `private` declared inside that block is scoped to it and would be
// undefined here, which the HEMTT undefined-variable lint caught.
private _viewDist = (getObjectViewDistance select 0) max 300;
private _pending = missionNamespace getVariable [QGVAR(tiBldgPending), []];
if !(_pending isEqualType []) then { _pending = []; };
if (_ambientChanged) then {
    // allMissionObjects "" returned 1193 objects on the operator's Altis
    // session (visible in the RPT as "Building thermal: 1193 found"), and the
    // per-selection solve then ran over EVERY one of them on thermal entry.
    // Distant objects are never painted at thermal range, so the bounded scan
    // the tick path already uses is sufficient on ENTER too.  Entering thermal
    // was a world scan; it is now a view-distance scan.
    // Building is the root of every building (House included), so the old
    // House + Building pair double-counted every house.  Add the paintable
    // non-building surfaces the scan missed: ammo crates (ReammoBox), animals,
    // and static props (Thing) that are neither a building nor a crate.  Men
    // stay on their own clothing path (fnc_applyClothingThermal).
    private _discovered = (_player nearObjects ["Building", _viewDist])
        + (_player nearObjects ["ReammoBox", _viewDist])
        + (_player nearObjects ["Animal", _viewDist])
        + ((_player nearObjects ["Thing", _viewDist]) select {
            !(_x isKindOf "Building") && {!(_x isKindOf "ReammoBox")}
        });
    // Every object is dirty when the ambient changes, so the whole discovery
    // is re-queued.  Any object the previous sweep had not reached is already
    // in _pending and stays FIRST, so a change that lands mid-sweep can never
    // starve the tail; only newly seen objects are appended.
    private _queued = createHashMap;
    { _queued set [str _x, true]; } forEach _pending;
    {
        if ((!isNull _x) && {!(_queued getOrDefault [str _x, false])}) then {
            _queued set [str _x, true];
            _pending pushBack _x;
        };
    } forEach _discovered;
    private _bldMsg = format ["building thermal scan (ENTER/ambient): %1 objects in %2 m", count _discovered, _viewDist];
    AEE_LOG_DEBUG(_bldMsg);
};
// Bound the vehicle list the same way the unit list is bounded.  This line
// ran on EVERY tick, and `vehicles` is world-wide with no radius, so it fed
// a per-selection solve for every vehicle in the mission at 10 Hz.
// GUARD + CACHE.  `vehicles` is world-wide, and this line ran on EVERY tick
// at 10 Hz over every vehicle in the mission, re-evaluating getPosATL per
// vehicle.  Cached and refreshed on a 1 s timer with the same shape as the
// mobility loops, so a newly spawned vehicle is picked up within a second.
// _viewDist is re-read on each refresh, so a view-distance change is honoured
// on the next tick.
private _vehNowT = diag_tickTime;
private _vehList = missionNamespace getVariable [QGVAR(tiVehList), []];
private _vehListT = missionNamespace getVariable [QGVAR(tiVehListT), -99];
if ((_vehList isEqualTo []) || ((_vehNowT - _vehListT) > 1)) then {
    private _playerPosATL = getPosATL _player;
    _vehList = (vehicles - [player]) select {
        (_x distance _playerPosATL) < _viewDist
    };
    missionNamespace setVariable [QGVAR(tiVehList), _vehList];
    missionNamespace setVariable [QGVAR(tiVehListT), _vehNowT];
    private _vehMsg = format ["buildingThermal vehicle cache refreshed: %1 in %2 m", count _vehList, _viewDist];
    AEE_LOG_DEBUG(_vehMsg);
};
// Take the bounded batch for this pass; the remainder stays queued.  The
// vehicle list rides every pass (it is small and its heat changes with motion
// and engine state); buildings ride the queue.  The budget is bounded (a
// variable with a floor, never unbounded) so a sweep can never stall one
// frame.  A newly spawned vehicle is already in _vehList within a second of
// the refresh above, so it is painted promptly without a separate hook.
private _sweepBudget = missionNamespace getVariable [QGVAR(sweepBudget), 16];
if !(_sweepBudget isEqualType 0) then { _sweepBudget = 16; };
private _taken = [_pending, _sweepBudget] call FUNC(takeThermalSweep);
private _objects = (_taken select 0) + _vehList;
_pending = _taken select 1;
missionNamespace setVariable [QGVAR(tiBldgPending), _pending];
if ((count (_taken select 0)) > 0) then {
    private _sweepMsg = format ["building thermal sweep batch: %1 solved, %2 pending (budget %3)", count (_taken select 0), count _pending, _sweepBudget];
    AEE_LOG_DEBUG(_sweepMsg);
};

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
// hiddenSelections is FIXED per type.  The config read below ran for every
// object on every 10 Hz tick; memoised by typeOf like the solver geometry.
private _hsCache = missionNamespace getVariable [QGVAR(bldgHsCache), -1];
if (_hsCache isEqualType 0) then {
    _hsCache = createHashMap;
    missionNamespace setVariable [QGVAR(bldgHsCache), _hsCache];
};
private _solarRadiation = missionNamespace getVariable [QEGVAR(core,currentSolarRadiation), 0];
if !(_solarRadiation isEqualType 0) then { _solarRadiation = 0; };

{
    if (isNull _x) then { continue; };
    private _obj = _x;

    // Dynamic thermal-selection discovery (cached per class).
    private _selNames = [_obj] call FUNC(getThermalSelections);
    if (count _selNames == 0) then { continue; };

    // Single per-vehicle heat value (MKK model) + motion state.
    BEGIN_COUNTER(bldgVehHeat);
    private _vehicleHeat = [_obj] call FUNC(calculateVehicleHeat);
    END_COUNTER(bldgVehHeat);
    private _isMoving = (abs (speed _obj)) > 1.5 || {vectorMagnitude (velocity _obj) > 0.5};
    private _heatTrend = _obj getVariable [QGVAR(vehicleHeatTrend), 0];

    // Selection names resolved from the indices the discovery returns.
    // getSelectionMaterials keys on NAMES - passing the raw index threw
    // "Type Number, expected String" (issue #204, the RPT error).
    private _hsKey = typeOf _obj;
    private _hs = _hsCache getOrDefault [_hsKey, -1];
    if (_hs isEqualType 0) then {
        _hs = getArray (configOf _obj >> "hiddenSelections");
        _hsCache set [_hsKey, _hs];
    };
    // HOISTED out of the per-selection loop.  selectionNames is an ENGINE call
    // and it was re-fetched for EVERY selection of EVERY object on EVERY tick -
    // the same defect applyClothingThermal had.  It depends only on the object,
    // so it is read once per object here.
    private _names = if (_obj isKindOf "Man") then { selectionNames _obj } else { [] };
    // Resolve the selection NAMES once, then map each name to its lag from the
    // heat source (fnc_getThermalSelectionLag).  The lag replaces the old
    // list-position phase: the engine bay heats first, a part further from the
    // block lags.
    private _selNamesResolved = [];
    {
        private _selIdx = _x;
        _selNamesResolved pushBack (if (_obj isKindOf "Man") then {
            if (_selIdx < count _names) then { _names select _selIdx } else { "" }
        } else {
            if (_selIdx < count _hs) then { _hs select _selIdx } else { "" }
        });
    } forEach _selNames;
    private _selLags = [_obj, _selNamesResolved] call FUNC(getThermalSelectionLag);
    {
        private _selName = _x;
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
        // phase is the DISTANCE from the heat source now (the engine point,
        // fnc_getThermalSelectionLag), so a part further from the block
        // lags until the heat builds; the smootherstep
        // (_heat^2 * (3 - 2*heat)) softens the edge like real diffusion.
        private _selectionPhase = _selLags param [_forEachIndex, 0];
        if !(_selectionPhase isEqualType 0) then { _selectionPhase = 0; };
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
    } forEach _selNamesResolved;
} forEach (_objects + ([_objects] call FUNC(collectThermalNestedObjects)));

// Diagnostic: confirms the physics baseline applies in-game.
if (missionNamespace getVariable [QGVAR(thermalDebug), false]) then {
    diag_log text format ["[AEE] Building thermal: %1 found, %2 selections painted (T=%3)",
        count _objects, _applied, round _airTemp];
};

missionNamespace setVariable [QGVAR(tiBldgLastTemp), _airTemp];
_applied
