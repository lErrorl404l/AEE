#include "..\script_component.hpp"

/*
Bounded vehicle mass estimate core (modelled, issue #117).

Pure arithmetic. This function reads no engine state. The caller supplies
the box extents, a cited density range, a calibrated fill range, and an
optional engine-power band. The function returns a bounded mass range or
the unavailable tuple. It never returns a point mass.

The model is a box volume times a fill fraction times a material density:

    V    = length * width * height                  (m3)
    low  = V * fillLow  * rhoLow                    (kg)
    high = V * fillHigh * rhoHigh                   (kg)

The width of the range carries the uncertainty. The function refuses a
range wider than _maxWidthRatio, because a wide range is not an estimate.
The function also refuses a range with no width, because a point value is
not an estimate.

The power check corroborates the geometry result. It only lowers the
confidence code or refuses the result. It never sets a mass.

Arguments:
  0:  _lengthM          (NUMBER) box length, metres, > 0
  1:  _widthM           (NUMBER) box width, metres, > 0
  2:  _heightM          (NUMBER) box height, metres, > 0
  3:  _rhoLow           (NUMBER) low material density, kg/m3, > 0
  4:  _rhoHigh          (NUMBER) high material density, kg/m3, >= _rhoLow
  5:  _fillLow          (NUMBER) low fill fraction, > 0
  6:  _fillHigh         (NUMBER) high fill fraction, >= _fillLow
  7:  _enginePower      (NUMBER) engine power value, band units, >= 0
  8:  _pwrEnabled       (NUMBER) 1 to use the power check, else 0
  9:  _pwrLow           (NUMBER) low power-to-weight band bound, > 0
  10: _pwrHigh          (NUMBER) high power-to-weight band bound, > _pwrLow
  11: _pwrHardFactor    (NUMBER) hard rejection factor, > 0
  12: _maxWidthRatio    (NUMBER) maximum high/low ratio, > 0
  13: _materialNarrowed (NUMBER) material signal code, from the wrapper:
        0 default density class used
        1 exactly one declared material class used
        2 declared material classes disagreed, default used
        3 only the ground residual class matched, its density is not used
      Any other value is treated as code 0.

Return Value: ARRAY [lowKg, highKg, methodCode, assumptionMask,
confidenceCode, statusCode]
  methodCode      0 none, 1 geometry_material, 2 geometry_material_power
  confidenceCode  0 none, 1 low, 2 medium, 3 reserved for a calibrated
                  and power-confirmed estimate
  statusCode      0 unavailable, 1 estimated
  assumptionMask  sum of distinct bits:
                  1    geometry_box
                  2    box_includes_mirrors
                  4    material_declared
                  8    material_class_default
                  16   density_cited
                  32   fill_calibrated
                  64   power_disabled
                  128  power_in_band
                  256  power_out_band
                  512  residual_ground_not_trusted
                  1024 material_disagreement
  The unavailable tuple carries a zero mask, because no assumption
  supports a result that was not produced.

Example: [4.5, 1.8, 1.4, 7100, 7850, 0.05, 0.12, 0, 0, 0, 0, 2, 6, 0] call aee_mobility_fnc_estimateVehicleMassCore
Public: No
*/

params [
    ["_lengthM", 0, [0]],
    ["_widthM", 0, [0]],
    ["_heightM", 0, [0]],
    ["_rhoLow", 0, [0]],
    ["_rhoHigh", 0, [0]],
    ["_fillLow", 0, [0]],
    ["_fillHigh", 0, [0]],
    ["_enginePower", 0, [0]],
    ["_pwrEnabled", 0, [0]],
    ["_pwrLow", 0, [0]],
    ["_pwrHigh", 0, [0]],
    ["_pwrHardFactor", 2, [0]],
    ["_maxWidthRatio", 6, [0]],
    ["_materialNarrowed", 0, [0]]
];

// Fail closed on a geometry, density, fill or bound defect. An inverted
// range, a zero value and a negative value all refuse the result.
private _geometryOk = (_lengthM > 0) && (_widthM > 0) && (_heightM > 0);
private _densityOk = (_rhoLow > 0) && (_rhoHigh > 0) && (_rhoLow <= _rhoHigh);
private _fillOk = (_fillLow > 0) && (_fillHigh > 0) && (_fillLow <= _fillHigh);
private _boundOk = _maxWidthRatio > 0;

if !(_geometryOk && _densityOk && _fillOk && _boundOk) exitWith {
    [0, 0, 0, 0, 0, 0]
};

private _volume = _lengthM * _widthM * _heightM;
private _low = _volume * _fillLow * _rhoLow;
private _high = _volume * _fillHigh * _rhoHigh;

if (_low <= 0) exitWith { [0, 0, 0, 0, 0, 0] };
if (_high <= 0) exitWith { [0, 0, 0, 0, 0, 0] };

// A point mass is not a bounded estimate.
if (_high <= _low) exitWith { [0, 0, 0, 0, 0, 0] };

// A range wider than the cap is not an estimate.
if ((_high / _low) > _maxWidthRatio) exitWith { [0, 0, 0, 0, 0, 0] };

// Base assumptions: a bounding box that includes mirrors and protrusions,
// a cited density range and a calibrated fill range.
private _materialBits = 8;
private _confidence = 2;

if (_materialNarrowed == 1) then {
    _materialBits = 4;
};

if (_materialNarrowed == 2) then {
    _materialBits = 8 + 1024;
    _confidence = 1;
};

if (_materialNarrowed == 3) then {
    _materialBits = 8 + 512;
    _confidence = 1;
};

private _mask = 1 + 2 + 16 + 32 + _materialBits;
private _method = 1;
private _reject = 0;

private _powerActive = (_pwrEnabled > 0) && (_enginePower > 0) && (_pwrLow > 0) && (_pwrHigh > _pwrLow) && (_pwrHardFactor > 0);

if (_powerActive) then {
    private _impliedLow = _enginePower / (_high / 1000);
    private _impliedHigh = _enginePower / (_low / 1000);

    if ((_impliedHigh < (_pwrLow * _pwrHardFactor)) || (_impliedLow > (_pwrHigh * _pwrHardFactor))) then {
        _reject = 1;
    } else {
        _method = 2;

        if ((_impliedLow < _pwrLow) || (_impliedHigh > _pwrHigh)) then {
            _mask = _mask + 256;
            _confidence = (_confidence - 1) max 1;
        } else {
            _mask = _mask + 128;
        };
    };
} else {
    _mask = _mask + 64;
};

if (_reject > 0) exitWith { [0, 0, 0, 0, 0, 0] };

[_low, _high, _method, _mask, _confidence, 1]
