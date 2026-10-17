#include "..\..\script_component.hpp"
/*
 * aee_lib_fnc_gnssFixState
 *
 * GPS fix state from the satellites received.  Pure.
 *
 *   4 or more satellites  3D fix ("ok")
 *   3 satellites          2D fix with the height held ("degraded")
 *   fewer                 no fix ("none"); the last position is held
 * A receiver whose satellites return re-acquires as a hot start, about 1 s,
 * while its broadcast ephemeris is still valid (the 4 h fit interval of
 * IS-GPS-200), and as a cold start, about 26 s, after a longer outage
 * (u-blox NEO-M8 data sheet UBX-15031086, TTFF: hot 1 s, cold 26 s).
 *
 * Arguments:
 *   0: dt        <NUMBER> seconds since the previous call
 *   1: count     <NUMBER> satellites received (after line-of-sight blocking)
 *   2: prevState <ARRAY>  [timeSinceFix s, acquireRemaining s]; [] at first
 *
 * Return: [quality, timeSinceFix, acquireRemaining]
 */
params [["_dt", 0, [0]], ["_count", 0, [0]], ["_prevState", [], [[]]]];
private _step = _dt max 0;
private _since = 0;
private _acquire = 0;
if ((count _prevState) >= 2) then {
    _since = (_prevState select 0) max 0;
    _acquire = (_prevState select 1) max 0;
};
private _quality = "none";
if (_count >= 3) then {
    if (_since > 0 && _acquire <= 0) then {
        // Satellites back after an outage: start the time to fix.
        _acquire = [26, 1] select (_since < 14400);
    };
    _acquire = (_acquire - _step) max 0;
    if (_acquire <= 0) then {
        _quality = ["degraded", "ok"] select (_count >= 4);
        _since = 0;
    } else {
        _since = _since + _step;
    };
} else {
    _since = _since + _step;
    _acquire = 0;
};
[_quality, _since, _acquire]
