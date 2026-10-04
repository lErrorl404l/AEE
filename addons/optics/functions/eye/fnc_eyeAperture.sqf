#include "..\..\script_component.hpp"

/*
Camera aperture from the adapted scene luminance (issue #141).

The eye model computes an adapted scene luminance. This maps that luminance
to the aperture value the engine expects. Higher value = wider aperture, so
the map descends: the night anchor is the wide value and the day anchor is
the narrow one.

Anchors 8 (night) and 0.2 (day) are the BI wiki setApertureNew examples.
The domain is base-10 log lux from -3 (starlight) to 5 (full sun).

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
private _nightStandard = 8;      // BI wiki setApertureNew night example
private _dayStandard = 0.2;      // BI wiki setApertureNew day example

_adaptedLux = (_adaptedLux max _minLux) min _maxLux;

private _ev = log _adaptedLux;

linearConversion [-3, 5, _ev, _nightStandard, _dayStandard, true]
