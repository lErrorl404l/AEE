#include "..\script_component.hpp"

/*
Frost accumulation on vehicle windscreens.

Conditions for frost formation:
  • Temperature < 1 °C
  • Humidity   > 70 %
  • Overcast   < 30 %   (clear sky — frost forms on cold, clear nights)
  • Player is in / on a vehicle

Accumulation:
  +0.001 per tick while all conditions hold  (~50 ticks ≈ 4 min to max)

Decay:
  −0.01 / tick when temperature > 2 °C or humidity < 50 %
  −0.02 / tick when player is not in a vehicle (fast melt/evaporation)

Reads from missionNamespace (set by other AEE modules):
  aee_core_currentTemperature
  aee_core_currentHumidity
  aee_core_currentOvercast

Sets  QGVAR(frostIntensity) — float, 0–1
Returns QGVAR(frostIntensity)
*/

params [];

private _intensity = missionNamespace getVariable [QGVAR(frostIntensity), 0];
private _vehicle   = vehicle player;

// ─── Read environment ─────────────────────────────────────────────────────
private _temp     = missionNamespace getVariable ["aee_core_currentTemperature", 20];
private _humidity = missionNamespace getVariable ["aee_core_currentHumidity",   50];
private _overcast = missionNamespace getVariable ["aee_core_currentOvercast",   0];

// ─── Not in a vehicle — fast decay ────────────────────────────────────────
if (_vehicle isEqualTo player) exitWith {
    _intensity = (_intensity - 0.02) max 0;
    missionNamespace setVariable [QGVAR(frostIntensity), _intensity];
    _intensity
};

// ─── Frost formation ──────────────────────────────────────────────────────
if (_temp < 1 && _humidity > 70 && _overcast < 0.3) then {
    _intensity = (_intensity + 0.001) min 1;
} else {
    // Decay when warm or dry
    if (_temp > 2 || _humidity < 50) then {
        _intensity = (_intensity - 0.01) max 0;
    };
};

missionNamespace setVariable [QGVAR(frostIntensity), _intensity];

_intensity
