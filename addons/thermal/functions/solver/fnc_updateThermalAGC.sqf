#include "..\..\script_component.hpp"
/*
Scene-adaptive AGC for the thermal display (issue #196).

Real FLIR never maps temperature onto a fixed window.  It reads the
scene's actual radiance histogram and stretches the narrow band the
scene contains across the full display range, re-computing continuously
(FLIR Camera Adjustments app note 102-PS242-100-01).  The AGC modes are
documented:

  Linear AGC (mode used here): 8bit = m * (rad - radMin) with the slope
    computed from the scene histogram with tail rejection:
        m = 1 / (rad_100-tail% - rad_tail%)
    FLIR recommends tail rejection below 1% so real content is not
    clipped.
  AGC modes: FLIR's current guidance prefers Information-Based
    Histogram Equalization (IBHEQ) as the default; plateau histogram
    equalization was the Tau-2-generation default and remains a valid
    mode; linear AGC with tail rejection is the documented formula-exact
    form.  At this sim's per-selection granularity (a few dozen samples
    per frame) plateau/IBHEQ and linear AGC are nearly identical, so
    linear AGC with tail rejection is used - the documented, formula
    form, with the 1% tail rejection FLIR recommends.
  Max Gain (default 8): caps how much the mapping can stretch a bland
    scene.  A flat night scene with a 2 K spread cannot be stretched to
    full range: the cap holds the gain at 8, preserving the true
    "low-contrast night" look instead of inventing contrast that is not
    in the scene (FLIR: AGC cannot create contrast that does not exist).
  AGC filter: an IIR temporal filter (FLIR "Damping Factor") that
    smooths the mapping over time so it does not jump when the scene
    changes.

The mapping is computed over BAND RADIANCE (fnc_calculateBandRadiance),
not temperature - the sensor reads radiance, and the emissivity +
reflection terms in the radiance model are what make bare metal read
dark at night.

Arguments: none.  Reads the per-selection temperature state
(QGVAR(selTemperature), written by applySelectionThermal) plus the
ground temperature for the background term.  Publishes the smoothed
AGC window:

  QGVAR(agcRadMin) / QGVAR(agcRadMax) - the scene radiance window
    (W/m2/sr), tail-rejected and IIR-smoothed.  applySelectionThermal
    maps each selection's radiance through this window.

The engine-window AGC (applyEngineThermal) handles the vehicle-native
side separately; this is the per-selection side where AEE controls the
full display range.
*/
params [""];

private _selTemps = missionNamespace getVariable [QGVAR(selTemperature), createHashMap];
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
private _groundTemp = missionNamespace getVariable [QEGVAR(core,avgGroundTemp), _airTemp];
if !(_groundTemp isEqualType 0) then { _groundTemp = _airTemp; };

// Gather scene radiances: every selection's temperature through the
// band-radiance model, plus the ground (the background every object
// sits against).  The fixed-window fallback (used when the scene map is
// empty, e.g. the first frame) is the radiance of -40..150 C - the
// engine default window AEE previously hard-coded.
private _rads = [];
{
    private _t = _x;
    if !(_t isEqualType 0 && {finite _t}) then { continue; };
    // Emissivity for the radiance: use the selection's material where
    // possible; default 0.92 (painted surface) otherwise.
    _rads pushBack ([_t, 0.92, _airTemp, 0.5, _groundTemp] call FUNC(calculateBandRadiance));
} forEach (values _selTemps);
if (_rads isNotEqualTo []) then {
    _rads pushBack ([_groundTemp, 0.92, _airTemp, 0.5, _groundTemp] call FUNC(calculateBandRadiance));
};

// ─── Tail rejection (FLIR: <1% so real content is not clipped) ────────────
// Sort the radiances, cut the top and bottom 1%, and take the window.
// With fewer than ~50 samples the 1% cut is <1 sample; keep at least the
// min/max in that case so the window is never empty.
private _radMin = -1;
private _radMax = -1;
if (_rads isNotEqualTo []) then {
    _rads sort true;
    private _cut = floor ((count _rads) * 0.01) max 0;
    private _lo = _rads select (_cut min ((count _rads) - 1));
    private _hi = _rads select (((count _rads) - 1 - _cut) max 0);
    // Guard a zero/negative spread: a dead-flat scene must still render
    // (mid-grey, per real FLIR low-contrast behaviour).
    if (_hi > _lo) then {
        _radMin = _lo;
        _radMax = _hi;
    } else {
        _radMin = _lo * 0.999;
        _radMax = _hi * 1.001;
    };
};

// ─── Max gain cap (FLIR default 8) ────────────────────────────────────────
// The mapping gain is spread_display / spread_scene.  Cap the total
// stretch so a bland scene does not invent contrast.  The display spread
// is the radiance of a 190 K window (the engine's -40..150 C span) so a
// gain of 1 reproduces the old fixed window exactly.
private _fullSpan = ([150, 0.92, _airTemp, 0.5, _groundTemp] call FUNC(calculateBandRadiance))
    - ([(-40), 0.92, _airTemp, 0.5, _groundTemp] call FUNC(calculateBandRadiance));
_fullSpan = _fullSpan max 1e-6;
if (_radMax - _radMin < _fullSpan / 8) then {
    // Scene spread is under the max-gain floor: expand the window to the
    // floor (gain exactly 8), centred on the scene mean.
    private _mid = (_radMin + _radMax) / 2;
    private _half = (_fullSpan / 8) / 2;
    _radMin = _mid - _half;
    _radMax = _mid + _half;
};

// ─── IIR temporal smoothing (FLIR AGC filter) ─────────────────────────────
// n' = n * alpha + n'prev * (1 - alpha), alpha from the tick interval.
// ~0.5 s time constant: the mapping tracks the scene without hunting.
private _prevMin = missionNamespace getVariable [QGVAR(agcRadMin), _radMin];
private _prevMax = missionNamespace getVariable [QGVAR(agcRadMax), _radMax];
if (!(_prevMin isEqualType 0) || !(_prevMax isEqualType 0) || _prevMin >= _prevMax) then {
    _prevMin = _radMin;
    _prevMax = _radMax;
};
if (diag_deltaTime > 0) then {
    private _a = diag_deltaTime / (diag_deltaTime + 0.5);
    _radMin = _prevMin + (_radMin - _prevMin) * _a;
    _radMax = _prevMax + (_radMax - _prevMax) * _a;
};

// NaN guards: a NaN window would map every selection to NaN brightness.
if !(finite _radMin) then { _radMin = 0; };
if !(finite _radMax) then { _radMax = 1; };
if (_radMax <= _radMin) then { _radMax = _radMin + 1e-6; };

missionNamespace setVariable [QGVAR(agcRadMin), _radMin];
missionNamespace setVariable [QGVAR(agcRadMax), _radMax];

[_radMin, _radMax]
