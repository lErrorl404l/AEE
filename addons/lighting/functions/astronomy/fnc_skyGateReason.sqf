#include "..\..\script_component.hpp"

/*
Why a night-sky feature is on or off.

The consolidated sky-state log line reports, for each feature, whether it
renders and, when it does not, which gate turned it off.  This kernel is the
one place that order is decided, so the log and the renderers cannot drift.

The caller composes the whole-sky force hook into the arguments before the
call: `skyForce` sets `_settingOn` true and `_forceOn` true.  The kernel never
reads a hook, so it stays pure and tools/tests/sqf_lite.py can execute it.

Gate order is setting, then force, then feature physics.  The thresholds match
the renderers: stars and meteors gate on sun elevation and overcast < 0.8,
the aurora adds Kp > 4, a daytime window, and the oval latitude limit, and the
Milky Way gates on the limiting magnitude.

Arguments:
  0:  String  - feature: "stars", "meteors", "aurora" or "milkyway"
  1:  Boolean - setting enabled (dynamicStars and so on)
  2:  Boolean - force hook active
  3:  Number  - sun elevation, degrees
  4:  Number  - overcast, 0..1
  5:  Number  - Kp geomagnetic index
  6:  Number  - day time, hours
  7:  Number  - observer latitude, degrees
  8:  Number  - aurora equatorward oval limit, degrees
  9:  Number  - limiting magnitude (NELM)
  10: Boolean - a meteor shower is active

Returns:
  Array [effectiveOn, reasonCode] - reasonCode is one of "FORCED", "ON",
  "SETTING", "NIGHT", "OVERCAST", "KP", "DAYTIME", "LATITUDE", "NELM",
  "NO_SHOWER".
*/

params [
    ["_feature", "stars", [""]],
    ["_settingOn", true, [false]],
    ["_forceOn", false, [false]],
    ["_sunElev", 0, [0]],
    ["_overcast", 0, [0]],
    ["_kpIndex", 0, [0]],
    ["_daytime", 12, [0]],
    ["_latDeg", 45, [0]],
    ["_ovalLimit", 60, [0]],
    ["_nelm", 6.5, [0]],
    ["_meteorActive", false, [false]]
];

if (!_settingOn) exitWith { [false, "SETTING"] };
if (_forceOn) exitWith { [true, "FORCED"] };

private _on = true;
private _reason = "ON";

if (_feature == "stars") then {
    if (_sunElev >= 0) then { _on = false; _reason = "NIGHT"; }
    else { if (_overcast >= 0.8) then { _on = false; _reason = "OVERCAST"; }; };
};

if (_feature == "meteors") then {
    if (_sunElev >= 0) then { _on = false; _reason = "NIGHT"; }
    else {
        if (_overcast >= 0.8) then { _on = false; _reason = "OVERCAST"; }
        else { if (!_meteorActive) then { _on = false; _reason = "NO_SHOWER"; }; };
    };
};

if (_feature == "aurora") then {
    if (_sunElev >= 0) then { _on = false; _reason = "NIGHT"; }
    else {
        if (_overcast >= 0.3) then { _on = false; _reason = "OVERCAST"; }
        else {
            if (_kpIndex <= 4) then { _on = false; _reason = "KP"; }
            else {
                if ((_daytime >= 6) && (_daytime <= 20)) then { _on = false; _reason = "DAYTIME"; }
                else { if (_latDeg <= _ovalLimit) then { _on = false; _reason = "LATITUDE"; }; };
            };
        };
    };
};

if (_feature == "milkyway") then {
    if (_sunElev >= 0) then { _on = false; _reason = "NIGHT"; }
    else {
        if (_overcast >= 0.8) then { _on = false; _reason = "OVERCAST"; }
        else { if (_nelm < 5.0) then { _on = false; _reason = "NELM"; }; };
    };
};

[_on, _reason]
