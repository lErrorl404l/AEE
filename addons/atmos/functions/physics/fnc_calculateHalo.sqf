#include "..\..\script_component.hpp"

/*
Author: AEE
Description: Computes the ice-crystal halo geometry and the parhelion
(sundog) offset from the hexagonal-prism minimum-deviation law and the
current ice-cloud and solar state. Results are stored in aee_atmos_halo*
mission variables.

The 22-degree and 46-degree halos are refraction minima through the
60-degree and 90-degree prism faces of hexagonal ice crystals. The angular
radius of a halo is the prism minimum deviation:

    D_min = 2 * asin( n * sin(A/2) ) - A

  - A = 60 deg (the alternate prism faces of a hexagonal column) gives the
    22-degree halo.
  - A = 90 deg (the basal faces with a prism face) gives the 46-degree halo.

Hexagonal ice refractive index, visible band (Warren and Brandt 2008, JGR
113 D14220, doi:10.1029/2007JD009216): n(red, 656 nm) = 1.306 and
n(blue, 486 nm) = 1.317. The red index bounds the sharp inner edge and the
blue index the diffuse outer edge, so the ring has a small chromatic width.

Parhelia (sundogs) sit on the 22-degree halo circle at the sun's elevation.
Their azimuth offset from the sun follows from the halo being a circle of
angular radius 22 deg about the sun:

    cos(delta_az) = ( cos(22 deg) - sin^2(elev) ) / cos^2(elev)

They spread outward as the sun rises and fade near 61 deg solar elevation
(Tape 1994, Atmospheric Halos; Cowley, atoptics.co.uk).

Sources:
  - Tape, W. (1994) Atmospheric Halos, Antarctic Research Series 64.
  - Minnaert, M. (1993) Light and Color in the Outdoors.
  - Warren, S. G. and Brandt, R. E. (2008) Optical constants of ice,
    JGR 113, D14220.
  - Cowley, L. atoptics.co.uk (parhelia geometry).

Arguments: None
Return Value: NUMBER: 22-degree halo intensity 0..1
Example: [] call aee_atmos_fnc_calculateHalo
Public: No
*/

if (!(missionNamespace getVariable [QGVAR(haloEnabled), true])) exitWith {
    missionNamespace setVariable [QGVAR(haloIntensity), 0];
    missionNamespace setVariable [QGVAR(haloActive), false];
    missionNamespace setVariable [QGVAR(halo22InnerDeg), 0];
    missionNamespace setVariable [QGVAR(halo22OuterDeg), 0];
    missionNamespace setVariable [QGVAR(halo46InnerDeg), 0];
    missionNamespace setVariable [QGVAR(halo46OuterDeg), 0];
    missionNamespace setVariable [QGVAR(sundogOffsetDeg), 0];
    missionNamespace setVariable [QGVAR(sundogActive), false];
    0
};

// ─── Ice refractive index (visible band) ──────────────────────────────────
// Warren and Brandt 2008: red 1.306, blue 1.317 at visible wavelengths.
private _nRed = 1.306;
private _nBlue = 1.317;

// ─── Minimum deviation: D_min = 2*asin(n*sin(A/2)) - A ─────────────────────
// SQF sin and asin work in degrees, so the apex half-angle and the result are
// direct. The red index bounds the inner edge, the blue index the outer edge.
private _halo22Inner = 2 * asin (_nRed * (sin 30)) - 60;    // 60 deg prism
private _halo22Outer = 2 * asin (_nBlue * (sin 30)) - 60;
private _halo46Inner = 2 * asin (_nRed * (sin 45)) - 90;    // 90 deg prism
private _halo46Outer = 2 * asin (_nBlue * (sin 45)) - 90;

// ─── Solar and cloud state ────────────────────────────────────────────────
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _overcast = overcast;
if !(_overcast isEqualType 0) then { _overcast = 0; };

// ─── Halo presence ────────────────────────────────────────────────────────
// A halo needs ice cloud between the observer and the sun. AEE has no
// ice-cloud classifier, so overcast presence is the proxy: thin cloud (low
// overcast) leaves the sun visible and the ring bright, and thick cloud
// occludes the sun, so the (1 - overcast) term dims the ring. The sun must
// be above the horizon, and the ring brightness follows the solar elevation.
private _haloIntensity = 0;
if (_sunElev > 0 && _overcast > 0.1) then {
    _haloIntensity = (1 - _overcast) * (sin _sunElev);
};
_haloIntensity = _haloIntensity max 0 min 1;
private _haloActive = _haloIntensity > 0.05;

// ─── Parhelion azimuth offset ─────────────────────────────────────────────
// cos(delta_az) = (cos 22 - sin^2(elev)) / cos^2(elev). The argument leaves
// [-1, 1] only above the parhelion vanish elevation; parhelia fade near
// 61 deg (Tape 1994), so the offset is defined only below that and the
// argument is clamped for safety.
private _sundogOffset = 0;
private _sundogActive = false;
private _sundogVanishElev = 61;
if (_sunElev > 0 && _sunElev <= _sundogVanishElev && _overcast > 0.1) then {
    private _sinElev = sin _sunElev;
    private _cosElev = cos _sunElev;
    if (_cosElev > 1e-3) then {
        private _cosAz = ((cos 22) - (_sinElev ^ 2)) / (_cosElev ^ 2);
        _cosAz = _cosAz max -1 min 1;
        _sundogOffset = acos _cosAz;
        _sundogActive = true;
    };
};

// ─── Store ────────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(haloIntensity), _haloIntensity];
missionNamespace setVariable [QGVAR(haloActive), _haloActive];
missionNamespace setVariable [QGVAR(halo22InnerDeg), _halo22Inner];
missionNamespace setVariable [QGVAR(halo22OuterDeg), _halo22Outer];
missionNamespace setVariable [QGVAR(halo46InnerDeg), _halo46Inner];
missionNamespace setVariable [QGVAR(halo46OuterDeg), _halo46Outer];
missionNamespace setVariable [QGVAR(sundogOffsetDeg), _sundogOffset];
missionNamespace setVariable [QGVAR(sundogActive), _sundogActive];

_haloIntensity
