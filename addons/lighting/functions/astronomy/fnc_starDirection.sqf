#include "..\..\script_component.hpp"

/*
Horizontal coordinates to a world direction unit vector.

A star's altitude and azimuth (the horizontal coordinates fnc_getStarCatalog
already computes and stores as aee_lighting_visibleStars) describe where the
star sits on the observer's celestial sphere.  The renderer converts that
pair to a world-space direction from the player each frame.

World axes follow the engine compass convention (BIKI vectorDir): x = east,
y = north, z = up.  Azimuth is measured from north, clockwise (getDir
convention), altitude is the angle above the horizon.  A star at azimuth 0
(north) and altitude 0 (horizon) therefore points at [0, 1, 0]; at azimuth
90 (east) it points at [1, 0, 0].

SQF sin/cos take degrees, so the two angles feed them directly - a radian
conversion here would be the exact degrees-radians bug fixed in 14b8b0f.

Arguments:
  0: Number - altitude above horizon, degrees (-90..90)
  1: Number - azimuth from north, clockwise, degrees (0..360)

Returns:
  Array - unit direction vector [east, north, up].
*/

params [
    ["_altDeg", 0, [0]],
    ["_azDeg", 0, [0]]
];

private _cosAlt = cos _altDeg;

[
    (sin _azDeg) * _cosAlt,   // east
    (cos _azDeg) * _cosAlt,   // north
    sin _altDeg               // up
]
