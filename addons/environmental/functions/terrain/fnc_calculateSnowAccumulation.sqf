#include "..\..\script_component.hpp"

/*
Snow accumulation / melt / drifting model.

Reads and writes QEGVAR(core,snowDepth_m) as a leaky integrator.

  • Accretion:  temp < 0 °C AND precipitation or heavy overcast
                → +rain × accretion rate m per tick.  The condition is
                grouped so snow needs BOTH cold AND moisture (a dry
                overcast day does not snow).
  • Melt:       temp > 2 °C → –0.003 × temp m per DAY (degree-day melt,
                ~3 mm/°C/day), scaled to the tick.
  • Stall:      0–2 °C      → no change
  • Drift:      wind > 8 m/s + snow > 5 cm → small redistribution

Clamped 0–max snow depth.
Stored in QEGVAR(core,snowDepth_m) and QGVAR(snowDriftIntensity) (0–1).
*/

private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _interval = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];

private _depth = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
// Kept for the melt flux below: the depth before this tick's change is
// what melted, and the depth after is what remains.
private _prevDepth = _depth;

private _accretionRate = missionNamespace getVariable [QGVAR(SnowAccretionRate), 0.01];
private _maxSnowDepth = missionNamespace getVariable [QGVAR(MaxSnowDepth), 3.0];

if (!isNil "_T") then {
    // ─── Accretion — cold AND moisture (precipitation or heavy overcast) ──
    if (_T < 0 && (rain > 0 || overcast > 0.7)) then {
        _depth = _depth + (rain * _accretionRate * (_interval / 5));
    };

    // ─── Melt — degree-day melt ~3 mm per °C per day, scaled to tick ──────
    // 0.003 m/°C/day ÷ (86400 / _interval) ticks/day
    if (_T > 2) then {
        _depth = _depth - (0.003 * _T * (_interval / 86400));
    };
    // 0–2 °C: stall (no change)
};

_depth = _depth max 0 min _maxSnowDepth;

// ─── Melt heat flux, for the soil surface balance (issue #11) ─────────────
// Melting snow consumes latent heat, and that heat comes from the ground
// and the air above it. Without this the soil surface reads warm through a
// thaw, because the balance has no sink for it.
//
// The snow owner computes the melt, so the snow owner publishes the flux.
// The node stack reads it. One writer per variable, which is the rule the
// mod already applies to the biome class and the chambering.
//
//   flux W/m2 = melt_depth_m * rho_snow * L_f / interval_s
//
// Positive means the surface is LOSING heat to the melt.
private _meltFlux = 0;
if (_T > 2 && _depth < _prevDepth) then {
    private _snowDensity = (missionNamespace getVariable [QEGVAR(environmental,slabDensity), 300]) / 1000;
    if !(_snowDensity isEqualType 0) then { _snowDensity = 0.3 };
    private _rhoSnowKgM3 = _snowDensity * 1000;
    private _lFus = 334e3;                  // J/kg, IAPWS-95
    private _meltDepthM = _prevDepth - _depth;
    private _intervalS = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
    if !(_intervalS isEqualType 0) then { _intervalS = 5; };
    _meltFlux = (_meltDepthM * _rhoSnowKgM3 * _lFus) / (_intervalS max 1);
};
missionNamespace setVariable [QEGVAR(core,snowMeltFlux_Wm2), _meltFlux];

// ─── Wind drifting ────────────────────────────────────────────────────────
private _windSpd = vectorMagnitude wind;
private _drift = 0;
if (_windSpd > 8 && _depth > 0.05) then {
    _drift = (_windSpd * 0.001) min 1.0;
};

missionNamespace setVariable [QEGVAR(core,snowDepth_m), _depth];
missionNamespace setVariable [QGVAR(snowDriftIntensity), _drift];

if (missionNamespace getVariable [QEGVAR(core,diagnostic), false]) then {
    diag_log text format [
        "[AEE] SnowAccum: depth=%1 m drift=%2 (T=%3 °C, wind=%4 m/s)",
        // CBA_fnc_formatNumber is [number, integerWidth, decimalPlaces]:
        // the 2nd arg is integer width, so 0.5 m showed as "00" (issue #177).
        [_depth, 0, 2] call CBA_fnc_formatNumber,
        [_drift, 0, 3] call CBA_fnc_formatNumber,
        [_T, 1] call CBA_fnc_formatNumber,
        [_windSpd, 1] call CBA_fnc_formatNumber
    ];
};

_depth
