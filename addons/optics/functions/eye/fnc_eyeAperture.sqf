#include "..\..\script_component.hpp"

/*
Camera aperture from the adapted scene luminance (issue #141).

The eye model computes an adapted scene luminance. This maps that luminance
to the aperture value the engine expects. The value is LIGHT INTAKE: the
closer it is to 0, the wider the aperture and the brighter the image (BIS
wiki setAperture, Namikaze calibration). The map therefore ASCENDS from the
wide night anchor to the narrow daylight anchor.

Anchors. 8 is the BI wiki setApertureNew night example, the standard of the
[2, 8, 14] night range. 50 is the BI wiki setAperture Namikaze calibration
for daylight outdoor, the same calibration already cited in
addons/nightvision/functions/fnc_applyNVGTubeModel.sqf (50 outdoor, 30
indoor, below 20 a very bright scene suitable for night). A previous revision
used 0.2 for the day anchor, taken from the scenario-less setApertureNew
Example 1; 0.2 is close to 0, so it pinned a near-maximum intake at noon and
over-exposed the day scene. The domain is base-10 log lux from -3 (starlight)
to 5 (full sun).

The driver pins the standard with the four-element form [min, standard,
maximum, luminance] with min = standard = maximum, so the engine cannot
adapt inside a range: AEE owns the rate.

Two engine facts from the retired bridge carry forward. (1) setApertureNew
has effect only when HDR is enabled. (2) The engine resets the aperture at
mission start, so the driver must run after mission start.

Arguments:
  0: Number - adapted scene luminance, lx

Returns:
  Number - camera aperture; higher is wider.
*/

params [["_adaptedLux", 0, [0]]];

private _minLux = 0.001;         // starlight floor
private _maxLux = 100000;        // full sun
private _nightStandard = 8;      // BI wiki setApertureNew night example, the [2, 8, 14] standard
private _dayStandard = 50;       // BI wiki setAperture Namikaze calibration: 50 = daylight outdoor

_adaptedLux = (_adaptedLux max _minLux) min _maxLux;

private _ev = log _adaptedLux;

linearConversion [-3, 5, _ev, _nightStandard, _dayStandard, true]
