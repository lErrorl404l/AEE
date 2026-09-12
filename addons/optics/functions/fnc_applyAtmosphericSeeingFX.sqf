#include "..\script_component.hpp"

/*
Atmospheric seeing / long-range shimmer post-process.

Reads QGVAR(atmosphericSeeing) (0.1–1.0) produced by
fnc_calculateAtmosphericSeeing.  Lower = better seeing.
Gates on EGVAR(core,opticsEnabled).

Computes and stores the seeing ChromAberration intensity in
QGVAR(seeingChroma); application is handled by fnc_managePostProcess.

Reference values:
  • Good seeing (0.2): barely perceptible — skip the effect
  • Moderate seeing (0.5): mild chromatic fringing at edges
  • Poor seeing (0.8+): visible shimmer on distant objects
  • Night seeing is naturally better (seeing * 0.3 in calculator)

This is distinct from heat shimmer (vehicle/engine) which uses
the same effect but driven by different state.
*/

if (!EGVAR(core,opticsEnabled)) exitWith {};

private _seeing    = missionNamespace getVariable [QGVAR(atmosphericSeeing), 0.2];
private _player    = call CBA_fnc_currentUnit;
if (isNil "_player" || !alive _player || cameraOn != _player) exitWith {};
if !(_seeing isEqualType 0) then { _seeing = 0.2; };

// Scale: 0.35 = 0, 1.0 = 0.02 (subtle but visible at distance)
private _chromatic = linearConversion [0.35, 1, _seeing, 0, 0.02, true];

// Store 0 below moderate seeing so the arbiter can fade the effect out
missionNamespace setVariable [QGVAR(seeingChroma), [0, _chromatic] select (_seeing > 0.35)];
