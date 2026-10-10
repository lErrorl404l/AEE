#include "..\..\script_component.hpp"

/*
IR seeker detection range (pure).

The point-source (unresolved-target) infrared range equation:

    R_det = sqrt( J * tau / (NEFD * SNR_min) )

    J        contrast radiant intensity of the target, W/sr
    tau      band-averaged atmospheric transmission, 0..1
    NEFD     noise-equivalent flux density of the seeker, W/m2
    SNR_min  detection signal-to-noise ratio (a system threshold, not a
             physical constant)

J is the IN-BAND contrast radiant intensity: the target's radiant intensity
minus the background's, over the seeker's band.  It is NOT the display
contrast factor fnc_calculateThermalContrast publishes, which is a
dimensionless display-degradation term.  A caller builds J from the band
radiance the solver already computes (fnc_calculateBandRadiance) times the
projected area and the emissivity, then passes it here.

The equation holds for a POINT SOURCE (the target is unresolved).  A resolved
(extended) target is range-independent above the resolution limit and must
not use this form.  This kernel is the point-source case.

SOURCE.  Holst, "Electro-Optical Imaging System Performance", 6th ed., SPIE
Press, 2017, ISBN 9781510611023; and Holst, "A Common Sense Approach to
Thermal Imaging", SPIE Press, 2000.  The point-source range form is the
standard EO one; its exact placement in Holst was NOT verified this session,
so the FORM is cited as the EO-literature standard and marked PARTIALLY
UNSOURCED.  The NEFD and SNR_min figures are seeker datasheet properties; SNR_min is a
detection threshold set by the required Pd/Pfa, not a derived constant.  The
issue #131 range "5-10" for SNR_min is a plausible engineering band, not a
sourced value, and is recorded as such.

Arguments:
  0: _contrastRadiantIntensity (NUMBER) J, W/sr, >= 0
  1: _transmission            (NUMBER) tau, 0..1, default 1
  2: _nefd                    (NUMBER) NEFD, W/m2, > 0
  3: _snrMin                  (NUMBER) SNR_min, > 0

Return Value: NUMBER - detection range in metres.  Returns 0 when J is zero
(no contrast) and when any denominator term is not positive.
Public: No
*/

params [
    ["_contrastRadiantIntensity", 0, [0]],
    ["_transmission", 1, [0]],
    ["_nefd", 1, [0]],
    ["_snrMin", 5, [0]]
];

private _j = _contrastRadiantIntensity max 0;
if (_j <= 0) exitWith { 0 };

private _tau = (_transmission max 0) min 1;
if (_tau <= 0) exitWith { 0 };

if (_nefd <= 0) exitWith { 0 };
if (_snrMin <= 0) exitWith { 0 };

sqrt (_j * _tau / (_nefd * _snrMin))
