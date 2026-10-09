#include "..\..\script_component.hpp"
/*
Continuous thermal display palette (issue #204 rework).

The display carries ONE scalar per pixel.  Material enters the image only
through emissivity, and the band-radiance model already applies emissivity
and the reflected-sky term.  So the display is a pure function of the
normalised band position.  The palette interpolates between control points
and never reads a material class.

Default ember ramp.  The control points are the engine's own decoded
thermal colours (docs/wiki/research/engine-thermal-mechanisms.md):
  0.00 black            (0,0,0)
  0.35 dark maroon      linear mix of black and the vehicle hue
  0.55 vehicle hue      default_vehicle_ti_ca.paa (145,46,0) = (0.5686,0.1804,0)
  0.85 hot red          default_ti_ca.paa (255,0,0) = (1,0,0)
  1.00 white-hot lift   (1,1,1)
An AEE-painted object therefore matches the native StageTI red/orange of an
unpainted weapon.

Palette 1 is a grey ramp.  It is the luminance form of the ember ramp, so it
adds no new source colour.

Polarity is baked here.  In vision mode 2 the engine compiles the native TI
renderer and does not apply the ColorInversion ppEffect, so the reversed ramp
is the polarity the operator sees there.  fnc_applyThermalVision still applies
ColorInversion for the channels where ppEffects do run.

Arguments:
  0: normalised band position (NUMBER, 0..1)
  1: palette index (NUMBER, optional) - 0 ember, 1 grey
  2: polarity (NUMBER, optional) - 0 white hot, 1 black hot

Return Value:
  ARRAY - [r, g, b] in 0..1
*/
params [
    ["_n", 0, [0]],
    ["_palette", 0, [0]],
    ["_polarity", 0, [0]]
];

if !(_n isEqualType 0) then { _n = 0; };
if !(finite _n) then { _n = 0; };
_n = (_n max 0) min 1;
if (_polarity == 1) then { _n = 1 - _n; };

private _points = [
    [0.00, [0.0, 0.0, 0.0]],
    [0.35, [0.3618, 0.1148, 0.0]],
    [0.55, [0.5686, 0.1804, 0.0]],
    [0.85, [1.0, 0.0, 0.0]],
    [1.00, [1.0, 1.0, 1.0]]
];
if (_palette == 1) then {
    _points = [
        [0.0, [0.0, 0.0, 0.0]],
        [1.0, [1.0, 1.0, 1.0]]
    ];
};

// ─── Isotherm/highlight palette modes (MKK thermal_improvement,
// workshop 3753145363, functions/fnc_setThermalMaterials.sqf:112-119) ───────
// MKK offers fixed thermal highlight modes - ISOTHERM_RED/GREEN/YELLOW/
// MAGENTA and PALETTE_SEPIA - that paint hot bodies in one hue.  MKK renders
// them with raster faces (.paa) that AEE cannot ship, so each mode is a
// procedural two-tone isotherm in the MKK base colour: below the AGC window
// midpoint the body stays cold (black), at or above it the body takes the
// base hue.  The threshold IS the AGC window: _n is already normalised over
// the window by the caller, so 0.5 is the window midpoint.  The hue values
// are MKK's own _getHighlightBaseColor table, numbers only, no asset.
if (_palette >= 2) exitWith {
    private _base = ([
        [0, 0, 0],
        [0, 0, 0],
        [1, 0.10, 0.08],   // ISOTHERM_RED
        [0.10, 1, 0.12],   // ISOTHERM_GREEN
        [1, 0.82, 0.10],   // ISOTHERM_YELLOW
        [1, 0.10, 1],      // ISOTHERM_MAGENTA
        [1, 0.52, 0.20]    // PALETTE_SEPIA
    ] select (_palette min 6));
    if (_n < 0.5) then { _base = [0, 0, 0]; };
    _base
};

private _lo = _points select 0;
private _hi = _points select -1;
{
    if (_n >= (_x select 0)) then { _lo = _x; };
} forEach _points;
{
    if (_n <= (_x select 0)) exitWith { _hi = _x; };
} forEach _points;

private _cLo = _lo select 1;
private _cHi = _hi select 1;
private _span = ((_hi select 0) - (_lo select 0)) max 1e-6;
private _f = ((_n - (_lo select 0)) / _span) max 0 min 1;
[
    (_cLo select 0) + ((_cHi select 0) - (_cLo select 0)) * _f,
    (_cLo select 1) + ((_cHi select 1) - (_cLo select 1)) * _f,
    (_cLo select 2) + ((_cHi select 2) - (_cLo select 2)) * _f
]
