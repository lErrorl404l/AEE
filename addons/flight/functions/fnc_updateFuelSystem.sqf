#include "..\script_component.hpp"

/*
Burn one interval of fuel on one local aircraft and move its centre of
gravity.

WHY THIS FUNCTION EXISTS.  The engine reads fuelCapacity, fuelConsumptionRate
and fuel, and it exposes setFuel, so the fuel LEVEL is engine-owned.  The
generated config sets fuelConsumptionRate to zero for every bound aircraft
class, because the sourced rate lives in the systems row and a nonzero config
rate would double-count.  This kernel is the scripted burn that replaces it.
It reads the generated systems row through aee_flight_fnc_getAircraftSystems
and does the arithmetic in the pure kernel aee_flight_fnc_calculateFuelBurn.

DETERMINISM AND LOCALITY.  The burn is DETERMINISTIC and it runs on the machine
that owns the airframe, INCLUDING the server.  The local test is the gate.  A
server-owned AI airframe therefore burns fuel and never has infinite fuel.  A
remote client never writes another machine's fuel state.  Every machine that
owns the same airframe computes the same burn from the same systems row and
the same elapsed interval, so the state agrees.

THE TWO EFFECTS.
  - The fuel level is the remaining mass over the full mass, written with
    setFuel.  The engine's own burn is zero, so this is the only burn.
  - The centre of gravity is the fuel's mass-weighted share of the fuel arm,
    written with setCenterOfMass.  The model is stated in the pure kernel.

THE RATE.  The sourced fuel_consumption_rate drives the burn.  When the corpus
holds no rate, the pure kernel derives it from sfc_kg_kwh and the rated power.
The rated power is the flight-model row's rated_power_w, never a config value.

THE CEILING.  Fuel is built-in partial.  The engine reads fuelCapacity,
fuelConsumptionRate and fuel, and it exposes setFuel.  Fuel TRANSFER between
tanks and fuel JETTISON are scripted only: the engine exposes neither, so this
kernel does not model them.  The centre-of-gravity shift is scripted, not
engine-owned.  Fuel is not gated on difficultyEnabledRTD: setFuel is not an RTD
command.  The RTD gate applies to the engine system, not to fuel.

Guards, each explicit:
  - A null or dead vehicle is refused.
  - A non-Air vehicle is refused.  A parachute is an Air object with no engine
    or tank, so it is refused.
  - A non-local vehicle is refused, so only the owning machine writes.
  - An unknown class has no systems row, so it is refused.
  - A non-positive fuel capacity or density is refused before any conversion,
    so the kernel never divides by zero.  The pure kernel repeats the
    full-mass guard.

Arguments:
  0:  _veh        (OBJECT) the aircraft to burn
  1:  _deltaTimeS (NUMBER) elapsed interval, s, default 0

Return Value: BOOL - true when the burn was applied
Example: [cursorObject, 1] call aee_flight_fnc_updateFuelSystem
Public: No
*/

params [["_veh", objNull, [objNull]], ["_deltaTimeS", 0, [0]]];

if (isNull _veh || {!alive _veh}) exitWith { false };
if !(_veh isKindOf "Air") exitWith { false };
if (_veh isKindOf "ParachuteBase") exitWith { false };

// Deterministic and local, INCLUDING the server. The owning machine is the
// only writer.
if (!local _veh) exitWith { false };

if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { false };

private _systems = [typeOf _veh] call FUNC(getAircraftSystems);
if (_systems isEqualTo []) exitWith { false };

private _fuelCapacityL = _systems select 0;
private _sourcedRate = _systems select 1;
private _density = _systems select 2;
private _sfc = _systems select 3;
private _cgArm = _systems select 4;

// A zero capacity or density cannot be divided by. Refuse before any
// conversion, so the kernel never divides by zero.
if (_fuelCapacityL <= 0 || {_density <= 0}) exitWith { false };

private _fullMassKg = _fuelCapacityL * _density;

// The rated power feeds the derived burn when the corpus holds no sourced
// rate. It is the flight-model row's rated power, never a config value.
private _data = [typeOf _veh] call FUNC(getAircraftData);
private _ratedPowerW = if (_data isEqualTo []) then { 0 } else { _data select 1; };

// The current fuel mass from the engine's fuel fraction.
private _currentMassKg = (fuel _veh) * _fullMassKg;

private _state = [
    _currentMassKg,
    _sourcedRate,
    _sfc,
    _ratedPowerW,
    _deltaTimeS,
    _fullMassKg,
    _cgArm
] call FUNC(calculateFuelBurn);

if ((_state select 0) < 0) exitWith { false };

private _remainingKg = _state select 0;
private _cgOffsetM = _state select 1;

_veh setFuel ((_remainingKg / _fullMassKg) min 1 max 0);
_veh setCenterOfMass [_cgOffsetM, 0, 0];

true
