#include "..\..\script_component.hpp"

/*
Author: AEE
Description: Green-flash intensity (0.0-1.0) for the setting or rising sun.

The green flash is the last green sliver of the sun's upper limb as it
crosses the horizon. It is not a separate light source: it is the dispersion
of atmospheric refraction magnified by a mirage (Young, SDSU). Refraction
lifts the whole disc, and dispersion lifts the green image slightly more than
the red, so the green rim is the last part to set. The red image has already
set, and haze removes the violet and blue, so only green remains.

  - Horizon refraction R(h) ~ 0.53-0.57 deg (Saemundsson and Bennett).
  - Fractional dispersion of air, d(n-1)/(n-1), ~ 0.025 (red to green).
  - Angular red-green separation at the horizon: deltaR = R(h) * 0.025.
  - The sun's limb crosses the horizon at 0.25 deg/min, so the rim shows for
    deltaR / (0.25/60) seconds, about 1-2 s.

Conditions (all must hold): the sun's upper limb within ~0.5 deg of the
horizon, a mirage (a strong refractivity gradient at the horizon), and a
clean horizon (low aerosol and low overcast).

Reads:  EGVAR(core,currentSunElevation), EGVAR(core,currentHaze),
        EGVAR(atmos,refractivityGradient)
Sets:   QGVAR(greenFlashIntensity), QGVAR(greenFlashActive),
        QGVAR(greenFlashDurationS)

Sources:
  - Young, A. T. (SDSU) "Green flashes" and "An introduction to mirages".
  - Saemundsson (1986) and Bennett (1982) atmospheric refraction formulas.
  - Issue #12 (2026-09-16) green-flash model and constants.

Arguments: None
Return Value: NUMBER: green-flash intensity 0..1
Example: [] call aee_optics_fnc_calculateGreenFlash
Public: No
*/

if (!(missionNamespace getVariable [QGVAR(greenFlashEnabled), true])) exitWith {
    missionNamespace setVariable [QGVAR(greenFlashIntensity), 0];
    missionNamespace setVariable [QGVAR(greenFlashActive), false];
    missionNamespace setVariable [QGVAR(greenFlashDurationS), 0];
    0
};

// ─── Refraction dispersion ─────────────────────────────────────────────────
// Horizon refraction and the fractional red-green dispersion of air. The
// product is the angular red-green separation; the sun's sink rate turns it
// into the rim-crossing time.
private _horizonRefractionDeg = 0.57;
private _dispersionFraction = 0.025;
private _deltaRDeg = _horizonRefractionDeg * _dispersionFraction;
private _sunSinkRateDegPerS = 0.25 / 60;
private _durationS = _deltaRDeg / _sunSinkRateDegPerS;

// ─── State ─────────────────────────────────────────────────────────────────
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _haze = missionNamespace getVariable [QEGVAR(core,currentHaze), 0];
if !(_haze isEqualType 0) then { _haze = 0; };
private _gradient = missionNamespace getVariable [QEGVAR(atmos,refractivityGradient), -39];
if !(_gradient isEqualType 0) then { _gradient = -39; };
private _overcast = overcast;
if !(_overcast isEqualType 0) then { _overcast = 0; };

// ─── Gate ──────────────────────────────────────────────────────────────────
// Upper limb within 0.5 deg of the horizon; a mirage (gradient <= -100 N/km);
// a clean horizon (haze < 0.3 and overcast < 0.3).
private _nearHorizon = (_sunElev > -1) && (_sunElev < 2);
private _mirage = _gradient <= -100;
private _clean = (_haze < 0.3) && (_overcast < 0.3);

private _intensity = 0;
if (_nearHorizon && _mirage && _clean) then {
    // Proximity of the limb to the horizon: peaks with the upper limb at the
    // horizon (sun elevation ~0.5 deg), zero at the band edges.
    private _proximity = (1 - (abs (_sunElev - 0.5) / 1.5)) max 0;
    // Mirage strength: 0 at the -100 N/km onset, 1 at -200 N/km.
    private _mirageFactor = (((-_gradient) - 100) / 100) min 1;
    // Clean horizon: full at zero haze, zero at the 0.3 limit.
    private _clearFactor = (1 - _haze / 0.3) min 1;
    _intensity = _proximity * _mirageFactor * _clearFactor * (1 - _overcast);
};
_intensity = _intensity max 0 min 1;

private _active = _intensity > 0.05;

// ─── Store ─────────────────────────────────────────────────────────────────
missionNamespace setVariable [QGVAR(greenFlashIntensity), _intensity];
missionNamespace setVariable [QGVAR(greenFlashActive), _active];
missionNamespace setVariable [QGVAR(greenFlashDurationS), [_durationS, 0] select (!_active)];

_intensity
