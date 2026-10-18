#include "..\script_component.hpp"

/*
Hearing scan rate-limit kernel.

The scan in fnc_revealSound is a full-radius nearestObjects over every man, run
once per shot, and it is reached up to the shot rate under automatic fire.  This
kernel is the throttle: a call inside the window returns false and the caller
skips the scan.  A skipped shot costs the field nothing that the engine keeps,
because reveal only raises knowledge and the next due shot re-issues the same
band while the source keeps firing.

Pure: no missionNamespace, no GVAR or EGVAR, no engine command, so the test
harness can execute it.  The rate is AI_HEARING_SCAN_RATE, a performance policy
value rather than a physical quantity.

Arguments:
  0: Number - current mission time, seconds
  1: Number - the time of the last accepted scan, seconds
  2: Number - the scan rate limit, scans per second

Returns:
  Boolean - true when the scan is due
*/

params [
    ["_now", 0, [0]],
    ["_lastScan", -1e9, [0]],
    ["_scanRate", 4, [0]]
];

((_now - _lastScan) >= (1 / (_scanRate max 0.001)))
