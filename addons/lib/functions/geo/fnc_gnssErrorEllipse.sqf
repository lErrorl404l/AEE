#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_gnssErrorEllipse
 *
 * Pure, argument-driven GNSS position-error kernel.  It reads no world, no
 * config, no player and no engine state.  It models the horizontal and
 * vertical error of a satellite fix from the dilution of precision, the user
 * equivalent range error, the atmosphere, the canopy, the urban canyon,
 * jamming and the receiver quality, and it returns the error ellipse.
 *
 * SOURCED GPS Standard Positioning Service Performance Standard, 5th edition,
 * April 2020 (gps.gov):
 *   UERE 3.6 m RMS.  App. A.4: the <= 7.0 m 95 percent SPS SIS URE standard
 *     is statistically equivalent to a <= 3.6 m RMS.
 *   Horizontal 8 m and vertical 13 m at 95 percent (App. A.4, the accuracy
 *     standard).  Their ratio 13/8 = 1.625 is the sourced vertical-to-
 *     horizontal 1-sigma ratio used below.
 *   DOP definition: sigma = DOP * UERE (App. A.8.2).
 *   R95 conversion factor 2.0 (App. A.8.2): the 2DRMS radius
 *     R95 = 2.0 * sqrt(sigmaEast^2 + sigmaNorth^2).
 *
 * UNSOURCED shapes (listed for the per-constant register):
 *   GNSS_ATMOS_PER_INDEX   atmosphere index -> sigma gain, linear
 *   GNSS_CANOPY_PER_FRAC   canopy fraction -> sigma gain, linear
 *   GNSS_URBAN_PER_FRAC    urban fraction -> sigma gain, linear
 *   GNSS_URBAN_ANISOTROPY  urban fraction -> east/north axis stretch
 *   GNSS_JAM_MAX_GAIN      full jamming -> sigma gain, on jammer^1.5
 *   GNSS_RX_MAX_PENALTY    receiver quality -> sigma gain, linear
 *   GNSS_CEP_COEFF         elliptical CEP coefficient 0.589
 *
 * Arguments:
 *   0: dop             <NUMBER> dilution of precision, 1.0 nominal
 *   1: uere            <NUMBER> user equivalent range error, metres RMS
 *   2: atmosIndex      <NUMBER> atmospheric error index, 0 to 1
 *   3: canopyFraction  <NUMBER> canopy cover, 0 to 1
 *   4: urbanFraction   <NUMBER> urban canyon cover, 0 to 1
 *   5: jamming         <NUMBER> normalised jamming power, 0 to 1
 *   6: receiverQuality <NUMBER> receiver quality, 0 to 1, 1.0 best
 *
 * Return: [sigmaEast, sigmaNorth, sigmaUp, semiMajor, semiMinor,
 *          orientation, cep, r95]
 *   The sigmas and the axes are metres.  orientation is the semi-major
 *   bearing in degrees from true north, 0 = north, 90 = east.  cep and r95
 *   are metres.
 */
params [
    ["_dop", 1.0, [0]],
    ["_uere", 3.6, [0]],
    ["_atmosIndex", 0, [0]],
    ["_canopyFraction", 0, [0]],
    ["_urbanFraction", 0, [0]],
    ["_jamming", 0, [0]],
    ["_receiverQuality", 1.0, [0]]
];

private _atmosIndexC = ((_atmosIndex) max 0) min 1;
private _canopy = ((_canopyFraction) max 0) min 1;
private _urban = ((_urbanFraction) max 0) min 1;
private _jam = ((_jamming) max 0) min 1;
private _rx = ((_receiverQuality) max 0) min 1;

// Environmental sigma gain.  Every coefficient here is UNSOURCED.
private _atmosPerIndex = 0.5;                            // UNSOURCED
private _canopyPerFrac = 1.0;                            // UNSOURCED
private _urbanPerFrac = 1.5;                             // UNSOURCED
private _jamMaxGain = 20;                                // UNSOURCED
private _rxMaxPenalty = 2;                               // UNSOURCED
private _atmosGain = 1 + (_atmosIndexC * _atmosPerIndex);
private _canopyGain = 1 + (_canopy * _canopyPerFrac);
private _urbanGain = 1 + (_urban * _urbanPerFrac);
private _jamGain = 1 + ((_jam ^ 1.5) * _jamMaxGain);
private _rxGain = 1 + ((1 - _rx) * _rxMaxPenalty);
private _envGain = _atmosGain * _canopyGain * _urbanGain * _jamGain * _rxGain;

// The DOP definition: DOP * UERE is the 1-sigma horizontal error.
private _sigmaHorizontal = _dop * _uere * _envGain;

// The 95 percent vertical and horizontal standards give the sourced
// vertical-to-horizontal 1-sigma ratio 13/8.
private _verticalRatio = 13 / 8;
private _sigmaUp = _sigmaHorizontal * _verticalRatio;

// Urban canyon multipath runs along the street walls, so it stretches the
// east-west axis.  The stretch is UNSOURCED.
private _urbanAnisotropy = 2;                            // UNSOURCED
private _anisotropy = 1 + (_urban * _urbanAnisotropy);
private _sigmaEast = _sigmaHorizontal * _anisotropy;
private _sigmaNorth = _sigmaHorizontal;

private _semiMajor = _sigmaEast max _sigmaNorth;
private _semiMinor = _sigmaEast min _sigmaNorth;
private _orientation = 0;
if (_sigmaEast > _sigmaNorth) then { _orientation = 90; };

// R95 is the 2DRMS radius: the sourced factor 2.0 on the horizontal DRMS.
private _drms = sqrt ((_sigmaEast * _sigmaEast) + (_sigmaNorth * _sigmaNorth));
private _r95 = 2.0 * _drms;

// Elliptical CEP approximation.  The coefficient 0.589 is UNSOURCED.
private _cepCoeff = 0.589;                               // UNSOURCED
private _cep = _cepCoeff * (_sigmaEast + _sigmaNorth);

[_sigmaEast, _sigmaNorth, _sigmaUp, _semiMajor, _semiMinor, _orientation, _cep, _r95]
