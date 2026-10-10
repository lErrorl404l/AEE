#include "..\script_component.hpp"

/*
Nuclear EMP free field at a ground distance from the burst (issue #9).

Two burst geometries, each from a published model.  The kernel is pure: it
reads no engine state and returns the free field in volts per metre.

High-altitude burst (HEMP, "hemp"):
  A burst above the atmosphere (above about 30 km) deposits its gamma rays
  over a wide area and the field is roughly uniform inside the horizon
  footprint, then absent outside it.  The footprint radius is the geometric
  horizon of the burst altitude:

      r = sqrt(2 * R * h)

  Source: Glasstone & Dolan, The Effects of Nuclear Weapons, Ch XI (the
  line-of-sight horizon), and the issue's own correction of the coverage
  formula.  R = 6371 km (mean Earth radius, IUGG).  h = 100 km -> 1129 km;
  h = 400 km -> 2257 km (continental scale).
  Peak E1 field 50 kV/m (IEC 61000-2-9 / MIL-STD-464C A.5.9.1).

Ground / low burst (SREMP, "ground"):
  The source region field falls off as 1/R from a reference range:

      E = E0 * R0 / R

  Source: the issue's ground-burst model (E0 = 100 kV/m, R0 = 5 km), which
  matches the SREMP figure (> 100 kV/m) in MIL-STD-464D.  The distance is
  floored at R0 so the field never exceeds the peak.

Arguments:
  0: burstType (STRING) - "hemp" (high-altitude) or "ground" (low burst)
  1: distanceM (NUMBER) - ground distance from the burst ground zero, m
  2: burstAltM (NUMBER) - burst altitude, m (used by the HEMP footprint)
  3: peakVpm   (NUMBER) - peak field, V/m (default 50000)

Return Value: NUMBER - free field at the distance, V/m
Example: ["hemp", 2000000, 400000, 50000] call aee_core_fnc_calculateEmpField
Public: No
*/

params [
    ["_burstType", "hemp", [""]],
    ["_distanceM", 0, [0]],
    ["_burstAltM", 400000, [0]],
    ["_peakVpm", 50000, [0]]
];

private _field = 0;

if (_burstType == "hemp") then {
    // Geometric horizon of the burst altitude: r = sqrt(2 R h).
    private _earthRadiusM = 6371000;
    private _radius = sqrt (2 * _earthRadiusM * _burstAltM);
    if (_distanceM <= _radius) then {
        _field = _peakVpm;
    };
} else {
    // Source-region 1/R fall-off, floored at the reference range.
    private _refRangeM = 5000;
    _field = _peakVpm * (_refRangeM / (_distanceM max _refRangeM));
};

_field
