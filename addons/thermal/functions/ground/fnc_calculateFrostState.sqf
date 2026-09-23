#include "..\..\script_component.hpp"
/*
Frost and ice phase-change state at a ground position (issue #195).

The node-stack surface node (layer 1) solves the diurnal temperature
wave with moisture-dependent conductivity and evaporative draw.  This
function adds the PHASE-CHANGE tier on top of that surface:

  1. FREEZING PIN: a wet film on the surface pins at 0C while it
     releases latent heat of fusion (334 kJ/kg, IAPWS-95 333.55,
     Incropera 333.7).  The pin holds until the film mass is consumed
     (m'' = q_net * dt / L_f), then the surface is released to
     continue cooling.  Mirrors the melt path: freezing is the
     endothermic mirror with latent heat RELEASED.
  2. FROST DEPOSITION: vapour deposits directly as frost when the
     surface sits below the FROST POINT (ice saturation, Magnus over
     ice: ln e_i = ln 611.2 + 22.46*t/(272.62+t) - the frost point is
     ~0.6C higher than the dew point at -5C because ice saturation
     pressure is lower than supercooled water).  Growth rate
     m''_dep = h_m * (rho_v,air - rho_v,sat_ice) with h_m from the
     Lewis relation, capped to the Leoni 2016 band (0.1..3 mm/h).
  3. FROST EMISSIVITY: frost is a near-blackbody (0.94..0.99, MODIS
     UCSB Emissivity Library; CESM 0.97 snow) - HIGHER than bare soil
     (0.90..0.95), so a frosted surface radiates more and cools
     harder, and the LWIR contrast the FLIR path reads changes.

State is per grid cell (same 5m grid as the node stack), persisted in
GVAR(frostState) as [filmMass_kg_m2, frostDepth_mm, lastTick].  A film
is seeded by rain (rain command) or wet ground; the phase-change pin
only engages when BOTH the surface is at/below 0C AND film mass > 0.

Input:
  0: position (ARRAY, ASL)
  1: surface temperature (NUMBER, deg C) - the node-stack layer 1
  2: air temperature (NUMBER, deg C)
  3: wind speed (NUMBER, m/s)
  4: humidity (NUMBER, 0..1 fraction)
  5: rain (NUMBER, 0..1 engine rain command)

Output: [surfaceTempAdjusted, frostEmissivityFlag]
  - surfaceTempAdjusted: 0C while the pin holds, else the input temp
  - frostEmissivityFlag: 1 when frost is present (depth > 0), else 0
*/

params [
    ["_pos", [], [[]]],
    ["_tSurf", 0, [0]],
    ["_tAir", 0, [0]],
    ["_windSpd", 0, [0]],
    ["_rh", 0.5, [0]],
    ["_rain", 0, [0]]
];

// ─── Constants (sourced) ───────────────────────────────────────────────────
private _lFus = 334e3;                 // J/kg, latent heat of fusion (IAPWS-95)
private _sigma = 5.670374419e-8;       // W/m2K4, Stefan-Boltzmann (CODATA 2022)

// ─── Per-position frost state (persisted) ──────────────────────────────────
// [_filmMass_kg_m2, _frostDepth_mm, _lastTick].  The 5m grid cell key
// matches the node stack so both share one position identity.
private _state = missionNamespace getVariable [QGVAR(frostState), createHashMap];
if (isNil "_state") then { _state = createHashMap; };
// The cell key indexes the position unconditionally, so a caller that
// passes an empty array would raise a zero divisor. Guard rather than
// assume the caller always supplies one.
if (count _pos < 2) then { _pos = [0, 0, 0]; };
private _cell = format ["%1_%2", floor ((_pos select 0) / 5), floor ((_pos select 1) / 5)];
private _last = _state getOrDefault [_cell, []];
private _filmMass = if (count _last > 0) then { _last select 0 } else { 0 };
private _frostDepth = if (count _last > 1) then { _last select 1 } else { 0 };
private _lastTick = if (count _last > 2) then { _last select 2 } else { diag_tickTime };

// ─── Elapsed time (real, clamped - same pattern as the node stack) ────────
private _dt = diag_tickTime - _lastTick;
if (_dt < 0.1) then { _dt = 0.1; };
if (_dt > 600) then { _dt = 600; };

// ─── Film mass from rain (external water, issue #193 pattern) ─────────────
// A rain film seeds the phase-change pin: 1mm rain = 1 kg/m2 film.
if (_rain > 0) then {
    _filmMass = _filmMass + (_rain * _dt / 3600 * 0.5);  // ~0.5 mm/h at full rain
};

// ─── Saturation pressures ──────────────────────────────────────────────────
// Magnus over WATER (Bolton 1980, Pa) and over ICE (Pa, frost point).
private _esWater = 611.2 * exp (17.67 * _tAir / (_tAir + 243.5));
private _ea = _esWater * (_rh min 1);
// Ice saturation at the SURFACE (Magnus over ice - the frost condition).
private _esIceSurf = 611.2 * exp (22.46 * _tSurf / (272.62 + _tSurf));

// ─── Phase-change pin: surface at 0C while film releases latent heat ──────
// Freezing is the endothermic mirror of melting.  If the surface would
// sit below 0C AND a film exists, the surface pins at 0C until the
// film is consumed: dm'' = -q_net * dt / L_f.
private _tSurfAdjusted = _tSurf;
if (_filmMass > 0 && _tSurf < 0) then {
    // Net cooling flux at the pinned 0C surface: convection + radiation
    // to the sky, minus any solar gain.  Radiation against the clear
    // night sky drives the pin.
    private _h = 5.7 + (3.8 * _windSpd);           // McAdams, W/m2K
    private _tSkyClear = (0.0552 * ((_tAir + 273.15) ^ 1.5)) - 273.15;
    private _tSkyK = (_tSkyClear + 273.15);
    private _qConv = _h * (0 - _tAir);             // surface pinned at 0C
    private _qRad = 0.97 * _sigma * ((273.15 ^ 4) - (_tSkyK ^ 4));
    private _qNet = _qConv + _qRad;                // W/m2, negative = cooling
    if (_qNet < 0) then {
        private _dm = (-_qNet) * _dt / _lFus;      // kg/m2 released
        _filmMass = _filmMass - _dm;
        if (_filmMass <= 0) then {
            _filmMass = 0;
        } else {
            _tSurfAdjusted = 0;                    // pin holds
        };
    };
};

// ─── Frost deposition (Magnus over ice frost point) ───────────────────────
// Frost deposits when the surface is below the FROST POINT: the ice
// saturation pressure at the surface is below the air's vapour
// pressure.  Growth is the Lewis-relation mass transfer, capped to the
// Leoni 2016 band (0.1..3 mm/h) - the honest calibration for the
// 10-40% over-prediction of the bare Lewis relation (O'Neal 1982).
if (_tSurf <= 0 && _ea > _esIceSurf) then {
    // Vapour drive: excess air vapour over the ice-saturated surface.
    private _rhoVair = _ea / (461.5 * (_tAir + 273.15));        // kg/m3
    private _rhoVIce = _esIceSurf / (461.5 * (_tSurf + 273.15));
    private _hE = 16.5 * (5.7 + (3.8 * _windSpd));              // Lewis
    private _hM = _hE / (1.1614 * 1007);                        // m/s
    private _growth = (_hM * (_rhoVair - _rhoVIce)) * _dt * 1000;  // mm
    if (_growth > 0) then {
        _growth = _growth min (3.0 * _dt / 3600);               // mm/h cap
        _frostDepth = _frostDepth + _growth;
    };
} else {
    // No deposition: frost sublimes away when the surface warms or the
    // vapour drive reverses.  Simple exponential clearance (hours).
    if (_frostDepth > 0) then {
        _frostDepth = _frostDepth * exp (-_dt / 3600);
        if (_frostDepth < 0.01) then { _frostDepth = 0; };
    };
};

// ─── Emissivity flag (feeds the FLIR contrast path) ───────────────────────
// Frost is a near-blackbody (0.94..0.99) vs bare soil 0.90..0.95.  The
// flag lets the thermal contrast consumer apply the higher value.
private _frostFlag = parseNumber (_frostDepth > 0);

// ─── Persist ───────────────────────────────────────────────────────────────
_state set [_cell, [_filmMass, _frostDepth, diag_tickTime]];
missionNamespace setVariable [QGVAR(frostState), _state];

[_tSurfAdjusted, _frostFlag]
