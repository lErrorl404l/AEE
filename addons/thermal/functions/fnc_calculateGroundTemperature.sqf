#include "..\script_component.hpp"
/*
Ground surface temperature at a position (issue #124).

The old thermal model kept ONE map-wide ground scalar (avgGroundTemp).
That is physically wrong: asphalt, concrete, soil and vegetation absorb
solar energy very differently, so a road in midday sun can sit 20+ C
above grass in the same field (asphalt albedo 0.05-0.15 vs vegetation
0.25+; Hoehne NSF, Li 2015, Kim & Lee 2024).  Every object and every
selection of an object exchanges radiation with the ground it sits on,
not a global average.

This function solves the ground surface temperature at a given
position from the SAME single-node energy balance every AEE surface
uses (Incropera, lumped capacity), with the material class taken from
the #96 detector at that position:

  q_solar + q_conv + q_rad = 0

  q_solar = alpha * G                [W/m2]  (alpha from material registry)
  q_conv  = h * (Tg - Tair)          [W/m2]  (h = 5.7 + 3.8*w, McAdams)
  q_rad   = eps * sigma * (Tg^4 - Tsky^4)    (radiation to the SKY, not
  air - the ground's upper hemisphere is the sky, Swinbank 1963)

  tau = rho * c * depth / (h)        [s]  lumped inertia of the surface
  layer (a shallow soil layer ~0.1 m exchanges heat fast; deep rock
  holds it - the depth term is the user's mass/insulation refinement
  applied to the ground)

The result is cached per [materialClass] for the tick - two objects on
the same surface share one solve, so N objects do not mean N ground
solves per frame.

Input:
  0: position (ARRAY) - world position (ASL preferred) [optional,
     defaults to the current unit's position]
  1: material class (STRING) - override; defaults to the #96
     classification at the position via surfaceType

Output: ground surface temperature in degrees C (number)
*/

params [["_pos", [], [[]]], ["_material", "", [""]]];

private _tAir = EGVAR(core,currentTemperature);
if (isNil "_tAir") exitWith { _tAir };

if (_pos isEqualTo []) then {
    private _unit = call CBA_fnc_currentUnit;
    if (!isNil "_unit") then { _pos = getPosASL _unit; };
};

// ─── Material class at the position (#96 detector) ────────────────────────
// `surfaceType` at the ground point gives the engine surface class
// (e.g. #gdtasphalt); the #96 taxonomy maps it to the physical material.
if (_material == "") then {
    if (count _pos >= 2) then {
        private _surf = surfaceType [_pos select 0, _pos select 1];
        if (_surf != "") then {
            _material = [_surf] call EFUNC(material,classifyBySurfaceType);
        };
    };
    if (_material == "") then { _material = "ground"; };
};

// ─── Wet-ground state (issue #194) ────────────────────────────────────────
// Soil moisture (0..1) comes from the existing fnc_updateSoilMoisture
// (core): rain soak capped at field capacity, FAO-56 ET0 evaporation
// scaled to the tick.  Wet soil conducts 7-8x more heat (Johansen 1975
// Kersten interpolation between dry and saturated k) and evaporates
// moisture (FAO-56 Penman-Monteith with bare-soil surface resistance).
// Both pull a wet surface below the dry-air equilibrium (Stull 2011
// wet-bulb depression: 5-8 C at 40-60% RH).  Read BEFORE the cache
// key - the moisture axis is part of the state.
private _moisture = missionNamespace getVariable [QEGVAR(core,soilMoisture), 0.2];
if !(_moisture isEqualType 0) then { _moisture = 0.2; };
_moisture = _moisture max 0 min 1;

// ─── Cache per [material, moisture] for this tick ─────────────────────────
// The equilibrium solve is cached per material+moisture pair (two
// objects on the same dry road share one solve, but a wet road and a
// dry road do NOT - the moisture axis is a real state, issue #194).
// The THERMAL STAMP offset is applied on top AFTER the cache hit - it
// is per-position (a boot print, a tyre track, a parked-car shade
// patch), so it must not be cached away.
private _cached = missionNamespace getVariable [QGVAR(groundTempCache), createHashMap];
if (isNil "_cached") then { _cached = createHashMap; };
private _cacheKey = [_material, _moisture];
private _tCached = _cached getOrDefault [_cacheKey, nil];
if (!isNil "_tCached") exitWith {
    (_tCached + ([_pos] call FUNC(getGroundStampOffset)))
};

// ─── Material properties ───────────────────────────────────────────────────
private _props = [_material] call FUNC(getMaterialThermal);
_props params ["_eps", "_alpha", "_rho", "_cp", "_k"];

// Johansen 1975 Kersten number: k = k_dry + Ke*(k_sat - k_dry).
// Material registry k is the DRY value (Incropera).  Saturated
// conductivities (de Vries/Wessolek 2022): sand 2.14, general soil
// 1.44-2.56.  Use 2.14 for the saturated end, the sand value.
private _kSat = 2.14;
private _kEff = _k + _moisture * (_kSat - _k);

private _wind = EGVAR(core,currentWind);
if !(_wind isEqualType []) then { _wind = [0, 0, 0]; };
private _windSpd = vectorMagnitude _wind;
private _solar = EGVAR(core,currentSolarFlux);
if (isNil "_solar") then { _solar = 0; };
private _overcast = overcast;

private _h = 5.7 + (3.8 * _windSpd);            // McAdams, W/m2K
private _sigma = 5.670374419e-8;             // CODATA 2022
private _tAirK = _tAir + 273.15;

// ─── Sky longwave temperature (Swinbank 1963) ─────────────────────────────
private _tSkyClear = (0.0552 * (_tAirK ^ 1.5)) - 273.15;
private _tSkyK = ((_tAir + (_tSkyClear - _tAir) * (1 - _overcast)) + 273.15);

// ─── Evaporative draw (FAO-56 Penman-Monteith, issue #194) ────────────────
// Bare-soil surface resistance: ~10 s/m wet, ~2000 dry (van de Griend
// & Owe 1994; Fuchs & Tanner 1967).  Rises steeply below ~15% vol.
private _rs = if (_moisture >= 0.5) then { 10 } else {
    10 + 1990 * (1 - _moisture / 0.5)
};
// Saturation slope (Bolton 1980 derivative, kPa/C)
private _es = 0.6112 * exp (17.67 * _tAir / (_tAir + 243.5));
private _delta = _es * 4302.645 / ((_tAir + 243.5) ^ 2);
private _ea = _es * (overcast min 1);   // ea from RH proxy (overcast 0..1)
// Aerodynamic resistance: h = rho*cp/ra  =>  ra = rho*cp/h
private _ra = (1.1614 * 1007) / (_h max 0.1);
// Net radiation available for evaporation (W/m2), bare-soil albedo 0.3.
private _rn = _alpha * _solar * 0.7;
// FAO-56 (Allen et al 1998): lambda*E = [Delta(Rn) + rho*cp*(es-ea)/ra]
// / [Delta + gamma*(1+rs/ra)], then bucketed (Manabe/Budyko):
// E = E0 while W >= 0.75*FC, E = E0*W/(0.75*FC) below.
private _gamma = 0.066;     // kPa/C psychrometric (FAO-56)
private _evapW = (_delta * _rn + (1.1614 * 1007 * (_es - _ea) / _ra)) /
    (_delta + _gamma * (1 + _rs / _ra));
_evapW = _evapW max 0;
private _wk = 0.75 * 0.25;   // Manabe bucket: WK = 0.75*FC (loam FC 0.25)
if ((_moisture * 0.25) < _wk) then {
    _evapW = _evapW * ((_moisture * 0.25) / _wk);
};

// ─── Equilibrium solve (Newton, 8 iterations - same pattern as the
//     per-selection solver) ────────────────────────────────────────────────
private _tsK = _tAirK + 5;                    // first guess
// Deep-soil temperature: the surface layer conducts to a 0.12 m
// evaporative zone (FAO-56 Ze).  Deep soil lags the surface strongly;
// use the air temperature of the PREVIOUS day as a simple anchor
// (the diurnal average - approximated by the current air temp at
// night, air temp at day, both within a few C of deep soil).
private _tDeep = _tAir;
private _zEff = 0.12;                         // evaporative zone depth (m)
for "_i" from 1 to 8 do {
    private _qSolar = _alpha * _solar;
    private _qConv = _h * (_tsK - _tAirK);
    private _qRad = _eps * _sigma * ((_tsK ^ 4) - (_tSkyK ^ 4));
    private _qCond = _kEff * ((_tDeep + 273.15) - _tsK) / _zEff;
    private _qEvap = _evapW;
    private _residual = _qSolar + _qCond - _qConv - _qRad - _qEvap;
    private _deriv = -(_h + (_kEff / _zEff) + (4 * _eps * _sigma * (_tsK ^ 3)));
    _tsK = _tsK - (_residual / _deriv);
    if (_tsK < (_tAirK - 30)) then { _tsK = _tAirK - 30; };
    if (_tsK > (_tAirK + 80)) then { _tsK = _tAirK + 80; };
};

private _ts = _tsK - 273.15;
_cached set [_cacheKey, _ts];
missionNamespace setVariable [QGVAR(groundTempCache), _cached];

// Per-position thermal stamp (boot print, tyre track, shade patch).
(_ts + ([_pos] call FUNC(getGroundStampOffset)))
