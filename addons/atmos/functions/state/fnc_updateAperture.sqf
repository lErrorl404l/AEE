#include "..\..\script_component.hpp"

/*
Camera aperture from AEE's illuminance model (issue #141).

`setApertureNew [minimum, standard, maximum, luminance]` sets the eye
accommodation aperture; the engine adapts within the range by the scene
luminance.  AEE's illuminance layer already computes the scene lux, so the
aperture follows the physics instead of a fixed engine value.

Mapping: the wiki anchors are [2, 8, 14, 0.9] at night and [0.1, 0.2, 0.3,
1] in daylight.  The standard aperture therefore falls from 8 (dark) to 0.2
(bright) as the base-10 log of lux rises from -3 to 5.  The minimum and the
maximum are the night ratios of the standard (0.25 and 1.75), so
minimum <= standard <= maximum holds for every input by construction.

REQUIREMENTS:
  - Run after mission start (BI wiki: "sleep 0.1").  The environment tick
    runs after mission start; the time guard covers a short update interval.
  - The command has effect only when HDR is enabled.

SENSOR ARBITRATION.  The naked eye and the sensor path do not want the same
exposure, so exactly one of them may drive the camera at a time:

  - Naked eye: the exposure follows the SCENE luminance, which is what this
    function computes.
  - Through NVGs or thermal: the eye looks at the tube, whose AGC holds the
    output near constant (2.8-4.2 fL) whatever the scene does.  The sensor
    modules therefore set a FIXED exposure, and a scene-derived value would
    pump up and down as the scene brightens.  That artefact is exactly what
    the fixed value exists to prevent.

The gate is `currentVisionMode`, read live.  The latched flags the sensor
modules publish (`nvgGrainActive`, `thermalActive`) are NOT safe here: they
clear only in the exit branch, so they can go stale.  `currentVisionMode` is
the engine's own state and cannot.

Reads:  QEGVAR(core,illuminanceLux)
Sets:   camera aperture (setApertureNew)
*/
if (!hasInterface) exitWith {};

// The wiki requires the command after mission start.
if (time < 0.5) exitWith {};

// A vision sensor is active: it owns the exposure.  Stand down.
private _player = call CBA_fnc_currentUnit;
if (!isNull _player && {currentVisionMode _player != 0}) exitWith {};

private _minLux = 0.001;         // starlight floor
private _maxLux = 100000;        // full sun
private _nightStandard = 8;      // wiki example at night
private _dayStandard = 0.2;      // wiki example in daylight
private _minFactor = 0.25;       // 2 / 8
private _maxFactor = 1.75;       // 14 / 8

private _lux = missionNamespace getVariable [QEGVAR(core,illuminanceLux), _minLux];
if !(_lux isEqualType 0) then { _lux = _minLux; };
_lux = (_lux max _minLux) min _maxLux;

// Base-10 log of lux spans -3 (starlight) to 5 (full sun).
private _ev = log _lux;

private _standard = linearConversion [-3, 5, _ev, _nightStandard, _dayStandard, true];
private _minimum = _standard * _minFactor;
private _maximum = _standard * _maxFactor;

// The fourth element is the reference scene luminance on the engine scale.
private _luminance = linearConversion [-3, 5, _ev, 0.9, 1, true];

setApertureNew [_minimum, _standard, _maximum, _luminance];
