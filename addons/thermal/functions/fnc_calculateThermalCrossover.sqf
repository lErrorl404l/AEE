#include "..\script_component.hpp"

/*
Diurnal thermal crossover detection — nullifies thermal optic contrast.

When ambient air temperature and ground surface temperature converge within
~1.5 °C, the thermal gradient disappears and FLIR/IR systems lose contrast.
A sustained timer (~1 tick ≈ 5 s) prevents brief fluctuations from
triggering false positives.

Stored in GVAR(thermalCrossoverActive) (bool) and GVAR(surfaceTemperature).
*/

private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), missionNamespace getVariable [QEGVAR(core,currentTemperature), 15]];
private _groundState = missionNamespace getVariable [QEGVAR(core,groundState), "Normal"];
private _overcast = overcast;

// ─── Estimate surface temperature from ground state ─────────────────────
private _surfaceTemp = switch (_groundState) do {
    case "Snow":   { _airTemp - 2 };
    case "Mud":    { _airTemp - 1 };
    case "Dusty":  { _airTemp + 5 };
    case "Frozen": { _airTemp - 3 };
    default        { _airTemp + 2 * (1 - _overcast) }; // Normal: solar heating
};

// ─── Crossover when within 1.5 °C ──────────────────────────────────────
private _delta = abs (_airTemp - _surfaceTemp);
private _crossoverNow = _delta <= 1.5;

// ─── Timer accumulator — sustain for ~1 tick ──────────────────────────
private _timer = missionNamespace getVariable [QEGVAR(core,crossoverTimer), 0];

if (_crossoverNow) then {
    _timer = _timer + 1;
} else {
    _timer = _timer - 1;
};

_timer = _timer max -6 min 6;

private _active = _timer > 1;

missionNamespace setVariable [QEGVAR(core,crossoverTimer), _timer];
missionNamespace setVariable [QEGVAR(core,thermalCrossoverActive), _active];
missionNamespace setVariable [QEGVAR(core,surfaceTemperature), _surfaceTemp];

_active
