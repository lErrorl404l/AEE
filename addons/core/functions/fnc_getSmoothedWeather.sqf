#include "..\script_component.hpp"
/*
 * Smoothed weather inputs (rain, overcast).
 *
 * The engine's `rain` and `overcast` variables can change ABRUPTLY: a
 * mission script sets rain to 0, the weather system clears, or a
 * transition completes.  Reading them raw every tick makes the NVG
 * display SNAP (the user report: "as soon as rain stops it snaps straight
 * away to a higher brightness").  Real weather clears over seconds to
 * minutes, not one frame.
 *
 * This mirrors the shared eye-state foundation: one EMA-smoothed value
 * per input, cached per frame, consumed by every brightness/visibility
 * system.  The time constant (~5 s) matches a weather front passing,
 * not a mission script step.
 *
 * Consumers that need INSTANT response (rain-droplet presence, rain-on-
 * optics particle gating) keep reading raw `rain` directly.  Only the
 * DIMMING/BRIGHTNESS paths consume the smoothed value, so the display
 * eases while the droplet physics still reacts immediately.
 *
 * Returns [smoothedRain, smoothedOvercast, smoothedFog], all 0..1.
 *
 * TIME CONSTANTS (from meteorology research, not guessed):
 *   rain     tau = 120 s  - rain intensity ramps over ~2-3 min at a point
 *                           (Bowler 2014; MDPI Atmosphere 2022 onset study:
 *                           cloud-to-rain onset ~17 min is the slow bound,
 *                           a point ramp 1-3 min is the display-relevant one)
 *   overcast tau = 300 s  - synoptic overcast changes over 5-10 min
 *                           (Bowler 2014; frontal passage 3-5 min)
 *   fog      tau = 900 s  - fog dissipation jumps visibility over ~15 min
 *                           (formation is slower, hours; dissipation is the
 *                           fast phase, so we use it for a display response)
 *
 * TRADE-OFF: with these physical taus a full change takes ~5 tau (10-75
 * min).  That is realistic but can feel slow in-game when a mission script
 * sets rain instantly.  The values are the PHYSICAL ones; shorten via the
 * _tau param if gameplay feel is preferred (30-60 s still removes the
 * single-frame snap).
 */
params [["_tauRain", 120], ["_tauOvercast", 300], ["_tauFog", 900]];

private _frame = diag_frameNo;
private _cache = missionNamespace getVariable [QGVAR(smoothedWeather), []];
if (count _cache >= 2 && {(_cache select 0) == _frame}) exitWith {
    _cache select 1
};

private _rawRain = rain;
if !(_rawRain isEqualType 0) then { _rawRain = 0; };
private _rawOvercast = overcast;
if !(_rawOvercast isEqualType 0) then { _rawOvercast = 0; };
private _rawFog = fog;
if !(_rawFog isEqualType 0) then { _rawFog = 0; };

private _prev = missionNamespace getVariable [QGVAR(weatherEMA), [_rawRain, _rawOvercast, _rawFog]];
if (count _prev < 3) then { _prev = [_rawRain, _rawOvercast, _rawFog]; };

private _dt = diag_deltaTime;
if (_dt > 0 && _dt < 1) then {
    private _aRain = _dt / (_dt + _tauRain);
    private _aOvercast = _dt / (_dt + _tauOvercast);
    private _aFog = _dt / (_dt + _tauFog);
    _prev = [
        (_prev select 0) + (_rawRain - (_prev select 0)) * _aRain,
        (_prev select 1) + (_rawOvercast - (_prev select 1)) * _aOvercast,
        (_prev select 2) + (_rawFog - (_prev select 2)) * _aFog
    ];
} else {
    // First frame or a huge dt (alt-tab): snap to raw to avoid a long
    // catch-up ramp.
    _prev = [_rawRain, _rawOvercast, _rawFog];
};

missionNamespace setVariable [QGVAR(weatherEMA), _prev];
missionNamespace setVariable [QGVAR(smoothedWeather), [_frame, _prev]];
_prev
