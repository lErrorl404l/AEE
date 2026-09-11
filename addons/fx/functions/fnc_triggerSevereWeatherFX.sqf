#include "..\script_component.hpp"

/*
Post-processing effects for severe weather (sandstorm, blowing snow, dust devil).

Reads QGVAR(currentSandstorm), QGVAR(currentBlowingSnow), QGVAR(currentDustDevil).
Gates on GVAR(atmosphericEventsEnabled).  Applies colour correction + blur
for active severe weather, fades both out when none active.

Sets: nothing (side effect only — applies/removes ppEffects)
*/

if (!EGVAR(core,atmosphericEventsEnabled)) exitWith {};

private _sandstorm   = missionNamespace getVariable [QEGVAR(core,currentSandstorm), 0];
private _blowingSnow = missionNamespace getVariable [QEGVAR(core,currentBlowingSnow), 0];
private _dustDevil   = missionNamespace getVariable [QEGVAR(core,currentDustDevil), 0];
private _windSpeed   = vectorMagnitude wind;

if (_sandstorm > 0 || _dustDevil > 0) then {
    "ColorCorrections" ppEffectEnable true;
    "ColorCorrections" ppEffectAdjust [
        0.8, 0.6, 0.0,                        // brightness, contrast, offset
        [0.3, 0.25, 0.15, 0.0],              // tint (sandy)
        [1.0, 0.85, 0.6, 0.5],               // desaturation mix
        [0.5, 0.5, 0.5, 0.0]                 // no extra colour
    ];
    "ColorCorrections" ppEffectCommit 2;

    "DynamicBlur" ppEffectEnable true;
    "DynamicBlur" ppEffectAdjust [_windSpeed / 10];
    "DynamicBlur" ppEffectCommit 2;
    } else {
        if (_blowingSnow > 0) then {
        "ColorCorrections" ppEffectEnable true;
        "ColorCorrections" ppEffectAdjust [
            1.0, 1.0, 0.0,
            [0.0, 0.0, 0.0, 0.0],
            [0.6, 0.65, 0.7, 0.5],              // blue-white desaturation
            [0.5, 0.5, 0.5, 0.0]
        ];
        "ColorCorrections" ppEffectCommit 2;

        "DynamicBlur" ppEffectEnable true;
        "DynamicBlur" ppEffectAdjust [_windSpeed / 10];
        "DynamicBlur" ppEffectCommit 2;
    } else {
        // Fade out both effects
        "ColorCorrections" ppEffectAdjust [1, 1, 0, [0,0,0,0], [1,1,1,1], [0,0,0,0]];
        "ColorCorrections" ppEffectCommit 5;

        "DynamicBlur" ppEffectAdjust [0];
        "DynamicBlur" ppEffectCommit 5;

        // Disable after fade completes
        [{
            "ColorCorrections" ppEffectEnable false;
            "DynamicBlur" ppEffectEnable false;
        }, [], 5] call CBA_fnc_waitAndExecute;
    };
};
