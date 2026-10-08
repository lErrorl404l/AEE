#include "..\..\script_component.hpp"
/*
 * aee_optics_fnc_mgrsMapPrecision
 *
 * Choose the MGRS digit count and the matching grid interval.  The displayed
 * scale sets the digits: the visible map span against the world size.  A view
 * at an eighth of the world or closer supports a ten-metre reference, a wider
 * view a hundred-metre one.  With no map view (a HUD or GPS readout) the world
 * size alone is the signal.
 *
 * The digit to resolution ladder is the NGA MGRS guidance (Modified February
 * 2009): 6 digits is 100 m, 8 digits is 10 m.  Map scale only LIMITS the
 * plottable precision (FM 3-25.26 chapter 4; TC 3-25.26 4-12; UK Military Map
 * Reading v2.0: 1:50,000 cannot give 8 figures, 1:25,000 can).  The scale to
 * digit thresholds have NO standard basis, so they are an engineering choice,
 * recorded UNSOURCED in ADR-023, the same grade as the anchor-box mapping.
 *
 * Arguments:
 *   0: _mapSize <NUMBER> world side length in metres (CfgWorlds mapSize)
 *   1: _span    <NUMBER> visible map span in metres, 0 when there is no view
 *
 * Return: [precision, interval]
 *   precision <NUMBER> total MGRS digit count, 6 or 8
 *   interval  <NUMBER> the matching grid step in metres, 100 or 10
 */
params [
    ["_mapSize", 0, [0]],
    ["_span", 0, [0]]
];
if !(_mapSize isEqualType 0) then { _mapSize = 0; };
if !(_span isEqualType 0) then { _span = 0; };

// The view shows an eighth of the world or less: 10 m.  Else 100 m.
private _zoom = 0;
if ((_mapSize > 0) && (_span > 0)) then { _zoom = _mapSize / _span; };

private _precision = 6;
private _interval = 100;
if (_zoom >= 8) then {
    _precision = 8;
    _interval = 10;
} else {
    // No map view: the world size alone.  UNKNOWN: no standard sets this
    // boundary; it splits the shipped worlds (Altis 30 km large; Stratis,
    // Malden, Tanoa and Enoch small).
    if ((_span <= 0) && (_mapSize > 16384)) then {
        _precision = 8;
        _interval = 10;
    };
};

[_precision, _interval]
