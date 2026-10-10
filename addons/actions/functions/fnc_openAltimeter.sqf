#include "..\script_component.hpp"

/*
Player-initiated altimeter readout — shows QNH, current altitude, standard
pressure altitude, and pressure trend via hintSilent structured text.

Gate: player is vehicle driver or gunner
Reads: GVAR(currentPressure), EGVAR(core,currentTemperature),
       GVAR(currentPressureTrend)
*/

private _player = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player) exitWith {};

private _veh = vehicle _player;
if (_veh == _player) exitWith {};
private _role = assignedVehicleRole _player;
if (_role isEqualTo [] || (_role select 0) != "driver" && (_role select 0) != "gunner") exitWith {};

private _pressure  = missionNamespace getVariable [QEGVAR(core,currentPressure), ISA_SEA_LEVEL_PRESSURE_HPA];
private _temp      = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _altitude  = (getPosASL _player) select 2;

// ─── Compute QNH (reduction to sea level, ICAO standard atmosphere) ─────
// QNH = P * (1 - (ISA_LAPSE_RATE * h / (T + ISA_LAPSE_RATE * h + KELVIN_OFFSET))) ^ (-5.257)
private _lapse = ISA_LAPSE_RATE;
private _denom = _temp + _lapse * _altitude + KELVIN_OFFSET;
private _qnh = _pressure * (1 - (_lapse * _altitude / _denom)) ^ (-5.257);

// Standard pressure altitude (rough approximation: ~30 ft / hPa)
private _stdAlt = _altitude + (ISA_SEA_LEVEL_PRESSURE_HPA - _pressure) * 30;

// ─── Pressure trend ─────────────────────────────────────────────────────
private _trendText = missionNamespace getVariable [QEGVAR(core,currentPressureTrend), ""];
if (isNil "_trendText" || _trendText == "") then { _trendText = "Stable"; };

hintSilent format [
    "<t size='1.4' align='center'>ALTIMETER</t><br/><br/>
    <t size='1.1'>QNH: %1 hPa</t><br/>
    <t size='1.1'>Current Alt: %2 m</t><br/>
    <t size='1.1'>Std Alt: %3 m</t><br/>
    <t size='0.8' color='#808080'>%4</t>",
    round _qnh,
    round _altitude,
    round _stdAlt,
    _trendText
];
