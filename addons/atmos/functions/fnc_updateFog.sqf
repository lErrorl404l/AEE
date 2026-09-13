#include "..\script_component.hpp"

/*
Fog density from biome climate, dew-point spread, wind, and solar
burn-off, plus a radiational-fog mechanism.

Radiational fog forms on clear nights: the ground cools by long-wave
radiation loss, chilling the near-surface air to its dew point.  It
needs a clear sky (low overcast), calm wind, and moist surface air.
The fog factor ramps slowly over several ticks so it does not pop in.

Fog is globally synchronised in the engine — each client receives the
same overcast/rain/fog state from the server.  We therefore calculate
and set fog from the SERVER only, using the base biome climate rather
than per-player position.

Stored in QEGVAR(core,currentFogDensity).
*/
if (!isServer) exitWith {};

private _month = date select 1;

private _biome = EGVAR(core,biome);
if (isNil "_biome" || _biome == "") exitWith {};

private _normals = [_biome] call EFUNC(environmental,getClimateNormals);
private _tDay   = _normals select 2;
private _tNight = _normals select 3;
private _RH_arr = _normals select 4;

private _T_biome = ((_tDay select (_month - 1)) + (_tNight select (_month - 1))) / 2;
private _RH_biome = _RH_arr select (_month - 1);

// ─── Settings ─────────────────────────────────────────────────────────────
private _maxFogDensity = missionNamespace getVariable [QGVAR(maxFogDensity), 0.8];
private _interval      = missionNamespace getVariable [QEGVAR(core,updateInterval), 5];
private _rampRate      = missionNamespace getVariable [QGVAR(radFogRampRate), 0.1];
_rampRate = _rampRate * (_interval / 5);

// Dew point — full Magnus formula (Sonntag 1990, over water, -45°C to 80°C)
//   γ = ln(RH/100) + b·T/(c+T)
//   Td = c·γ / (b-γ)
//   Constants: b = 17.62, c = 243.12°C (for water)
private _ln_rh = ln (_RH_biome / 100);
private _gamma = _ln_rh + (17.62 * _T_biome / (243.12 + _T_biome));
private _Td = 243.12 * _gamma / (17.62 - _gamma);
private _spread = _T_biome - _Td;  // how far above dew point

// Cloud base erosion: overcast caps fog formation (warming suppresses fog)
private _fogDensity = 0;
if (_spread < 3) then {
    _fogDensity = (3 - _spread) / 3; // 0 at spread=3, 1 at spread=0
};

// Wind disperses fog
private _windSpeed = vectorMagnitude wind;
if (_windSpeed > 2) then {
    _fogDensity = _fogDensity * (1 - ((_windSpeed - 2) / 12) min 1);
};

// Solar burn-off between 07:00–17:00
private _hour = dayTime;
if (_hour > 7 && _hour < 17) then {
    _fogDensity = _fogDensity * (1 - ((_hour - 7) / 10) max 0);
};

// At or below dew point → persistent thick fog
if (_spread <= 0) then {
    _fogDensity = _fogDensity max 0.3;
};

// ─── Radiational fog (clear-sky, calm, moist night) ─────────────────────
// Clear night + calm wind + near-saturated surface air → ground cools
// by radiation and fog forms.  Ramp slowly so it does not pop in.
private _RH = missionNamespace getVariable [QEGVAR(core,currentHumidity), _RH_biome];
private _clearNight = (overcast < 0.2) && (_hour < 6 || _hour > 18);
private _calm = _windSpeed < 3;
private _moist = _RH > 90;

private _radFog = missionNamespace getVariable [QGVAR(radiationalFog), 0];
if (_clearNight && _calm && _moist) then {
    _radFog = (_radFog + _rampRate) min 1;
} else {
    _radFog = (_radFog - 0.2) max 0;
};
missionNamespace setVariable [QGVAR(radiationalFog), _radFog];

_fogDensity = _fogDensity max (_radFog * 0.8);

_fogDensity = _fogDensity max 0 min _maxFogDensity;
missionNamespace setVariable [QEGVAR(core,currentFogDensity), _fogDensity];
0 setFog [_fogDensity, 0.5, 0];

// ─── Engine fog forecast (trend) ─────────────────────────────────────────
// fogForecast returns [level, decay, base] — the engine's predicted fog
// state, which other modules (visibility, NVG haze) can use as a trend.
// Guard: returns [] in some contexts; fall back to current density.
private _forecast = fogForecast;
if (_forecast isEqualType [] && {count _forecast >= 3}) then {
    missionNamespace setVariable [QEGVAR(core,fogForecast), _forecast];
} else {
    missionNamespace setVariable [QEGVAR(core,fogForecast), [_fogDensity, 0.5, 0]];
};
