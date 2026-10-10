#include "..\script_component.hpp"

/*
Publish the status-only state of the aircraft status systems for one local
aircraft.

WHY THIS FUNCTION EXISTS.  The engine exposes no hydraulic system, no
electrical system and no pressurisation system.  There is no pressure reader,
no generator reader, no bus-voltage reader and no cabin-pressure reader, and
there is no force, mass or velocity hook for any of them.  This kernel does
not simulate the systems.  It publishes the SOURCED NAMEPLATE STATE per
system from the generated systems row, so a status consumer (a readout, a
debug trace or a future display) can show the published figure.

THE CEILING.  Hydraulics, electrical and pressurisation are ABSENT from the
engine and are status only.  A status value cannot feed the flight dynamics
model.  The published value is NOT engine-observed and it is NOT a
measurement.  It is the sourced nameplate figure, held on the airframe as a
per-vehicle variable.  This kernel never calls a force, a mass or a velocity
command.  The flight dynamics model is ENGINE-FIXED at config load (ADR-017).

WHAT IT PUBLISHES.  One per-vehicle variable per system, from the sourced
systems row:
  - hydraulic pressure in kPa
  - generator power in kW
  - bus voltage in V
  - battery charge in Ah, the published battery capacity
  - cabin pressure in kPa
  - the oxygen system token

DETERMINISM AND LOCALITY.  The kernel runs on the machine that owns the
airframe, INCLUDING the server, so a server-owned AI airframe still carries
the published state.  The local test is the gate.  The values are a pure
function of the systems row, so every machine that owns the airframe
publishes the same state.

Guards, each explicit:
  - A null or dead vehicle is refused.
  - A non-Air vehicle is refused.  A parachute is an Air object with no
    engine, no systems and no status, so it is refused.
  - A non-local vehicle is refused, so only the owning machine writes.
  - An unknown class has no systems row, so it is refused.
  - A short systems row is refused, so a stale lookup never reads past its
    end.
  - A negative sourced figure is refused, because no status figure is
    negative.

Arguments:
  0:  _veh        (OBJECT) the aircraft to publish for
  1:  _deltaTimeS (NUMBER) elapsed interval, s, default diag_deltaTime

Return Value: BOOL - true when the status state was published
Example: [cursorObject, 1] call aee_flight_fnc_updateStatusSystems
Public: No
*/

params [["_veh", objNull, [objNull]], ["_deltaTimeS", diag_deltaTime, [0]]];

if (isNull _veh || {!alive _veh}) exitWith { false };
if !(_veh isKindOf "Air") exitWith { false };
if (_veh isKindOf "ParachuteBase") exitWith { false };

// Deterministic and local, INCLUDING the server. The owning machine is the
// only writer.
if (!local _veh) exitWith { false };

if (!(missionNamespace getVariable [QEGVAR(core,enabled), true])) exitWith { false };

private _systems = [typeOf _veh] call FUNC(getAircraftSystems);
if (_systems isEqualTo []) exitWith { false };
if ((count _systems) < 22) exitWith { false };

// The systems row holds the numeric fields first, in the generated order:
// 14 hydraulic_pressure_kpa, 15 generator_power_kw, 16 bus_voltage_v,
// 17 battery_capacity_ah, 18 cabin_pressure_max_kpa, then the enum fields
// with 21 oxygen_system.
private _hydraulicKpa = _systems select 14;
private _generatorKw = _systems select 15;
private _busV = _systems select 16;
private _batteryAh = _systems select 17;
private _cabinKpa = _systems select 18;
private _oxygen = _systems select 21;

if (_hydraulicKpa < 0 || _generatorKw < 0 || _busV < 0 || _batteryAh < 0 || _cabinKpa < 0) exitWith { false };

// Publish the sourced state. These are status values, not engine reads.
_veh setVariable [QGVAR(statusHydraulicPressureKpa), _hydraulicKpa];
_veh setVariable [QGVAR(statusGeneratorPowerKw), _generatorKw];
_veh setVariable [QGVAR(statusBusVoltageV), _busV];
_veh setVariable [QGVAR(statusBatteryChargeAh), _batteryAh];
_veh setVariable [QGVAR(statusCabinPressureMaxKpa), _cabinKpa];
_veh setVariable [QGVAR(statusOxygenSystem), _oxygen];

true
