#include "..\..\script_component.hpp"
/*
 * Vehicle heat state (issue #204).
 *
 * A single 0..1 heat fraction per vehicle, solved from a physically formed
 * lumped-capacitance engine body temperature, not from a reference mod's
 * normalised accumulator:
 *
 *   C * dT/dt = Q_reject - h * A * (T - T_ambient)
 *
 * The coolant thermostat regulates the engine to its opening temperature
 * T_op.  The rejection that holds that setpoint is exactly the surface loss
 * at T_op, so Q_reject = h*A*(T_op - T_ambient) while the engine runs and 0
 * while it is off.  The body relaxes toward T_op with the engine on and
 * toward T_ambient with it off.  The ODE is integrated in closed form (the
 * exact exponential), so the result does not depend on the tick interval:
 *
 *   T' = T_inf + (T - T_inf) * exp(-dt / tau),   tau = C / (h*A)
 *
 * PARAMETERS, EACH FROM A REAL RELATION
 *   m   getMass (kg), the real PhysX mass of the vehicle.
 *   c   460 J/(kg*K), specific heat of steel/cast iron (EN 1993-1-2 3.4.2).
 *   C   m*c (J/K), the lumped thermal capacitance.
 *   A   the bounding-box surface area (m^2) from boundingBoxReal.
 *   h   5.6 + 3.9*v W/(m^2*K), the air flat-plate correlation (Holman,
 *       Heat Transfer): the natural-convection value at zero airspeed, rising
 *       with the forced flow as the vehicle moves.
 *   T_op 90 C, the thermostat-open coolant temperature (Heywood, Internal
 *       Combustion Engine Fundamentals); published thermostats open at
 *       82-88 C and the coolant then runs near 90-100 C.
 *
 * LABELLED, NOT DERIVED HERE
 *   - The engine's own mass and wetted area are not exposed by the engine.
 *     The lump uses the VEHICLE mass and box, which over-estimates the
 *     reservoir and so under-estimates the warm-up rate.  A stated modelling
 *     assumption, not a measurement.
 *   - Brake heat is the kinetic energy the brakes absorb.  The published
 *     model (COMSOL, "Heat Generation in a Disc Brake", 2012) gives the
 *     instantaneous power P = m*a*v [W].  The energy per stop is
 *     E = 0.5*m*(v0^2 - v1^2) [J] over the duration t = (v0 - v1)/a [s], so
 *     the average power is P = E/t.  This term needs only getMass and the
 *     ground speed.  The config enginePower is a PhysX tuning value with no
 *     verified real unit (docs/wiki/research/vehicle-mass-estimate.md;
 *     mobility fnc_calculateEngineLoad.sqf) and is NOT read.
 *   - The COMSOL model neglects every loss outside the brakes, so assigning
 *     100 percent of the kinetic-energy change to the brakes is an UPPER
 *     BOUND.  No published value exists for the brakes-versus-road-load split
 *     of that energy.  The split here is DERIVED, not measured.
 *   - The fuel chain Q_fuel = P_brake/eta, Q_reject = Q_fuel*(1-eta) still
 *     cannot be closed from a measured output.  Diesel LHV 42.7 MJ/kg and the
 *     J/3 rejected fraction (Heywood) are published, but they only set the
 *     fuel flow that the thermostat balance implies.  No rated power is
 *     invented here.
 *   - Reference data for the brake temperatures, for context only: hard
 *     braking drives disc temperatures to 300-800 C, and fade starts above
 *     600 K.  Measured disc surface flux is 115-143.5 W/cm2.
 *   - Only the lumped body/coolant path is modelled here.  The exhaust plume
 *     is a separate consumer (fnc_applyExhaustHeat) and is not split out of
 *     this balance.
 *
 * The heat fraction maps the real body temperature through the thermostat
 * span, (T - T_ambient)/(T_op - T_ambient), so 0 is cold and 1 is at the
 * regulated engine temperature.
 *
 * State: QGVAR(vehicleHeatState) = [_heat, _lastUpdate, _stationarySince, _vMS]
 *        QGVAR(engineBodyTempC)  = the engine body temperature (C), persisted
 *                                  so the ODE carries across ticks.
 *
 * Params:
 *   0: _vehicle (OBJECT)
 *
 * Returns: SCALAR - the 0..1 heat fraction.
 */
params [["_vehicle", objNull]];

if (isNull _vehicle) exitWith { 0 };
if (_vehicle isKindOf "StaticWeapon") exitWith { 0 };

private _now = diag_tickTime;

// Airspeed drives the forced-convection term.  speed is m/s.
private _speedMS = abs (speed _vehicle);
// Ground speed in m/s for the brake term.  The engine `speed` above is
// km/h, so the brake model reads `velocity`, which is m/s.
private _vMS = vectorMagnitude (velocity _vehicle);

private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };

// Thermostat-open coolant temperature: the engine's regulated setpoint.
private _operatingTemp = 90;

// Lumped capacitance (real mass x the published specific heat of steel) and the
// surface area are FIXED FOR A VEHICLE TYPE: getMass and boundingBoxReal cannot
// change at runtime, yet both engine calls and the area algebra ran for EVERY
// object on EVERY 10 Hz tick.  Memoised by typeOf - the same pattern already
// used for the mobility SSF and the solver geometry.
private _massKg = 0;
private _capacitance = 0;
private _area = 0;
private _geoKey = typeOf _vehicle;
private _geoCache = missionNamespace getVariable [QGVAR(vehThermalGeoCache), -1];
if (_geoCache isEqualType 0) then {
    _geoCache = createHashMap;
    missionNamespace setVariable [QGVAR(vehThermalGeoCache), _geoCache];
};
private _geo = _geoCache getOrDefault [_geoKey, -1];
if (_geo isEqualType 0) then {
    _massKg = getMass _vehicle;
    _capacitance = _massKg * 460;
    private _box = boundingBoxReal _vehicle;
    if ((_box isEqualType []) && {(count _box == 2) || {count _box == 3}}
        && {(_box select 0) isEqualType []} && {(_box select 1) isEqualType []}) then {
        private _bMin = _box select 0;
        private _bMax = _box select 1;
        private _lx = abs ((_bMax select 0) - (_bMin select 0));
        private _ly = abs ((_bMax select 1) - (_bMin select 1));
        private _lz = abs ((_bMax select 2) - (_bMin select 2));
        _area = 2 * ((_lx * _ly) + (_lx * _lz) + (_ly * _lz));
    };
    _geo = [_massKg, _capacitance, _area];
    _geoCache set [_geoKey, _geo];
} else {
    _massKg = _geo select 0;
    _capacitance = _geo select 1;
    _area = _geo select 2;
};
if (_capacitance <= 0) exitWith { 0 };
if (_area <= 0) exitWith { 0 };

// Holman flat-plate correlation for air.  One expression covers natural
// convection at rest and the forced flow under way.
private _hA = (5.6 + (3.9 * _speedMS)) * _area;
private _tau = _capacitance / _hA;

private _engineRunning = isEngineOn _vehicle;

private _state = _vehicle getVariable [QGVAR(vehicleHeatState), []];
if !(_state isEqualType []) then { _state = []; };

private _previousHeat = _state param [0, 0];
if !(_previousHeat isEqualType 0) then { _previousHeat = 0; };
private _lastUpdate = _state param [1, _now];
if !(_lastUpdate isEqualType 0) then { _lastUpdate = _now; };
private _stationarySince = _state param [2, _now];
if !(_stationarySince isEqualType 0) then { _stationarySince = _now; };
private _prevSpeed = _state param [3, _vMS];
if !(_prevSpeed isEqualType 0) then { _prevSpeed = _vMS; };

private _bodyTemp = _vehicle getVariable [QGVAR(engineBodyTempC), _airTemp];
if !(_bodyTemp isEqualType 0) then { _bodyTemp = _airTemp; };

private _elapsed = (_now - _lastUpdate) max 0;

// With the engine running the thermostat holds the body at T_op; with it off
// the body falls to ambient.  The exact exponential solution of the balance.
private _target = _airTemp;
if (_engineRunning) then { _target = _operatingTemp; };
// Brake heat is the kinetic energy lost between ticks, assigned to the
// brakes.  Deceleration only: acceleration is engine work.  The average
// power over the interval comes from the tick-to-tick ground-speed change.
private _qBrake = 0;
if ((_elapsed > 0) && (_prevSpeed > _vMS)) then {
    _qBrake = (0.5 * _massKg * ((_prevSpeed * _prevSpeed) - (_vMS * _vMS))) / _elapsed;
};
// A source term shifts the equilibrium target: T_inf = T_amb + Q/(h*A).
_target = _target + (_qBrake / _hA);
if (_elapsed > 0) then {
    _bodyTemp = _target + ((_bodyTemp - _target) * exp (-(_elapsed / _tau)));
};

private _isMoving = _speedMS > 1.5;
if (_engineRunning || _isMoving) then { _stationarySince = _now; };

private _span = _operatingTemp - _airTemp;
private _heat = if (_span > 0) then {
    ((_bodyTemp - _airTemp) / _span) max 0 min 1
} else {
    0
};

// The 4th element is the ground speed from the previous call; the brake
// term above reads it.  applyExhaustHeat reads select 0 only.
_vehicle setVariable [QGVAR(vehicleHeatState), [_heat, _now, _stationarySince, _vMS]];
_vehicle setVariable [QGVAR(engineBodyTempC), _bodyTemp];

// Heat trend (rising/falling) for the material distribution - a rising
// vehicle heats its metal fastest.
private _heatDelta = _heat - _previousHeat;
private _heatTrend = 0;
if (abs _heatDelta >= 0.000001) then {
    _heatTrend = [1, -1] select (_heatDelta < 0);
};
_vehicle setVariable [QGVAR(vehicleHeatTrend), _heatTrend];

// Diagnostic trace: prove the heat pipeline.  Behind the module debug
// switch, like every other trace, and throttled to one line per vehicle per
// 5 s.  diag_log is synchronous file I/O on the render thread.
private _traceOn = AEE_TRACE_ON;
if (_traceOn) then {
    private _lastLog = _vehicle getVariable [QGVAR(vehicleHeatLogT), -999];
    if (_now - _lastLog >= 5) then {
        _vehicle setVariable [QGVAR(vehicleHeatLogT), _now];
        private _logMsg = format [
            "[HEAT] %1 T=%2C heat=%3 tau=%4s engineOn=%5 speed=%6m/s",
            typeOf _vehicle, round _bodyTemp, _heat, round _tau, _engineRunning, round _speedMS
        ];
        AEE_LOG_DEBUG(_logMsg);
    };
};

_heat
