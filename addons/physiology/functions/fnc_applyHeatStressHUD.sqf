#include "..\script_component.hpp"

/*
Heat stress HUD warning via structured title text.

Reads QGVAR(dehydrationRisk) (0–1) produced by fn_calculateDehydrationRisk.
Gates on GVAR(environmentalEnabled).

When risk > 0.3, shows a persistent orange-coloured dehydration warning
using titleText with PLAIN DOWN mode (does not interrupt other hint
displays).  Clears the warning when risk drops back below 0.3, using a
flag (QGVAR(hudWarningActive)) to avoid spamming titleText every tick.
*/

if (!EGVAR(core,environmentalEnabled)) exitWith {};

private _risk   = missionNamespace getVariable [QGVAR(dehydrationRisk), 0];
private _active = missionNamespace getVariable [QGVAR(hudWarningActive), false];

if (_risk > 0.3) then {
    if (!_active) then {
        private _pct = floor (_risk * 100);
        titleText [
            format [
                "<t color='#ff6600' size='1.2'>DEHYDRATION WARNING</t><br/><t color='#cccccc' size='0.9'>Risk: %1%2</t>",
                _pct, "%"
            ],
            "PLAIN DOWN", 0.5, true, true
        ];
        missionNamespace setVariable [QGVAR(hudWarningActive), true];
    };
} else {
    if (_active) then {
        titleText ["", "PLAIN DOWN"];
        missionNamespace setVariable [QGVAR(hudWarningActive), false];
    };
};
