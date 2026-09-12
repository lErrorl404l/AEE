#include "..\script_component.hpp"

/*
Atmospheric seeing / long-range shimmer post-process.

Reads QGVAR(atmosphericSeeing) (0.1–1.0) produced by
fnc_calculateAtmosphericSeeing.  Lower = better seeing.
Gates on EGVAR(core,opticsEnabled).

Applies subtle ChromAberration to simulate refractive turbulence
when viewing distant targets through thermal mixing layers.

Reference values:
  • Good seeing (0.2): barely perceptible — skip the effect
  • Moderate seeing (0.5): mild chromatic fringing at edges
  • Poor seeing (0.8+): visible shimmer on distant objects
  • Night seeing is naturally better (seeing * 0.3 in calculator)

This is distinct from heat shimmer (vehicle/engine) which uses
the same ppEffect but driven by different state.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _seeing    = missionNamespace getVariable [QGVAR(atmosphericSeeing), 0.2];
private _player    = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};

private _active = missionNamespace getVariable [QGVAR(seeingFXActive), false];

// Only apply above moderate seeing — good seeing is imperceptible
if (_seeing > 0.35) then {
    if (!_active) then {
        "ChromAberration" ppEffectEnable true;
        missionNamespace setVariable [QGVAR(seeingFXActive), true];
    };

    // Scale: 0.35 = 0, 1.0 = 0.02 (subtle but visible at distance)
    private _chromatic = linearConversion [0.35, 1, _seeing, 0, 0.02, true];
    "ChromAberration" ppEffectAdjust [_chromatic, _chromatic, true];
    "ChromAberration" ppEffectCommit 2;
} else {
    if (_active) then {
        "ChromAberration" ppEffectAdjust [0, 0, true];
        "ChromAberration" ppEffectCommit 1;

        [{
            "ChromAberration" ppEffectEnable false;
        }, [], 1.5] call CBA_fnc_waitAndExecute;

        missionNamespace setVariable [QGVAR(seeingFXActive), false];
    };
};
