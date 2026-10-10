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
private _perfT0 = diag_tickTime;
params [""];

// Exposure pin test: the operator pins the engine window from the debug
// console and suspends the AGC here, so only the engine's own response is
// seen (see docs/wiki/annexes/annex-c-variable-reference.qmd).
if (missionNamespace getVariable [QGVAR(agcPinned), false]) exitWith { 0 };

// ─── THROTTLE ────────────────────────────────────────────────────────────
// This function walks EVERY solved selection and calls FUNC(calculateBandRadiance)
// for each (line ~95) to build the scene histogram.  At 10 Hz with ~50 solved
// selections that is ~500 bandRadiance calls per SECOND, which is where the
// measured 490/s came from.  The AGC window is a scene statistic that moves on a
// seconds timescale, and it is applied to the display as a gain, so recomputing
// it at 4 Hz (the paint cadence) instead of 10 Hz is invisible and cuts the cost
// by 60%.  A FORCE caller is unaffected because nothing forces the AGC.
// The one real-time clock (Pillar 1) is the AGC time base.  diag_deltaTime is
// the last rendered frame, not the pass interval, so it would make the filter
// time constant depend on the frame rate (the eye-driver defect class).
private _agcNow = missionNamespace getVariable [QEGVAR(core,simTime), diag_tickTime];
private _agcLast = missionNamespace getVariable [QGVAR(agcLastT), -99];
private _agcDt = _agcNow - _agcLast;
if (_agcDt < 0.25) exitWith { 0 };
missionNamespace setVariable [QGVAR(agcLastT), _agcNow];

// The module trace switch, resolved ONCE for the whole pass.  AEE_TRACE_ON
// expands to three namespace lookups, so the per-selection band-radiance
// calls below receive the resolved flag as an argument instead of re-reading
// it for every selection.
private _traceOn = AEE_TRACE_ON;

// The detector band (T16): the mounted device's band, default lwir.  A
// device that cannot be read keeps the LWIR default, so the no-device path
// reproduces the old LWIR result bit for bit.  getThermalDeviceProperties
// returns the LWIR default for a null unit, so a dedicated server is safe.
private _band = ([player] call FUNC(getThermalDeviceProperties)) param [6, "lwir"];
if !(_band isEqualType "") then { _band = "lwir"; };
private _bandEdges = [_band] call FUNC(resolveThermalBand);
private _lambda1M = _bandEdges select 0;
private _lambda2M = _bandEdges select 1;
// Humidity for the band sky model, and the sun elevation for the MWIR
// reflected-solar term (zero for LWIR and at night).
private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
if !(_humidity isEqualType 0) then { _humidity = 50; };
private _sunElev = missionNamespace getVariable [QEGVAR(core,currentSunElevation), -90];
if !(_sunElev isEqualType 0) then { _sunElev = -90; };
private _surfaceWetness = missionNamespace getVariable [QEGVAR(core,surfaceWetness), 0];
if !(_surfaceWetness isEqualType 0) then { _surfaceWetness = 0; };

private _selTemps = missionNamespace getVariable [QGVAR(selTemperature), -1];
if (_selTemps isEqualType 0) then {
    _selTemps = createHashMap;
    missionNamespace setVariable [QGVAR(selTemperature), _selTemps];
};
private _airTemp = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
if !(_airTemp isEqualType 0) then { _airTemp = 15; };
// The ground term in the AGC window: the position-based ground
// temperature (surfaceType - asphalt stays warmer than soil at night),
// falling back to the global average.  The operator's thermal contrast
// is set by the ground they are standing on (issue #204).
private _groundTemp = [getPosASL player] call FUNC(calculateGroundTemperature);
if !(_groundTemp isEqualType 0) then {
    _groundTemp = missionNamespace getVariable [QEGVAR(core,avgGroundTemp), _airTemp];
};
if !(_groundTemp isEqualType 0) then { _groundTemp = _airTemp; };

// Gather scene radiances: every selection's temperature and ITS OWN
// emissivity through the band-radiance model, plus the ground (the
// background every object sits against).  One 0.92 for every selection
// normalised low-emissivity metal (eps ~0.1) as if painted and shifted the
// whole window.  The fixed-window fallback (used when the scene map is
// empty, e.g. the first frame) is the radiance of -40..150 C.
private _selEps = missionNamespace getVariable [QGVAR(selEmissivity), -1];
if (_selEps isEqualType 0) then {
    _selEps = createHashMap;
    missionNamespace setVariable [QGVAR(selEmissivity), _selEps];
};
private _groundEps = (["ground"] call FUNC(getMaterialThermal)) select 0;
// A rain-wetted ground emits toward the liquid-water value (T9).
_groundEps = [_groundEps, _surfaceWetness] call FUNC(getEffectiveEmissivity);
// The AGC anchors are scene-level calibration references, not targets, so
// they carry no path length: tau = 1 (unit range).  Each selection's own
// range attenuation is applied in applySelectionThermal.  A uniformly
// distant scene is therefore not range-compensated by the AGC - a stated
// limit, pending a per-target radiance histogram.
private _tauRef = 1;
private _rads = [];
// Per-object radiance lists for Local display mode.  Grouped from the same
// key walk the scene window uses, so Local costs no extra band-radiance
// calls.  The key is "<str object>|<selection>", and a selection name never
// contains "|", so the split is unambiguous.
private _objRads = createHashMap;
// ─── Cached scene sweep ───────────────────────────────────────────────────
// The band-radiance kernel is the measured cost of this pass: the sky
// bisection it runs inside every call dominated the 9.0 ms client RPT figure.
// The scene temperatures move on 600 s time constants, so a selection's
// radiance is unchanged from pass to pass.  Hold each selection's radiance
// with the inputs it was computed from and reuse it while those inputs are
// unchanged: at a fixed scene the held value IS the freshly computed value,
// so the published window is bit-identical.  Only a real move recomputes.
// The recompute count is capped per pass, which spreads a scene-wide change
// across passes instead of stalling one frame; a key beyond the cap keeps its
// held value until a later pass.  The cap is a count, not a time, because the
// per-call dispatch dominates the arithmetic.
private _manMinC = missionNamespace getVariable [QGVAR(thermalManualMinC), -40];
private _manMaxC = missionNamespace getVariable [QGVAR(thermalManualMaxC), 120];
if !(_manMinC isEqualType 0) then { _manMinC = -40; };
if !(_manMaxC isEqualType 0) then { _manMaxC = 120; };
if (_manMaxC <= _manMinC) then { _manMaxC = _manMinC + 1; };

private _radCache = missionNamespace getVariable [QGVAR(agcSelRad), -1];
if (_radCache isEqualType 0) then {
    _radCache = createHashMap;
    missionNamespace setVariable [QGVAR(agcSelRad), _radCache];
};
// The reuse tolerances sit far below the 1 percent tail cut and the 8 percent
// dead-band, so a reused value that drifted by less than this is invisible.
// At a fixed scene the drift is zero and the reuse is exact.  The ambient and
// ground tolerances cover the environment tick and the time-integrated ground
// node stack, which move a fraction of a kelvin between AGC passes.
private _AGC_REUSE_K = 0.05;
private _AGC_REUSE_AIR_K = 0.5;
private _AGC_REUSE_GROUND_K = 0.5;
private _AGC_REUSE_OVERCAST = 0.05;
private _AGC_RECOMPUTE_CAP = 48;
// A device switch changes the band, which changes every radiance, and the
// cache entries do not carry the band.  Clear both caches when it moves so a
// new optic never reads the previous band's window.
private _bandSig = format ["%1|%2|%3", _band, _lambda1M, _lambda2M];
private _prevBandSig = missionNamespace getVariable [QGVAR(agcBandSig), ""];
if !(_prevBandSig isEqualType "") then { _prevBandSig = ""; };
if (_prevBandSig != _bandSig) then {
    _radCache = createHashMap;
    missionNamespace setVariable [QGVAR(agcSelRad), _radCache];
    missionNamespace setVariable [QGVAR(agcSceneAnchor), []];
    missionNamespace setVariable [QGVAR(agcBandSig), _bandSig];
};
private _recompute = 0;
{
    private _k = _x;
    private _t = _selTemps get _k;
    if !(_t isEqualType 0 && {finite _t}) then { _radCache deleteAt _k; continue; };
    private _eps = _selEps getOrDefault [_k, _groundEps];
    if !(_eps isEqualType 0) then { _eps = _groundEps; };
    private _entry = _radCache getOrDefault [_k, []];
    private _rad = -1;
    private _fresh = false;
    if ((_entry isEqualType []) && {(count _entry) == 6}) then {
        if ((abs ((_entry select 0) - _t) <= _AGC_REUSE_K)
            && {(_entry select 1) == _eps}
            && {(abs ((_entry select 2) - _airTemp)) <= _AGC_REUSE_AIR_K}
            && {(abs ((_entry select 3) - _groundTemp)) <= _AGC_REUSE_GROUND_K}
            && {(abs ((_entry select 4) - overcast)) <= _AGC_REUSE_OVERCAST}) then {
            _rad = _entry select 5;
            _fresh = true;
        };
    };
    if (!_fresh) then {
        if (_recompute < _AGC_RECOMPUTE_CAP) then {
            private _wSolar = [_band, _eps, _sunElev] call FUNC(calculateReflectedSolarBand);
            _rad = [_t, _eps, _airTemp, 0.5, _groundTemp, _tauRef, _airTemp, _traceOn, _lambda1M, _lambda2M, _humidity, _band, _wSolar] call FUNC(calculateBandRadiance);
            _radCache set [_k, [_t, _eps, _airTemp, _groundTemp, overcast, _rad]];
            _recompute = _recompute + 1;
        } else {
            // Cap reached: keep the held value this pass.
            if ((_entry isEqualType []) && {(count _entry) == 6}) then { _rad = _entry select 5; };
        };
    };
    if (_rad isEqualType 0 && _rad >= 0) then {
        _rads pushBack _rad;
        private _oKey = (_k splitString "|") select 0;
        private _oList = _objRads getOrDefault [_oKey, []];
        _oList pushBack _rad;
        _objRads set [_oKey, _oList];
    };
} forEach (keys _selTemps);

// The ground sample and the two manual-window anchors are scene-level
// constants for a pass.  Cache them with the inputs that define them and
// recompute only when one moves; at a fixed scene they are free.
private _anchor = missionNamespace getVariable [QGVAR(agcSceneAnchor), []];
private _anchorOk = false;
if ((_anchor isEqualType []) && {(count _anchor) == 9}) then {
    if ((abs ((_anchor select 0) - _groundTemp) <= _AGC_REUSE_GROUND_K)
        && {(_anchor select 1) == _groundEps}
        && {(abs ((_anchor select 2) - _airTemp)) <= _AGC_REUSE_AIR_K}
        && {(abs ((_anchor select 3) - overcast)) <= _AGC_REUSE_OVERCAST}
        && {(_anchor select 4) == _manMinC}
        && {(_anchor select 5) == _manMaxC}) then { _anchorOk = true; };
};
private _groundRad = 0;
private _fullMin = 0;
private _fullMax = 0;
if (_anchorOk) then {
    _groundRad = _anchor select 6;
    _fullMin = _anchor select 7;
    _fullMax = _anchor select 8;
} else {
    // The ground is the background every object sits against and the one
    // sample that is always present, even before the first selection solves.
    // Keeping it in every pass anchors the window when the per-selection
    // sample set changes.  The 1 percent tail cut is a no-op below about 50
    // samples, so this anchor is what stops the window hunting.
    private _groundWSolar = [_band, _groundEps, _sunElev] call FUNC(calculateReflectedSolarBand);
    _groundRad = [_groundTemp, _groundEps, _airTemp, 0.5, _groundTemp, _tauRef, _airTemp, _traceOn, _lambda1M, _lambda2M, _humidity, _band, _groundWSolar] call FUNC(calculateBandRadiance);
    _fullMin = [_manMinC, _groundEps, _airTemp, 0.5, _groundTemp, _tauRef, _airTemp, _traceOn, _lambda1M, _lambda2M, _humidity, _band, _groundWSolar] call FUNC(calculateBandRadiance);
    _fullMax = [_manMaxC, _groundEps, _airTemp, 0.5, _groundTemp, _tauRef, _airTemp, _traceOn, _lambda1M, _lambda2M, _humidity, _band, _groundWSolar] call FUNC(calculateBandRadiance);
    missionNamespace setVariable [QGVAR(agcSceneAnchor), [_groundTemp, _groundEps, _airTemp, overcast, _manMinC, _manMaxC, _groundRad, _fullMin, _fullMax]];
};
_rads pushBack _groundRad;

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
// is the radiance of the manual/device window, so gain 1 reproduces that
// window exactly.  The window is a setting: the device library publishes
// no span.
private _fullSpan = (_fullMax - _fullMin) max 1e-6;
// Published so the display pass can convert the radiance window to its
// equivalent temperature span for the FPN amplitude (fnc_applyThermalVision).
missionNamespace setVariable [QGVAR(agcFullSpan), _fullSpan];
// ─── Max-gain floor regime (sticky) ──────────────────────────────────────
// The window span is floor-bound at fullSpan/8 (FLIR max gain 8).  The raw
// scene range can sit ON that floor as objects heat, so a plain per-pass
// `if (raw < floor)` flips the span between the raw range and the floor and
// re-quantises every selection.  Hold the regime instead: enter the floor
// whenever the raw range falls below it, so the max-gain cap is never
// violated, and leave it only when the raw range exceeds the floor by
// _AGC_FLOOR_MARGIN (25 percent).  A range hovering at the boundary holds
// the floor, so `b` cannot jump between the two gains.  The margin is
// larger than the dead-band (1 percent) and the IIR step, so the regime
// cannot change on two adjacent passes.
private _AGC_FLOOR_MARGIN = 0.25;
private _floorSpan = _fullSpan / 8;
private _rawSpan = (_radMax - _radMin) max 0;
private _atFloor = missionNamespace getVariable [QGVAR(agcAtFloor), true];
if !(_atFloor isEqualType true) then { _atFloor = true; };
if (_rawSpan < _floorSpan) then {
    _atFloor = true;
} else {
    if (_rawSpan > _floorSpan * (1 + _AGC_FLOOR_MARGIN)) then { _atFloor = false; };
};
missionNamespace setVariable [QGVAR(agcAtFloor), _atFloor];
if (_atFloor) then {
    // Expand (or hold) the window to the floor, centred on the scene mean.
    private _mid = (_radMin + _radMax) / 2;
    private _half = _floorSpan / 2;
    _radMin = _mid - _half;
    _radMax = _mid + _half;
};

// ─── Window dead-band (steady-scene hold) ─────────────────────────────────
// The window is a scene statistic that translates with the scene mean.  A
// client run (RPT 23:30:22) measured the SETTLED floor window's min/max
// breathing over 0.87 radiance, which is 5.0 percent of the 17.37 span at
// the 8x max-gain floor.  The raw window can swing a further 1 percent (the
// accepted lags the raw by the dead-band), so the raw swing is up to about 6
// percent.  Every move re-quantised every selection and repainted the scene:
// that is the operator's shimmer.  Hold the ACCEPTED raw window until it has
// moved by more than a set fraction of its own span, then let the IIR below
// smooth the real move.  The P79 probe measures the window EXTREMES, not the
// cold band: a scene shift that moves the cold band 5 percent of the floor
// span moves the window MAX about 12.7 percent, because the band radiance is
// super-linear in temperature.  Fifteen percent is used, above that measured
// 12.7 percent, so the breathing is held, while a genuine scene move (the P79
// 40 percent shift, about 46 percent of the span) still releases.  The old 8
// percent band released on this swing; the old 1 percent band before that.
private _AGC_DEADBAND = 0.15;
private _acceptedMin = missionNamespace getVariable [QGVAR(agcAcceptMin), _radMin];
private _acceptedMax = missionNamespace getVariable [QGVAR(agcAcceptMax), _radMax];
if (!(_acceptedMin isEqualType 0) || !(_acceptedMax isEqualType 0) || _acceptedMin >= _acceptedMax) then {
    _acceptedMin = _radMin;
    _acceptedMax = _radMax;
};
private _agcBand = (_acceptedMax - _acceptedMin) * _AGC_DEADBAND;
if ((abs (_radMin - _acceptedMin) > _agcBand) || {abs (_radMax - _acceptedMax) > _agcBand}) then {
    _acceptedMin = _radMin;
    _acceptedMax = _radMax;
};
_radMin = _acceptedMin;
_radMax = _acceptedMax;
missionNamespace setVariable [QGVAR(agcAcceptMin), _acceptedMin];
missionNamespace setVariable [QGVAR(agcAcceptMax), _acceptedMax];

// ─── Per-object windows for Local display mode ────────────────────────────
// Local mode maps an object's own selections through that object's own
// radiance range, not the scene window.  The scene window is ground-anchored
// and scene-wide, so one vehicle's internal spread maps to a few percent of
// the display.  Local widens that object's contrast but DESTROYS absolute
// ordering between objects: a hot and a cold object can map to the same
// ramp.  It is therefore an opt-in mode, never the default.  The SAME
// max-gain floor as the scene window applies per object: an object whose
// spread is under _fullSpan / 8 is stretched by at most 8 times, so a
// genuinely flat object is not invented into full contrast.
private _objWindows = createHashMap;
{
    private _oList = _objRads get _x;
    if ((_oList isEqualType []) && (_oList isNotEqualTo [])) then {
        _oList sort true;
        private _oLo = _oList select 0;
        private _oHi = _oList select -1;
        // A dead-flat object has no spread: nudge the window so the mapping
        // is defined, then the cap below sets the real floor.
        if (_oHi <= _oLo) then {
            _oLo = _oLo * 0.999;
            _oHi = _oHi * 1.001;
        };
        if ((_oHi - _oLo) < (_fullSpan / 8)) then {
            private _oMid = (_oLo + _oHi) / 2;
            private _oHalf = (_fullSpan / 8) / 2;
            _oLo = _oMid - _oHalf;
            _oHi = _oMid + _oHalf;
        };
        _objWindows set [_x, [_oLo, _oHi]];
    };
} forEach (keys _objRads);
missionNamespace setVariable [QGVAR(objAgcRad), _objWindows];

// ─── IIR temporal smoothing (FLIR AGC filter) ─────────────────────────────
// n' = n * alpha + n'prev * (1 - alpha), alpha from the tick interval.
// ~0.5 s time constant: the mapping tracks the scene without hunting.
//
// The interval is the WALL-CLOCK gap since the last pass, not diag_deltaTime.
// CBA_fnc_addPerFrameHandler passes no delta, and diag_deltaTime is the last
// RENDERED FRAME duration, so the old step made the filter time constant
// depend on the frame rate (the same defect class the eye driver was fixed
// for).  The throttle guarantees _agcDt >= 0.25 s here, so the published
// window is now frame-rate independent and converged to the same value on
// every run.
private _prevMin = missionNamespace getVariable [QGVAR(agcRadMin), -1];
private _prevMax = missionNamespace getVariable [QGVAR(agcRadMax), -1];
private _firstPublication = !(_prevMin isEqualType 0) || !(_prevMax isEqualType 0) || _prevMin >= _prevMax;
if (_firstPublication) then {
    // First publication: until now the display mapped through the no-AGC
    // fallback (the manual window _fullMin.._fullMax).  Seed the IIR from
    // that same window so the gain change to the max-gain floor ramps over
    // the filter time constant instead of stepping in one frame.  This is
    // the window side of the regime stickiness: the regime can change at
    // the IIR rate, never between two adjacent passes.
    _prevMin = _fullMin;
    _prevMax = _fullMax;
};
// World-clock jump: the scene changed in one step, so snap an ESTABLISHED
// window to the new scene instead of easing over the 0.5 s filter time
// constant.  A first publication is already seeded from the manual window
// and ramps, so a jump coincident with it must NOT bypass that seed (the
// P79 first-pass contract); the snap applies only to a live window.  The one
// clock holds clockJump for a short window after a jump (fnc_updateSimClock),
// so this throttled pass cannot miss it.
if (!_firstPublication) then {
    if (missionNamespace getVariable [QEGVAR(core,clockJump), false]) then {
        _prevMin = _radMin;
        _prevMax = _radMax;
    };
};
if (_agcDt > 0) then {
    private _a = _agcDt / (_agcDt + 0.5);
    _radMin = _prevMin + (_radMin - _prevMin) * _a;
    _radMax = _prevMax + (_radMax - _prevMax) * _a;
};

// NaN guards: a NaN window would map every selection to NaN brightness.
if !(finite _radMin) then { _radMin = 0; };
if !(finite _radMax) then { _radMax = 1; };
if (_radMax <= _radMin) then { _radMax = _radMin + 1e-6; };

missionNamespace setVariable [QGVAR(agcRadMin), _radMin];
missionNamespace setVariable [QGVAR(agcRadMax), _radMax];
if (_traceOn) then {
    private _agcMs = round ((diag_tickTime - _perfT0) * 1000);
    private _agcMsg = format ["thermalAGC %1 ms | radMin %2 | radMax %3 | fullSpan %4 | air %5 C | ground %6 C | selections %7",
        _agcMs, _radMin toFixed 6, _radMax toFixed 6,
        _fullSpan toFixed 6, _airTemp, _groundTemp, count _selTemps];
    AEE_LOG_DEBUG(_agcMsg);
};

private _agcOut = [_radMin, _radMax];
_agcOut
