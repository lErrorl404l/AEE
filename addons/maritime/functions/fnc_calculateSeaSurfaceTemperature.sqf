#include "..\script_component.hpp"
/*
Estimate sea-surface temperature (issue #37).

The evaporation duct depends on the AIR-SEA temperature difference, not
on air temperature alone.  Water has high thermal inertia: the surface
layer lags the air by days and never reaches the extremes of the diurnal
cycle.  There is no engine sea-surface temperature, so this models it as
a damped blend:

    SST = w * T_air + (1 - w) * T_clim

  T_clim: latitude-seasonal climatology (tropics ~28 C, poles ~0 C,
          sinusoidal through the year, northern/southern hemisphere
          phase by mission latitude).
  w     : the air-to-sea coupling weight.  A low weight (0.4) keeps the
          sea close to its climatology (high inertia); 0.6 lets a
          sustained warm/cold spell move it.  The value is a stated
          approximation - the true SST depends on months of accumulated
          heat content, not a one-day blend - but the DIRECTION and
          MAGNITUDE of the air-sea gradient are captured, which is what
          the duct model consumes.

The air-sea difference is then (T_air - SST): positive when the air is
warmer than the sea (warm-air-over-cold-water, the classic evaporation
duct condition).

Input:  none
Output: sea-surface temperature in degC
Sets:   QEGVAR(core,seaSurfaceTemperature)
*/

private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if (isNil "_T") exitWith { 15 };

// ─── Latitude-seasonal climatology ─────────────────────────────────────────
// Mean surface temperature by latitude band (annual average, degC).
// Tropical band 28, subtropical 22, temperate 13, subpolar 5, polar 0.
// Latitudes are negative in the southern hemisphere.
private _lat = (getPosASL player) select 1;
if !(_lat isEqualType 0) then { _lat = 50 };   // default: temperate north
private _absLat = abs _lat;
// Annual-mean surface temperature by latitude band (degC): tropics 28,
// subtropical 22, temperate 13, subpolar 5, polar 0.  Band index is
// 0..4 selected by latitude thresholds.
private _bandIdx = (
    (parseNumber (_absLat >= 65)) * 4
    + (parseNumber (_absLat >= 50 && _absLat < 65)) * 3
    + (parseNumber (_absLat >= 30 && _absLat < 50)) * 2
    + (parseNumber (_absLat >= 15 && _absLat < 30)) * 1
);
private _climAnnual = [28, 22, 13, 5, 0] select _bandIdx;

// Seasonal swing: ~6 C amplitude, peak in local summer (July north,
// January south).  Months since local summer: 0 at the peak, 6 at the
// trough, so cos(phase/12*360) = +1 in local summer, -1 in winter.
private _month = date select 1;
private _localSummer = [1, 7] select (parseNumber (_lat >= 0));
private _seasonPhase = (_month - _localSummer + 12) % 12;
private _clim = _climAnnual + 6 * (cos (_seasonPhase / 12 * 360));

// ─── Air-sea coupling ─────────────────────────────────────────────────────
private _w = missionNamespace getVariable [QGVAR(seaCouplingWeight), 0.5];
if !(_w isEqualType 0) then { _w = 0.5; };
private _sst = (_w * _T) + ((1 - _w) * _clim);

missionNamespace setVariable [QEGVAR(core,seaSurfaceTemperature), _sst];

_sst
