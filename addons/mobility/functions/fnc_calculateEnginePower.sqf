#include "..\script_component.hpp"

/*
Throttle modifiers for ground-vehicle engines (minEnginePower–1.0).

Naturally-aspirated power falls with altitude (thinner air) and high
ambient temperature (lower air density).  Turbocharged engines retain
more power at altitude via forced induction.

Stored in:
  QGVAR(enginePowerModifier)   — naturally-aspirated modifier
  QGVAR(engineTurboModifier)   — turbocharged modifier (less affected)
*/

params [["_posASL", [], [[]]]];

private _alt = 0;
private _pos = _posASL;
// Accept both a bare position [x, y, z] and a single-element wrapper
// [[x, y, z]] (some callers pass the array-of-array form).
if ((count _pos) == 1 && {(_pos select 0) isEqualType []}) then {
    _pos = _pos select 0;
};
if ((count _pos) >= 3) then {
    _alt = _pos select 2;
} else {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player") then {
        _alt = (getPosASL _player) select 2;
    };
};

private _T = EGVAR(core,currentTemperature);
if (isNil "_T") then { _T = 15 };

// ─── Battery cold-start gating (issue #36) ────────────────────────────────
// Cold Li-ion cells deliver a fraction of rated capacity (0.3-1.0 from
// the physiology model).  Below 0.7 derating the starter cannot crank
// reliably; below 0.5 the engine fails to start (cold-soak).  The crank
// probability scales 0.2-1.0 across 0.5-0.7, stored for vehicle-start
// consumers and applied as a gate on the power modifier.
private _batteryDerate = missionNamespace getVariable [QEGVAR(physiology,batteryTemperatureDerating), 1.0];
if !(_batteryDerate isEqualType 0) then { _batteryDerate = 1.0; };
_batteryDerate = _batteryDerate max 0.3 min 1.0;
private _crankSuccess = if (_batteryDerate < 0.5) then {
    0
} else {
    linearConversion [0.5, 0.7, _batteryDerate, 0.2, 1.0, true]
};
missionNamespace setVariable [QGVAR(crankSuccess), _crankSuccess];

// ─── Naturally-aspirated engine ──────────────────────────────────────────
// SAE J1349 / ISO 1585 density correction: power derates with the
// air-density ratio to the power 1.2.  20 % loss by 55 °C.
private _density = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
private _powerRatio = (_density / 1.225) ^ 1.2;
private _power = (1.0 - ((0 max (_T - 15)) / 40) * 0.2) * _powerRatio;
private _minPower = missionNamespace getVariable [QGVAR(minEnginePower), 0.3];
_power = _power max _minPower min 1.0;
// A battery that cannot crank the engine yields no power at all.
if (_crankSuccess <= 0) then { _power = 0; };

// ─── Turbocharged engine — less altitude-sensitive ───────────────────────
// 35 % loss by 9000 m; temperature effect same
private _turbo = 1.0 - ((0 max (_alt - 2000)) / 7000) * 0.35 - ((0 max (_T - 15)) / 40) * 0.2;
_turbo = _turbo max 0.3 min 1.0;
if (_crankSuccess <= 0) then { _turbo = 0; };

missionNamespace setVariable [QGVAR(enginePowerModifier), _power];
missionNamespace setVariable [QGVAR(engineTurboModifier), _turbo];

if (EGVAR(core,diagnostic)) then {
    diag_log text format [
        "[AEE] EnginePower: NA=%1 Turbo=%2 Crank=%3 (alt=%4 m, T=%5 °C, bat=%6)",
        [_power, 2] call CBA_fnc_formatNumber,
        [_turbo, 2] call CBA_fnc_formatNumber,
        [_crankSuccess, 2] call CBA_fnc_formatNumber,
        [_alt, 0] call CBA_fnc_formatNumber,
        [_T, 1] call CBA_fnc_formatNumber,
        [_batteryDerate, 2] call CBA_fnc_formatNumber
    ];
};

_power
