#include "..\script_component.hpp"

/*
Author: AEE
Description: Computes a deterministic, slowly changing weather quality factor from a seeded LCG. The raw seed changes every tick; a low-pass filter makes the progression drift slowly.
Arguments: None
Return Value: NUMBER: weather progression 0..1
Example: [] call aee_core_fnc_calculateSeededWeatherProgression
Public: No
*/

private _seed = [round (time * 60), 601] call FUNC(deterministicRandom);
private _prev = missionNamespace getVariable [QEGVAR(core,weatherProgression), 0.5];

private _progression = (_prev * 0.95) + (_seed * 0.05);

missionNamespace setVariable [QEGVAR(core,weatherProgressionSeed), _seed];
missionNamespace setVariable [QEGVAR(core,weatherProgression), _progression];

_progression
