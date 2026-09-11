#include "..\script_component.hpp"

/*
Snow accumulation / melt / drifting model.

Reads and writes QGVAR(snowDepth_m) as a leaky integrator.

  • Accretion:  temp < 0 °C + precipitation → +rain × 0.01 m
  • Melt:       temp > 2 °C                 → –0.02 × temp m
  • Stall:      0–2 °C                      → no change
  • Drift:      wind > 8 m/s + snow > 5 cm → small redistribution

Clamped 0–3.0 m.
Stored in QGVAR(snowDepth_m) and QGVAR(snowDriftIntensity) (0–1).
*/

private _T = EGVAR(core,currentTemperature);

private _depth = missionNamespace getVariable [QGVAR(snowDepth_m), 0];

if (!isNil "_T") then {
    // ─── Accretion ───────────────────────────────────────────────────────
    if (_T < 0 && rain > 0 || overcast > 0.7) then {
        _depth = _depth + (rain * 0.01);
    };

    // ─── Melt — above freezing ───────────────────────────────────────────
    if (_T > 2) then {
        _depth = _depth - (0.02 * _T);
    };
    // 0–2 °C: stall (no change)
};

_depth = _depth max 0 min 3.0;

// ─── Wind drifting ────────────────────────────────────────────────────────
private _windSpd = vectorMagnitude wind;
private _drift = 0;
if (_windSpd > 8 && _depth > 0.05) then {
    _drift = (_windSpd * 0.001) min 1.0;
};

missionNamespace setVariable [QGVAR(snowDepth_m), _depth];
missionNamespace setVariable [QGVAR(snowDriftIntensity), _drift];

if (GVAR(diagnostic)) then {
    diag_log text format [
        "[AEE] SnowAccum: depth=%1 m drift=%2 (T=%3 °C, wind=%4 m/s)",
        [_depth, 2] call CBA_fnc_formatNumber,
        [_drift, 3] call CBA_fnc_formatNumber,
        [_T, 1] call CBA_fnc_formatNumber,
        [_windSpd, 1] call CBA_fnc_formatNumber
    ];
};

_depth
