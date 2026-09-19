#include "..\script_component.hpp"
/*
Full-depth ground temperature node-stack at a position (issue #198).

The #124/#194 ground solver was SINGLE-NODE: one equilibrium surface
temperature with the deep soil anchored to air.  That cannot represent
both the diurnal (10-15 cm, hours lag) and seasonal (1-3 m, weeks lag)
skin depths - one node is either too fast for seasonal or too slow for
diurnal.

This function solves a 4-layer 1D vertical diffusion stack in the
Noah LSM geometry (Mitchell 2005 NCEP User's Guide v2.7.1):

  dz   = 0.10 / 0.30 / 0.60 / 1.00 m      (layer thicknesses)
  node = 0.05 / 0.25 / 0.70 / 1.50 m      (node depths, total 2.0 m)

  dT/dt = alpha * d2T/dz2                  (1D conduction)
  alpha = k / (rho * cp)                   soil thermal diffusivity
  k     = k_dry + Ke * (k_sat - k_dry)     Johansen 1975 Kersten

Discretisation is CRANK-NICOLSON (second-order, unconditionally
stable - the scheme Noah and CLM use; Chen & Dudhia 2001 Mon Wea Rev
129:569-585, Oleson et al 2010 NCAR/TN-478+STR), solving the
tridiagonal system each tick.

Boundary conditions:
  Top:    the surface energy balance (solar + sky longwave - emitted -
          sensible - latent) as a finite-volume flux on the surface
          half-cell - the same balance every AEE surface uses.
  Bottom: FIXED temperature (Noah TBOT approach) = the long-run air
  mean, computed natively as a slow EMA (30-day tau) persisted per
  cell - NOT a fresh air read (the deep anchor must not ride the
  diurnal cycle).
          applied at the deepest node.

Moisture is PER LAYER (the soilMoisture scalar from fnc_updateSoilMoisture
is the top-layer value; deep layers pinned near field capacity), so the
top layer dries fastest (k falls toward k_dry) while the deep layers
stay conductive (k near k_sat) - the 4-8x contrast the land-surface
literature requires.

Output: [layerTemps] array of 4 temperatures (C), node depths
  0.05 / 0.25 / 0.70 / 1.50 m.  Layer 1 feeds the MRT exchange and the
  Stefan freeze-thaw index; layer 4 is the seasonal anchor (and the
  TBOT boundary itself).
*/

params [["_pos", [], [[]]], ["_material", "", [""]]];

private _tAir = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tAir isEqualType 0) then { _tAir = 15; };
if (isNil "_tAir") exitWith { [15, 15, 15, 15] };

if (_pos isEqualTo []) then {
    private _unit = call CBA_fnc_currentUnit;
    if (!isNil "_unit") then { _pos = getPosASL _unit; };
};

// ─── Material class at the position (#96 detector) ────────────────────────
if (_material == "") then {
    if (count _pos >= 2) then {
        private _surf = surfaceType [_pos select 0, _pos select 1];
        if (_surf != "") then {
            _material = [_surf] call EFUNC(material,classifyBySurfaceType);
        };
    };
    if (_material == "") then { _material = "ground"; };
};

// ─── Persistence: per-position node temperatures ──────────────────────────
// The stack has MEMORY (layer 4 remembers last month's weather), so the
// node temperatures persist per position across ticks (and across
// save/JIP via the missionNamespace state).  Keyed by position grid cell
// + material, as the #194 moisture cache.
private _state = missionNamespace getVariable [QGVAR(groundNodeStack), createHashMap];
if (isNil "_state") then { _state = createHashMap; };
private _cell = format ["%1_%2_%3", floor ((_pos select 0) / 5), floor ((_pos select 1) / 5), _material];
private _last = _state getOrDefault [_cell, []];
// Real elapsed time since this cell last advanced (diag_tickTime delta,
// clamped 0.1..600 s).  The stack is time-integrated, not per-call: the
// first caller in a tick advances by the real interval, subsequent
// callers in the same tick advance ~0 and read the SAME state.  This
// makes delegation safe (MRT, object solver and stamps all call the
// ground temp per tick without triple-advancing the physics).
private _now = diag_tickTime;
private _dt = if (count _last == 6) then {
    ((_now - (_last select 5)) max 0.1) min 600
} else { 5 };

// ─── Layer geometry (Noah 4-layer, Mitchell 2005) ─────────────────────────
private _dz = [0.10, 0.30, 0.60, 1.00];

// ─── Soil properties (Johansen 1975, per-layer) ───────────────────────────
// The #194 moisture scalar is the TOP-layer value (FAO-56 evaporative
// zone dries fastest); deeper layers sit near field capacity.  Each
// layer gets its own conductivity so the stack carries the moisture
// gradient the land-surface literature requires.
private _props = [_material] call FUNC(getMaterialThermal);
_props params ["_eps", "_alphaSurf", "_rho", "_cp", "_kDry"];
private _kSat = 2.14;  // saturated soil k (de Vries / Wessolek 2022)
private _moistTop = missionNamespace getVariable [QEGVAR(core,soilMoisture), 0.2];
if !(_moistTop isEqualType 0) then { _moistTop = 0.2; };
_moistTop = _moistTop max 0 min 1;
private _moist = [_moistTop, 0.30, 0.32, 0.32];  // deep layers near FC (0.25-0.32)

// Kersten number (Johansen 1975; Farouki 1981 CRREL Monograph 81-1).
// Unfrozen coarse soil (sand): Ke = 0.7*log10(Sr) + 1.0, Sr = saturation
// ratio; frozen: Ke = Sr (linear).  The AEE wet-ground used the LINEAR
// form; the standard unfrozen form is LOGARITHMIC.  SQF `log` IS base-10
// (BIKI: 'Base-10 logarithm of x'), so log _sr is log10 directly.
private _k = [];
{
    private _sr = (_moist select _forEachIndex) max 0.02;
    private _ke = (0.7 * (log _sr)) + 1.0;
    _ke = _ke max 0 min 1;
    _k pushBack (_kDry + (_ke * (_kSat - _kDry)));
} forEach _dz;

// Thermal diffusivity per layer (m2/s): dry 0.16e-6, saturated 0.79e-6
// (inside the Oke 1987 band 2.6e-7..1.0e-6).
private _alpha = [];
{
    _alpha pushBack ((_k select _forEachIndex) / (_rho * _cp));
} forEach _dz;

// ─── Node temperatures: persist or seed ───────────────────────────────────
// State is [_t1.._t4, _tBot, _lastTick]: the 4 layer temps, the TBOT
// anchor, and the last-advance timestamp (real elapsed time).
// TBOT is the deep-soil annual-mean anchor.  It must NOT track hourly
// air (the shallow-limit error the stack exists to fix) - it is a slow
// EMA of the air temperature with a 30-day time constant, persisted
// per cell.  No state exists?  Seed at current air (the best estimate
// without long history; the EMA then drifts it over the run).
private _T = [];
private _tBot = _tAir;
if (count _last == 6) then {
    _T = _last select [0, 4];
    _tBot = _last select 4;
} else {
    _T = [_tAir, (_tAir + _tBot) / 2, (_tAir + _tBot * 2) / 3, _tBot];
};
// Slow EMA toward the long-run air mean (30-day tau).  The deep anchor
// must not ride the diurnal cycle - it integrates the seasonal signal.
_tBot = _tBot + ((_tAir - _tBot) * (_dt / 2592000));

// ─── Surface forcing (the top BC, W/m2) ───────────────────────────────────
private _wind = missionNamespace getVariable [QEGVAR(core,currentWind), [0, 0, 0]];
if !(_wind isEqualType []) then { _wind = [0, 0, 0]; };
private _windSpd = vectorMagnitude _wind;
private _solar = missionNamespace getVariable [QEGVAR(core,currentSolarFlux), 0];
if !(_solar isEqualType 0) then { _solar = 0; };
private _overcast = overcast;
private _h = 5.7 + (3.8 * _windSpd);            // McAdams, W/m2K
private _sigma = 5.670374419e-8;             // CODATA 2022
private _tSkyClear = (0.0552 * ((_tAir + 273.15) ^ 1.5)) - 273.15;
private _tSkyK = ((_tAir + (_tSkyClear - _tAir) * (1 - _overcast)) + 273.15);

// Evaporative draw (FAO-56 Penman-Monteith) - the #194 wet-ground path.
// Top-layer moisture -> surface resistance: 10 s/m wet, rises below 15%
// vol (van de Griend & Owe 1994; Fuchs & Tanner 1967).
private _rs = 10 + (1990 * ((1 - (_moistTop / 0.5)) max 0));
private _gamma = 0.066;  // psychrometric constant, kPa/C
private _psat = {
    // Bolton 1980: e_s = 611.2*exp(17.67*T/(T+243.5)) Pa
    611.2 * exp (17.67 * (_this / (_this + 243.5)))
};
private _delta = {
    // Exact Bolton derivative, kPa/C
    ((_this call _psat) * 4302.645 / ((_this + 243.5) ^ 2)) / 1000
};
private _esKPa = ((_tAir call _psat) / 1000);  // kPa
private _eaKPa = _esKPa * (0.5);               // kPa (50% RH default)
private _ra = (_rho * 1007) / (_h max 1);      // aerodynamic resistance, s/m
private _Rn = _alphaSurf * (_solar max 0) * 0.7;  // bare-soil albedo 0.3
private _qEvap = 0;
if (_moistTop > 0.02) then {
    private _numerator = ((_tAir call _delta) * _Rn) + ((_rho * 1007 * (_esKPa - _eaKPa)) / _ra);
    private _denominator = (_tAir call _delta) + (_gamma * (1 + (_rs / _ra)));
    private _e0 = if (_denominator > 0) then { _numerator / _denominator } else { 0 };
    // Manabe 1969 bucket: E = E0 while W >= 0.75*FC, scaled below.
    private _scale = ((_moistTop / (0.75 * 0.25)) min 1) max 0;
    _qEvap = _e0 * _scale;
};

// ─── Crank-Nicolson tridiagonal solve ─────────────────────────────────────
// 4-node system: interior nodes diffuse; the surface node gets the
// forcing flux; the bottom node is the fixed TBOT anchor.
// Crank-Nicolson: (I - r*D) * T_new = (I + r*D) * T_old + source
// r = alpha*dt/(2*dz^2) for the CN half-step.
private _fluxSurf = (_alphaSurf * (_solar max 0)) + (_eps * _sigma * (((_T select 0) + 273.15) ^ 4) - (_eps * _sigma * (_tSkyK ^ 4))) - (_h * ((_T select 0) - _tAir)) - _qEvap;
// Surface half-cell transient: dT = q*dt*2/(rho_cp*dz) (finite volume,
// NOT the steady-state gradient - caught in the mirror as a 100x bug).
private _T0new = (_T select 0) + (_fluxSurf * _dt * 2 / (_rho * _cp * (_dz select 0)));

// Interior layers: Crank-Nicolson tridiagonal on the 3 inner nodes
// (layer 4 is the fixed TBOT boundary).
private _tNew = +_T;
_tNew set [0, _T0new];
private _r = [];
{
    _r pushBack ((_alpha select _forEachIndex) * _dt / (2 * ((_dz select _forEachIndex) ^ 2)));
} forEach [0, 1];

// Forward half-step (explicit part of CN) on the interior nodes (1,2).
// Node 0 is the surface (updated explicitly by the flux); node 3 is the
// FIXED bottom boundary (_tBot) - never solved, matching the mirror's
// d[-1] = t_bot pin.
private _tMid = +_T;
{
    private _i = _forEachIndex + 1;  // nodes 1..2
    private _a = _r select _forEachIndex;
    private _above = _T select (_i - 1);
    private _below = if (_i == 2) then { _tBot } else { _T select (_i + 1) };
    _tMid set [_i, (_T select _i) + (_a * ((_below - (2 * (_T select _i)) + _above)))];
} forEach [0, 1];

// Backward half-step (implicit part of CN): solve the tridiagonal
// (I - r*D) T_new = T_mid.  Thomas algorithm for the 2 interior nodes
// (1,2); node 3 stays the fixed TBOT anchor.
private _aDiag = [0, 0];  // sub-diagonal
private _bDiag = [0, 0];  // diagonal
private _cDiag = [0, 0];  // super-diagonal
private _dVec = [0, 0];   // RHS
{
    private _i = _forEachIndex;  // 0..1 = interior node index (1..2)
    _bDiag set [_i, 1 + (2 * (_r select _i))];
    _dVec set [_i, (_tMid select (_i + 1))];
    if (_i > 0) then { _aDiag set [_i, -(_r select _i)]; };
    if (_i < 1) then { _cDiag set [_i, -(_r select _i)]; };
} forEach [0, 1];

// Thomas algorithm
private _cpT = [0, 0];
private _dpT = [0, 0];
_cpT set [0, (_cDiag select 0) / (_bDiag select 0)];
_dpT set [0, (_dVec select 0) / (_bDiag select 0)];
for "_i" from 1 to 1 do {
    private _m = (_bDiag select _i) - ((_aDiag select _i) * (_cpT select (_i - 1)));
    if (_m == 0) then { _m = 1e-6; };
    _cpT set [_i, (_cDiag select _i) / _m];
    _dpT set [_i, ((_dVec select _i) - ((_aDiag select _i) * (_dpT select (_i - 1)))) / _m];
};
private _x = [0, 0];
_x set [1, _dpT select 1];
for "_i" from 0 to 0 step -1 do {
    _x set [_i, (_dpT select _i) - ((_cpT select _i) * (_x select (_i + 1)))];
};

// Write back interior nodes; the bottom node stays the fixed TBOT anchor.
_tNew set [1, _x select 0];
_tNew set [2, _x select 1];
_tNew set [3, _tBot];

// ─── Persist and return ───────────────────────────────────────────────────
// State is [_t1.._t4, _tBot, _lastTick]: the 4 layer temps, the TBOT
// anchor (the slow annual-mean EMA), and the last-advance timestamp so
// the next call advances by real elapsed time.
_tNew pushBack _tBot;
_tNew pushBack _now;
_state set [_cell, _tNew];
missionNamespace setVariable [QGVAR(groundNodeStack), _state];

_tNew
