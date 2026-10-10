#include "..\script_component.hpp"

/*
Scripted aircraft turbine temperature and oil pressure, from scalars.

WHY THIS FUNCTION EXISTS.  The engine exposes NO turbine temperature, NO
exhaust gas temperature, NO inter-turbine temperature, NO oil pressure, NO
start state and NO wear.  Those values are SCRIPTED from the sourced limits.
This helper maps the gas-generator speed ratio onto the two sourced bands.

THIS IS A SCRIPTED MODEL, NOT A MEASUREMENT.  The turbine temperature here is
not a measurement of any engine.  It is a declared readout between the
sourced limits.

THE MODEL.  The gas-generator speed ratio drives both values.  The spool is
the position of the current speed between the sourced idle speed and the
sourced maximum speed:

  spool     = (ng - idleNg) / (maxNg - idleNg)                 [0..1]
  idleTgtC  = maxTgtC * (idleNg / maxNg)                       [deg C]
  tgtC      = idleTgtC + (maxTgtC - idleTgtC) * spool          [deg C]
  oilKpa    = oilMinKpa + (oilMaxKpa - oilMinKpa) * spool      [kPa]

The idle turbine temperature is the sourced maximum scaled by the sourced
idle-to-maximum speed ratio, so the model introduces no new magnitude.  At
the idle speed the temperature is the idle figure and the oil pressure is
the sourced minimum.  At the maximum speed the temperature is the sourced
maximum and the oil pressure is the sourced maximum.  Both results lie
inside their sourced bands.

THE BANDS.  The turbine-temperature band is 0 to engine_max_tgt_c.  The oil
band is engine_oil_pressure_min_kpa to engine_oil_pressure_max_kpa.

Guards, each explicit:
  - A negative speed is refused with [0, 0], because a ratio cannot be
    negative.
  - A negative idle speed is refused with [0, 0].
  - A maximum speed not above the idle speed is refused with [0, 0],
    because the spool divides by the span.
  - A non-positive maximum turbine temperature is refused with [0, 0].
  - A negative minimum oil pressure is refused with [0, 0].
  - A maximum oil pressure below the minimum is refused with [0, 0],
    because the pair would interpolate backward.

Arguments:
  0:  _ng          (NUMBER) gas-generator speed ratio, >= 0
  1:  _idleNg      (NUMBER) sourced engine_idle_ng, >= 0
  2:  _maxNg       (NUMBER) sourced engine_max_ng, > idleNg
  3:  _maxTgtC     (NUMBER) sourced engine_max_tgt_c, deg C, > 0
  4:  _oilMinKpa   (NUMBER) sourced engine_oil_pressure_min_kpa, >= 0
  5:  _oilMaxKpa   (NUMBER) sourced engine_oil_pressure_max_kpa, >= oilMin

Return Value: ARRAY - [tgtC, oilKpa], or [0, 0] when an input is unusable.
Example: [0.9, 0.4, 1.0, 900, 200, 800] call aee_mobility_fnc_calculateScriptedTgtOil
Public: No
*/

params [
    ["_ng", 0, [0]],
    ["_idleNg", 0, [0]],
    ["_maxNg", 0, [0]],
    ["_maxTgtC", 0, [0]],
    ["_oilMinKpa", 0, [0]],
    ["_oilMaxKpa", 0, [0]]
];

if (_ng < 0) exitWith { [0, 0] };
if (_idleNg < 0) exitWith { [0, 0] };
if (_maxNg <= _idleNg) exitWith { [0, 0] };
if (_maxTgtC <= 0) exitWith { [0, 0] };
if (_oilMinKpa < 0) exitWith { [0, 0] };
if (_oilMaxKpa < _oilMinKpa) exitWith { [0, 0] };

// The spool is the position of the speed between idle and maximum.
private _clampedNg = _ng max _idleNg min _maxNg;
private _spool = (_clampedNg - _idleNg) / (_maxNg - _idleNg);

// The idle temperature is the sourced maximum scaled by the sourced
// idle-to-maximum speed ratio.
private _idleTgtC = _maxTgtC * (_idleNg / _maxNg);
private _tgtC = _idleTgtC + ((_maxTgtC - _idleTgtC) * _spool);
private _oilKpa = _oilMinKpa + ((_oilMaxKpa - _oilMinKpa) * _spool);

[_tgtC, _oilKpa]
