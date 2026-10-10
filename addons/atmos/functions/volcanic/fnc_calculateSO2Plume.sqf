#include "..\..\script_component.hpp"

/*
SO2 gas plume concentration and toxicity band (model).

The gas disperses with the same Gaussian plume kernel as the ash (gas phase,
no settling).  The mass concentration is converted to a volume mixing ratio
and classified against the NIOSH exposure limits.

  ppm = (C / M) * (R * T / P) * 1e6
  M = 0.064066 kg/mol (SO2), R = 8.314 J/(mol K)

Bands: NIOSH REL TWA 2 ppm, STEL 5 ppm, IDLH 100 ppm.  The 20 ppm
bronchospasm onset is the issue's own threshold.

Sources: NIOSH Pocket Guide to Chemical Hazards, sulfur dioxide (DHHS
Publication 2005-149); issue #25.

Arguments:
  0: Downwind distance (NUMBER, m)
  1: Crosswind distance (NUMBER, m)
  2: SO2 emission rate (NUMBER, kg/s)
  3: Wind speed (NUMBER, m/s)
  4: Pasquill stability class (STRING, "A".."F")
  5: Effective plume height (NUMBER, m)
  6: Receptor height (NUMBER, m, default 1.5 breathing height)
  7: Ambient temperature (NUMBER, degrees C)
  8: Ambient pressure (NUMBER, Pa)

Return Value: HashMap
  concentrationKgM3  ground/receptor-level concentration, kg/m3
  ppm                volume mixing ratio, parts per million
  band               "none" / "rel" / "stel" / "bronchospasm" / "idlh"
  lifeThreatening    BOOL, ppm >= 100 (NIOSH IDLH)
Example: [3000, 0, 1e5, 10, "D", 5000, 1.5, 15, 101325] call aee_atmos_fnc_calculateSO2Plume
Public: No
*/

params [
    ["_downwind", 0, [0]],
    ["_crosswind", 0, [0]],
    ["_emissionRate", 0, [0]],
    ["_windSpeed", 5, [0]],
    ["_stability", "D", [""]],
    ["_plumeHeight", 0, [0]],
    ["_receptorHeight", 1.5, [0]],
    ["_tempC", 15, [0]],
    ["_pressurePa", 101325, [0]]
];

private _cKg = [_emissionRate, _windSpeed, _stability, _plumeHeight, _downwind, _crosswind, _receptorHeight]
    call FUNC(calculateGaussianPlume);

// ─── Volume mixing ratio ────────────────────────────────────────────────────
private _M = 0.064066;   // kg/mol, SO2
private _R = 8.314;      // J/(mol K)
private _T = _tempC + 273.15;
private _ppm = (_cKg / _M) * (_R * _T / _pressurePa) * 1.0e6;
_ppm = _ppm max 0;

// ─── NIOSH bands ────────────────────────────────────────────────────────────
private _band = "none";
if (_ppm >= 2) then { _band = "rel"; };           // REL TWA 2 ppm
if (_ppm >= 5) then { _band = "stel"; };          // STEL 5 ppm (irritation)
if (_ppm >= 20) then { _band = "bronchospasm"; }; // issue threshold
if (_ppm >= 100) then { _band = "idlh"; };        // NIOSH IDLH

createHashMapFromArray [
    ["concentrationKgM3", _cKg],
    ["ppm", _ppm],
    ["band", _band],
    ["lifeThreatening", _ppm >= 100]
]
