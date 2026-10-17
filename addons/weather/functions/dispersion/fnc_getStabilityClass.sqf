#include "..\..\script_component.hpp"

/*
Pasquill-Gifford atmospheric stability class (A..F) for plume dispersion.

Source: Pasquill (1961), as tabulated in Turner, "Workbook of Atmospheric
Dispersion Estimates", EPA AP-26 (1970), Table 1.  The class drives the
Briggs dispersion coefficients.  A is the most unstable class (strong
mixing, low concentration), F the most stable (weak mixing, high
concentration).

Two methods, in the standard's order of preference:

  Gradient   the measured vertical temperature gradient dT/dz (C/100 m) is
             the direct stability measure, classed by the US NRC lapse-rate
             bands (Regulatory Guide 1.23).  It is used when supplied.
  Tables     otherwise, by day, the solar radiation/delta-T (SRDT) key of
             US EPA, "Meteorological Monitoring Guidance for Regulatory
             Modeling Applications", EPA-454/R-99-005 (2000), Table 6-7:
             total solar radiation (W/m2) crossed with the 10 m wind speed;
             by night, Turner's table: cloud cover crossed with the wind.

Arguments:
  0: wind speed (NUMBER, m/s)
  1: total (global horizontal) solar radiation (NUMBER, W/m2)
  2: cloud cover (NUMBER, oktas 0..8)
  3: is day (BOOL)
  4: observed lapse rate (NUMBER, C/100 m), or 999 for "not supplied"

Returns the class letter "A".."F".
*/

params [
    ["_windSpeed", 0, [0]],
    ["_solarFlux", 0, [0]],
    ["_cloudOktas", 0, [0]],
    ["_isDay", true, [true]],
    ["_lapseRate", 999, [0]]
];

private _cls = "D";

if (_lapseRate < 900) then {
    // ── Gradient method (Turner AP-26): the measured dT/dz wins ────────────
    // Superadiabatic (< -1.9) is strongly unstable; a strong inversion
    // (> +1.5) is strongly stable.
    if (_lapseRate < -1.9) then { _cls = "A"; }
    else {
        if (_lapseRate < -1.7) then { _cls = "B"; }
        else {
            if (_lapseRate < -1.5) then { _cls = "C"; }
            else {
                if (_lapseRate < -0.5) then { _cls = "D"; }
                else {
                    if (_lapseRate <= 1.5) then { _cls = "E"; }
                    else { _cls = "F"; };
                };
            };
        };
    };
} else {
    // ── Wind band: 0 <2, 1 2-3, 2 3-5, 3 5-6, 4 >=6 m/s ───────────────────
    private _band = 4;
    if (_windSpeed < 2) then { _band = 0; }
    else {
        if (_windSpeed < 3) then { _band = 1; }
        else {
            if (_windSpeed < 5) then { _band = 2; }
            else {
                if (_windSpeed < 6) then { _band = 3; };
            };
        };
    };

    if (_isDay) then {
        // EPA SRDT key (EPA-454/R-99-005, Table 6-7).  Columns: solar
        // radiation >= 925, 675-925, 175-675, < 175 W/m2.
        private _rad = 3;
        if (_solarFlux >= 925) then { _rad = 0; }
        else {
            if (_solarFlux >= 675) then { _rad = 1; }
            else {
                if (_solarFlux >= 175) then { _rad = 2; };
            };
        };
        private _table = [
            ["A", "A", "B", "D"],
            ["A", "B", "C", "D"],
            ["B", "B", "C", "D"],
            ["C", "C", "D", "D"],
            ["C", "D", "D", "D"]
        ];
        _cls = (_table select _band) select _rad;
    } else {
        // Night table: rows = wind band (<2, 2-3, 3-5, >=5), columns =
        // [clear (<=3/8 cloud), cloudy (>=4/8 cloud)].  The standard leaves
        // the calm cloudy cell unclassified; F is used as the most stable.
        private _nightBand = _band;
        if (_nightBand > 2) then { _nightBand = 3; };
        private _col = 0;
        if (_cloudOktas >= 4) then { _col = 1; };
        private _table = [
            ["F", "F"],
            ["F", "E"],
            ["E", "D"],
            ["D", "D"]
        ];
        _cls = (_table select _nightBand) select _col;
    };
};

_cls
