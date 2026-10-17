#include "..\..\script_component.hpp"

/*
Snow accumulation / melt / drifting model.

Reads and writes QEGVAR(core,snowDepth_m) as a leaky integrator.

  Accretion  The frozen precipitation rate is published by the phase model
             (aee_atmos_fnc_calculatePrecipitationPhase) as liquid-water
             equivalent, mm/h.  Depth follows from the fresh-snow density:
               dDepth = SWE_m * rho_water / rho_new
             rho_new from the air temperature (Hedstrom & Pomeroy 1998,
             Hydrol. Process. 12, eq. 3):
               rho_new = 67.92 + 51.25 * exp(T / 2.59)   kg/m3, T <= 0 C
             (~68 kg/m3 dry powder at -10 C, ~119 kg/m3 at 0 C; the
             classic 10:1 ratio is 100 kg/m3).  Heavy snowfall of 2.5 mm/h
             water equivalent at -5 C is ~3.3 cm/h of snow.
  Melt       Degree-day melt above 0 C (the standard base temperature):
               melt_SWE = DDF * T,  DDF = 4 mm w.e./C/day
             (Hock 2003, J. Hydrol. 282: snow DDF 2.5-6 mm/C/day), converted
             to depth with the snowpack density (aee_persistence_slabDensity,
             300 kg/m3 default, a settled seasonal pack).
  Drift      wind > 8 m/s + snow > 5 cm -> drift intensity.

Clamped 0 - max snow depth.
Stored in QEGVAR(core,snowDepth_m) and QGVAR(snowDriftIntensity) (0-1).
*/

private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _interval = EGVAR(core,updateInterval);
if !(_interval isEqualType 0) then { _interval = 5; };
private _depth = missionNamespace getVariable [QEGVAR(core,snowDepth_m), 0];
// Kept for the melt flux below: the depth before this tick's change is
// what melted, and the depth after is what remains.
private _prevDepth = _depth;

private _maxSnowDepth = missionNamespace getVariable [QGVAR(MaxSnowDepth), 3.0];
private _rhoPack = missionNamespace getVariable [QEGVAR(persistence,slabDensity), 300];
if !(_rhoPack isEqualType 0) then { _rhoPack = 300; };
_rhoPack = _rhoPack max 50;
private _rhoWater = 1000;

if (_T isEqualType 0) then {
    // ─── Accretion: liquid-equivalent snowfall over the fresh-snow density ─
    private _sweMmH = missionNamespace getVariable [QEGVAR(core,snowfallRate), 0];
    if !(_sweMmH isEqualType 0) then { _sweMmH = 0; };
    if (_sweMmH > 0) then {
        private _rhoNew = 67.92 + 51.25 * exp ((_T min 0) / 2.59);
        private _sweM = (_sweMmH / 1000) * (_interval / 3600);
        _depth = _depth + (_sweM * _rhoWater / _rhoNew);
    };
    // ─── Melt: degree-day, water equivalent converted to pack depth ───────
    if (_T > 0) then {
        private _meltSweM = 0.004 * _T * (_interval / 86400);
        _depth = _depth - (_meltSweM * _rhoWater / _rhoPack);
    };
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
if (_T > 0 && _depth < _prevDepth) then {
    private _snowDensity = (missionNamespace getVariable [QEGVAR(persistence,slabDensity), 300]) / 1000;
    if !(_snowDensity isEqualType 0) then { _snowDensity = 0.3 };
    private _rhoSnowKgM3 = _snowDensity * 1000;
    private _lFus = 334e3;                  // J/kg, IAPWS-95
    private _meltDepthM = _prevDepth - _depth;
    private _intervalS = EGVAR(core,updateInterval);
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

if (missionNamespace getVariable [QEGVAR(diagnostics,diagnostic), false]) then {
    private _logMsg = format [
        "SnowAccum: depth=%1 m drift=%2 (T=%3 °C, wind=%4 m/s)",
        // CBA_fnc_formatNumber is [number, integerWidth, decimalPlaces]:
        // the 2nd arg is integer width, so 0.5 m showed as "00" (issue #177).
        [_depth, 0, 2] call CBA_fnc_formatNumber,
        [_drift, 0, 3] call CBA_fnc_formatNumber,
        [_T, 1] call CBA_fnc_formatNumber,
        [_windSpd, 1] call CBA_fnc_formatNumber
    ];
    AEE_LOG_INFO(_logMsg);
};

_depth
