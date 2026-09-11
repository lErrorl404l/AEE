#include "..\script_component.hpp"

/*
Throttle modifiers for ground-vehicle engines (0.3–1.0).

Naturally-aspirated power falls with altitude (thinner air) and high
ambient temperature (lower air density).  Turbocharged engines retain
more power at altitude via forced induction.

Stored in:
  QGVAR(enginePowerModifier)   — naturally-aspirated modifier
  QGVAR(engineTurboModifier)   — turbocharged modifier (less affected)
*/

params [["_posASL", [], [[]]]];

private _alt = 0;
if (_posASL isEqualTo []) then {
    private _player = call CBA_fnc_currentUnit;
    if (!isNil "_player") then {
        _alt = (getPosASL _player) select 2;
    };
} else {
    _alt = _posASL select 2;
};

private _T = EGVAR(core,currentTemperature);
if (isNil "_T") then { _T = 15 };

// ─── Naturally-aspirated engine ──────────────────────────────────────────
// 50 % loss by 4500 m, 20 % loss by 55 °C
private _power = 1.0 - ((0 max (_alt - 500)) / 4000) * 0.5 - ((0 max (_T - 15)) / 40) * 0.2;
_power = _power max 0.3 min 1.0;

// ─── Turbocharged engine — less altitude-sensitive ───────────────────────
// 35 % loss by 9000 m; temperature effect same
private _turbo = 1.0 - ((0 max (_alt - 2000)) / 7000) * 0.35 - ((0 max (_T - 15)) / 40) * 0.2;
_turbo = _turbo max 0.3 min 1.0;

missionNamespace setVariable [QGVAR(enginePowerModifier), _power];
missionNamespace setVariable [QGVAR(engineTurboModifier), _turbo];

if (EGVAR(core,diagnostic)) then {
    diag_log text format [
        "[AEE] EnginePower: NA=%1 Turbo=%2 (alt=%3 m, T=%4 °C)",
        [_power, 2] call CBA_fnc_formatNumber,
        [_turbo, 2] call CBA_fnc_formatNumber,
        [_alt, 0] call CBA_fnc_formatNumber,
        [_T, 1] call CBA_fnc_formatNumber
    ];
};

_power
