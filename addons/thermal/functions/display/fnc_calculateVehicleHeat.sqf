#include "..\..\script_component.hpp"
/*
 * Vehicle heat state (issue #204).
 *
 * A single 0..1 heat value per vehicle, driven by the MKK heat model
 * (3753145363 fnc_setThermalMaterials _getVehicleHeat):
 *
 *   - Engine RUNNING or the vehicle MOVING -> heat warms toward 1
 *     over TI_VEHICLE_HEAT_WARMUP_TIME (120 s)
 *   - Engine off AND stationary -> heat decays toward 0 over
 *     TI_VEHICLE_HEAT_COOLDOWN_TIME (320 s), after a
 *     TI_VEHICLE_HEAT_COOLDOWN_DELAY (120 s) grace
 *   - A vehicle spawned with the engine RUNNING starts at
 *     TI_VEHICLE_HEAT_INITIAL_RUNNING (0.65) - a warm block, not cold
 *     (this is why MKK vehicles glow immediately; the old code started
 *     every vehicle at 0 and warmed so slowly nothing ever showed)
 *
 * The heat is the PER-VEHICLE source; applyBuildingThermal distributes
 * it to each selection by the selection's MATERIAL physics (metal
 * conducts, rubber friction-heats, glass stays cold).  This replaces
 * the static selection-name matching (_sn find "engine"/"wheel") that
 * failed on every modded or differently-named vehicle.
 *
 * State: QGVAR(vehicleHeatState) = [_heat, _lastUpdate, _stationarySince, _lastPosASL]
 *
 * Params:
 *   0: _vehicle (OBJECT)
 *
 * Returns: SCALAR - the 0..1 heat state.
 */
params [["_vehicle", objNull]];

if (isNull _vehicle) exitWith { 0 };
if (_vehicle isKindOf "StaticWeapon") exitWith { 0 };

private _now = diag_tickTime;
private _positionASL = getPosASL _vehicle;
private _motionSpeed = (abs (speed _vehicle)) max ((vectorMagnitude (velocity _vehicle)) * 3.6);

// Warm-up / cooldown time constants (MKK proven values).
private _warmupTime = 120;
private _cooldownDelay = 120;
private _cooldownTime = 320;
private _movementThreshold = 1.5;   // km/h
private _movementGrace = 3;         // s
private _initialRunning = 0.65;
private _trendEpsilon = 0.000001;

private _state = _vehicle getVariable [QGVAR(vehicleHeatState), []];
private _engineRunning = isEngineOn _vehicle;

if (count _state == 0) then {
    // First evaluation: a stationary vehicle with the engine running is
    // already warm (a hot block), a moving one starts cold and warms.
    private _initialMoving = _motionSpeed > _movementThreshold;
    private _initialHeat = _initialRunning * (parseNumber (_engineRunning && {!_initialMoving}));
    _state = [_initialHeat, _now, _now, _positionASL];
};

_state params ["_heat", "_lastUpdate", "_stationarySince", ["_lastPositionASL", _positionASL]];
private _previousHeat = _heat;
private _elapsed = (_now - _lastUpdate) max 0;

// Position-derived speed (velocity can be 0 while the vehicle moves on
// slopes / over terrain in some states).
private _positionSpeed = if (_elapsed > 0) then {
    ((_positionASL vectorDistance _lastPositionASL) / _elapsed) * 3.6
} else { 0 };

private _isMoving = (_motionSpeed max _positionSpeed) > _movementThreshold;
private _isHeating = _engineRunning || _isMoving;

if (_isHeating) then {
    // Engine or motion maintains/raises the heat.
    _heat = (_heat + (_elapsed / _warmupTime)) min 1;
    _stationarySince = _now;
} else {
    // Cooldown after the grace delay (lets a just-stopped engine keep
    // its residual glow instead of vanishing instantly).
    private _delay = _cooldownDelay max _movementGrace;
    if ((_now - _stationarySince) >= _delay) then {
        _heat = (_heat - (_elapsed / _cooldownTime)) max 0;
    };
};

_vehicle setVariable [QGVAR(vehicleHeatState), [_heat, _now, _stationarySince, _positionASL]];

// Heat trend (rising/falling) for the material distribution - a rising
// vehicle heats its metal fastest.
private _heatDelta = _heat - _previousHeat;
private _heatTrend = 0;
if (abs _heatDelta >= _trendEpsilon) then {
    _heatTrend = [1, -1] select (_heatDelta < 0);
};
_vehicle setVariable [QGVAR(vehicleHeatTrend), _heatTrend];

// Diagnostic trace: prove the heat pipeline. Behind the module debug
// switch, like every other trace, and throttled to one line per vehicle
// per 5 s. A diagnostic that writes unconditionally is a client cost:
// diag_log is synchronous file I/O on the render thread.
private _traceOn = missionNamespace getVariable [QGVAR(logDebug), false]
    || missionNamespace getVariable ["aee_core_logDebug", false]
    || missionNamespace getVariable [format ["aee_%1_logDebug", QUOTE(COMPONENT)], false];
if (_traceOn) then {
    private _lastLog = _vehicle getVariable [QGVAR(vehicleHeatLogT), -999];
    if (_now - _lastLog >= 5) then {
        _vehicle setVariable [QGVAR(vehicleHeatLogT), _now];
        diag_log format [
            "[AEE][HEAT] %1 heat=%2 engineOn=%3 moving=%4 speed=%5kph trend=%6",
            typeOf _vehicle, _heat, _engineRunning, _isMoving, round _motionSpeed, _heatTrend
        ];
    };
};

_heat
