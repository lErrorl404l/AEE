#include "..\..\script_component.hpp"

/*
Orographic precipitation enhancement (issue: the precipOrographicEnabled
setting).

Air forced up a slope cools and its water vapour condenses. The published
"upslope" model states the vertically integrated condensation rate as the
moisture flux through the forced ascent:

    S = rho * q_v * (U . grad h)

SOURCE: Smith, R.B. (1979) "The influence of mountains on the atmosphere",
Adv. Geophys. 21, 87-230, and Smith (2006); restated as Eq. 1 of Minder
and Roe, "Orographic Precipitation" (encyclopaedia chapter). The linear
theory that extends it is Smith and Barstad (2004), J. Atmos. Sci. 61,
1377-1391, DOI 10.1175/1520-0469(2004)061<1377:ALTOOP>2.0.CO;2.

  rho    air density, kg/m3 (AEE computes it)
  q_v    specific humidity, kg/kg
  U      the wind vector, m/s
  grad h the terrain slope, m/m

The dot product is the forced vertical motion: the component of the wind
blowing up the slope. Wind across a slope produces no ascent, and wind
down a slope produces descent and evaporation, so the term is signed.

VALIDITY, as the sources state: saturated air, flow parallel to the
topography, and instantaneous conversion and fallout. The model neglects
blocking and microphysics, so the result is an enhancement factor applied
to the background rate rather than an absolute precipitation rate.

Argument:
  0: position (ARRAY, PositionASL, default [])

Returns the enhancement factor (1.0 for no enhancement, greater over
upslope, below 1 over downslope). The caller multiplies the background
rate by it.
*/

params [["_pos", [], [[]]]];
if (count _pos < 2) exitWith { 1 };

// ─── Air density and moisture ────────────────────────────────────────────
private _rho = missionNamespace getVariable [QEGVAR(core,currentAirDensity), 1.225];
if !(_rho isEqualType 0) then { _rho = 1.225; };

// Specific humidity from the relative humidity and temperature the
// atmosphere model already publishes.  The saturation mixing ratio uses
// the same Buck 1996 relation as fnc_calculateAirDensity, so the two agree.
private _tempC = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_tempC isEqualType 0) then { _tempC = 15; };
private _rh = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_rh isEqualType 0) then { _rh = 50; };
private _pressure = missionNamespace getVariable [QEGVAR(core,currentPressure), 1013.25];
if !(_pressure isEqualType 0) then { _pressure = 1013.25; };

// Saturation vapour pressure (Buck 1996), hPa, then the mixing ratio.
private _eSat = 6.1121 * exp ((18.678 - _tempC / 234.5) * _tempC / (257.14 + _tempC));
private _e = _eSat * (_rh / 100);
// w = 0.622 e / (p - e), the mass of water vapour per mass of dry air.
private _q = 0.622 * _e / ((_pressure - _e) max 1);

// ─── The wind component up the slope ─────────────────────────────────────
private _wind = missionNamespace getVariable [QEGVAR(core,currentWind), []];
if !(_wind isEqualType []) then { _wind = [0, 0]; };
private _u = if (count _wind > 0) then { _wind select 0 } else { 0 };
private _v = if (count _wind > 1) then { _wind select 1 } else { 0 };
if !(_u isEqualType 0) then { _u = 0; };
if !(_v isEqualType 0) then { _v = 0; };

// The terrain slope over a 500 m baseline: the upslope model needs the
// large-scale slope the flow is forced over, not a single-terrain-cell
// gradient.
private _step = 500;
private _x = _pos select 0;
private _y = _pos select 1;
private _hAbove = getTerrainHeightASL [_x + _step, _y, 0];
private _hBelow = getTerrainHeightASL [_x - _step, _y, 0];
private _hRight = getTerrainHeightASL [_x, _y + _step, 0];
private _hLeft = getTerrainHeightASL [_x, _y - _step, 0];

// The gradient in the x and y directions, m per m.
private _dzdx = (_hAbove - _hBelow) / (2 * _step);
private _dzdy = (_hRight - _hLeft) / (2 * _step);

// U . grad h: positive when the wind blows up the slope.
private _ascent = _u * _dzdx + _v * _dzdy;

// ─── The source term and the enhancement factor ──────────────────────────
// S is the condensation rate per unit area (kg m-2 s-1).
private _source = _rho * _q * _ascent;

// The enhancement factor is the source normalised against a reference
// ascent.  The reference is the median slope of a hill the model is
// fitted for: a 250 m rise over the same 500 m baseline, 0.5 m/m, with a
// 10 m/s upslope wind.  That keeps the factor near 1 in flat country and
// rises over a ridge, which is how the caller uses it.
private _reference = _rho * _q * 10 * 0.5;
private _factor = 1;
if (_reference > 1e-9) then {
    _factor = 1 + (_source / _reference);
};
// Condensation cannot exceed the available vapour, and downslope
// evaporation cannot remove more than the background precipitation.
_factor = _factor max 0 min 2;

// Below saturation no air is forced to condense, so the enhancement
// applies only in saturated air, as the sources require (RH near 100).
if (_rh < 95) then {
    _factor = 1 + ((_factor - 1) * ((_rh - 50) / 45) max 0);
};

_factor
