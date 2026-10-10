#include "..\script_component.hpp"

/*
Per-tick ground-vehicle fuel consumption and coolant thermal management
(issue #111).

WHY THIS FUNCTION EXISTS.  The engine burns fuel at its own config
fuelConsumptionRate, which is not the brake-specific consumption the brief
models.  This driver computes the modelled consumption from the road load and
the brake-specific fuel consumption, and the coolant temperature from the heat
that consumption rejects, and publishes both on the vehicle.  It does not call
setFuel: the engine owns the tank, and a second burn would double-count the
engine's own rate.  The model is the published state; a consumer that wants to
drain the tank reads it.

THE CHAIN, one tick:
  1. road load   aee_vehicles_fnc_calculateRoadLoad  -> drive power, W
  2. fuel rate   aee_vehicles_fnc_calculateFuelRate  -> L/h and kg/s
  3. heat reject Q = heat_reject_fraction * fuel_mass_rate * LHV
  4. coolant     aee_vehicles_fnc_calculateCoolantTemperature -> coolant C
  5. derate      aee_vehicles_fnc_calculateCoolantDerate -> derate and fan

Every constant is read from the generated table aee_vehicles_fnc_getFuelData,
which is the runtime projection of data/physics/fuel.json.  The kernel takes
the constants as arguments, so this driver is the only place that joins them.

THE ROLLING-RESISTANCE BASE.  The corpus holds no per-vehicle rolling
coefficient.  The base is the vehicle type: a tracked class takes the track
anchor and a wheeled class the truck anchor, and the mobility ground state
scales it (Normal 1.0, Mud 2.5, ...).  The base is a declared default stated
in the corpus, not a measured per-vehicle value.

THE ENGINE CLASS.  The corpus holds no per-vehicle engine class, so the class
is a user setting with a documented default (diesel, the fuel of the military
ground fleet the brief lists).  This is the honest ceiling: a per-vehicle
engine class would need a held field the corpus does not carry.

THE IDLE POWER.  The idle power is the same declared fraction of the same
declared rated power the engine-load kernel aee_vehicles_fnc_calculateEngineLoad
declares.  It is a declared default, not a measurement.

Guards, each explicit: a disabled module or setting, a null or dead local unit,
a non-positive interval, a non-local vehicle, a static weapon, an unresolved
class or fuel, and an unusable road-load result each skip the vehicle.

Arguments:
  0: _deltaTimeS (NUMBER) elapsed interval, s, default the core tick interval
Return Value: BOOL - true when the pass ran.
Example: [] call aee_vehicles_fnc_updateFuelConsumption
Public: No
*/

params [["_deltaTimeS", -1, [0]]];

if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { false };
if (!GVAR(fuelConsumptionEnabled)) exitWith { false };

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || {isNull _player} || {!alive _player}) exitWith { false };

private _dt = _deltaTimeS;
if (_dt < 0) then {
    _dt = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
};
if (_dt <= 0) exitWith { false };

// ─── Constants ─────────────────────────────────────────────────────────────
private _data = call FUNC(getFuelData);
private _classes = _data get "engine_classes";
private _fuels = _data get "fuels";
private _rolling = _data get "rolling_resistance";
private _terrain = _data get "terrain_multipliers";
private _thermal = _data get "thermal";

private _classIds = ["diesel", "petrol_na", "petrol_turbo"];
private _classIndex = GVAR(engineFuelClass) max 0 min 2;
private _classRow = _classes getOrDefault [_classIds select _classIndex, []];
if (_classRow isEqualTo []) exitWith { false };
private _bsfc = _classRow select 0;
private _fuelRow = _fuels getOrDefault [_classRow select 1, []];
if (_fuelRow isEqualTo []) exitWith { false };
private _density = _fuelRow select 0;
private _lhv = _fuelRow select 1;

private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _terrainMult = _terrain getOrDefault [_groundState, 1.0];
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
if !(_rho isEqualType 0) then { _rho = 1.225; };

private _normalMax = _thermal getOrDefault ["coolant_normal_max_c", 100];
private _hotMax = _thermal getOrDefault ["coolant_hot_max_c", 115];
private _critical = _thermal getOrDefault ["coolant_critical_c", 130];
private _overheatDerate = _thermal getOrDefault ["coolant_overheat_derate", 0.5];
private _heatFraction = _thermal getOrDefault ["heat_reject_fraction", 0.333333];
private _convNatural = _thermal getOrDefault ["convection_natural_w_m2k", 5.6];
private _convForced = _thermal getOrDefault ["convection_forced_w_m2k_per_ms", 3.9];
private _coolantTau = _thermal getOrDefault ["coolant_tau_s", 90];

// The declared idle power and drag area reuse the engine-load kernel's own
// declared defaults, so the two kernels agree on the same nominal vehicle.
private _idlePowerW = 0.05 * 150000;
private _dragAreaM2 = 0.7;

private _playerDerate = 1.0;
private _vehicles = [200, _player] call EFUNC(vehicles,getNearbyVehicles);

{
    private _veh = _x;
    if (!local _veh || {!alive _veh} || {_veh isKindOf "StaticWeapon"}) then { continue; };

    private _class = [_veh] call EFUNC(vehicles,classifyVehicle);
    private _type = _class select 1;
    private _massKg = _class select 4;
    if (_massKg <= 0) then { _massKg = getMass _veh; };

    private _crrBase = if (_type == "tracked") then {
        _rolling getOrDefault ["track", 0.03]
    } else {
        _rolling getOrDefault ["truck", 0.007]
    };
    private _crr = _crrBase * _terrainMult;

    private _speedMS = vectorMagnitude (velocity _veh);
    private _prevSpeed = _veh getVariable [QGVAR(prevSpeedMS), _speedMS];
    if !(_prevSpeed isEqualType 0) then { _prevSpeed = _speedMS; };
    private _accelMS2 = (_speedMS - _prevSpeed) / _dt;
    _veh setVariable [QGVAR(prevSpeedMS), _speedMS];

    private _gradeSin = (vectorDir _veh) select 2;
    private _load = [_massKg, _speedMS, _accelMS2, _crr, _gradeSin, _dragAreaM2, _rho]
        call FUNC(calculateRoadLoad);
    if ((_load select 0) < 0) then { continue; };

    private _fuel = [_idlePowerW, _load select 1, _bsfc, _density] call FUNC(calculateFuelRate);
    if ((_fuel select 0) < 0) then { continue; };
    private _fuelRateLph = _fuel select 0;
    private _fuelMassRateKgs = _fuel select 1;

    private _speedKmh = _speedMS * 3.6;
    private _per100km = -1;
    if (_speedKmh > 1) then { _per100km = (_fuelRateLph / _speedKmh) * 100; };

    private _capacityL = getNumber (configOf _veh >> "fuelCapacity");
    private _rangeKm = -1;
    if ((_capacityL > 0) && (_fuelRateLph > 0) && (_speedKmh > 1)) then {
        _rangeKm = ((_capacityL * (fuel _veh)) * _speedKmh) / _fuelRateLph;
    };

    // Coolant: the surface area is the bounding-box area, the same source the
    // vehicle heat model aee_thermal_fnc_calculateVehicleHeat uses.
    private _box = boundingBoxReal _veh;
    private _area = 0;
    if ((_box isEqualType []) && ((count _box) >= 2)
        && {(_box select 0) isEqualType []} && {(_box select 1) isEqualType []}) then {
        private _bMin = _box select 0;
        private _bMax = _box select 1;
        private _lx = abs ((_bMax select 0) - (_bMin select 0));
        private _ly = abs ((_bMax select 1) - (_bMin select 1));
        private _lz = abs ((_bMax select 2) - (_bMin select 2));
        _area = 2 * ((_lx * _ly) + (_lx * _lz) + (_ly * _lz));
    };

    private _tAmb = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
    if !(_tAmb isEqualType 0) then { _tAmb = 15; };

    private _ua = (_convNatural + (_convForced * _speedMS)) * _area;
    private _qReject = _heatFraction * _fuelMassRateKgs * _lhv * 1e6;   // LHV MJ/kg -> J/kg

    private _tCool = _veh getVariable [QGVAR(coolantTempC), _tAmb];
    if !(_tCool isEqualType 0) then { _tCool = _tAmb; };
    _tCool = [_tAmb, _qReject, _ua, _coolantTau, _tCool, _dt]
        call FUNC(calculateCoolantTemperature);
    _veh setVariable [QGVAR(coolantTempC), _tCool];

    private _derate = [_tCool, _normalMax, _hotMax, _critical, _overheatDerate]
        call FUNC(calculateCoolantDerate);

    _veh setVariable [QGVAR(fuelRateLph), _fuelRateLph];
    _veh setVariable [QGVAR(fuelPer100km), _per100km];
    _veh setVariable [QGVAR(fuelRangeKm), _rangeKm];
    _veh setVariable [QGVAR(coolantDerate), _derate select 0];
    _veh setVariable [QGVAR(coolantFanOn), _derate select 1];

    if (_veh isEqualTo (vehicle _player)) then { _playerDerate = _derate select 0; };
} forEach _vehicles;

// The player's vehicle derate drives the global coolant derate the engine
// power model applies.
missionNamespace setVariable [QGVAR(coolantPowerDerate), _playerDerate];

true
