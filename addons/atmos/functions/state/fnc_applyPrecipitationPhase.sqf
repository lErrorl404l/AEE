#include "..\..\script_component.hpp"

/*
Precipitation phase to the engine rain renderer (issue: unused weather levers).

`setRain rainParams` (syntax 2, Arma 3 2.08) sets the LOCAL rain particle
parameters.  It does not change the rain density, which stays with the server
write of `setRain value` in FUNC(applyEngineWeather).  The array is the 17
element RainParticles list and element 15 is the `snow` flag (command DB
`setRain` syntax 2 and `rainParams`, acemod/arma3-wiki v2.22).  With `snow`
true the engine draws the same particle system with the snowflake texture.
This is the ONLY precipitation-phase render path: `setRain value` (syntax 1)
carries no phase, and the engine cannot draw rain and snow at once.

AEE computes the phase from the wet-bulb temperature in
FUNC(calculatePrecipitationPhase) and publishes `aee_core_precipitationPhase`.
This bridge turns that phase into the particle form.

ONE WRITE PER PHASE CHANGE, not per tick: the engine holds the params until
the next call, and the phase changes over minutes.  `setRain []` (the empty
array) resets the params to the config default, so every non-snow phase
resets rather than leaving a stale snow form.

TEXTURE: `a3\data_f\snowflake4_ca.paa`, the shipped 4-flake atlas the command
DB example names (commands/setRain.yml).  FUNC(calculateSnowRainParams) holds
the full array.

Locality: the params are client-side and are ignored on a dedicated server
(command DB `setRain` syntax 2), so this runs once per client.

Reads:  aee_core_precipitationPhase
Sets:   engine rain particle params (setRain [rainParams]), client-local
Example: [] call aee_atmos_fnc_applyPrecipitationPhase;
Public: No
*/

if (!hasInterface) exitWith {};

private _phase = missionNamespace getVariable [QEGVAR(core,precipitationPhase), "rain"];
if !(_phase isEqualType "") then { _phase = "rain"; };

// The engine renders one precipitation form.  Snow draws the snowflake form;
// rain, sleet and freezing rain reset to the config form.
private _snow = (_phase == "snow");

// The params persist until the next call, so write only on a change.
private _written = missionNamespace getVariable [QGVAR(rainPhaseWritten), ""];
if (_written isEqualTo _phase) exitWith {};
missionNamespace setVariable [QGVAR(rainPhaseWritten), _phase];

if (_snow) then {
    setRain (call FUNC(calculateSnowRainParams));
} else {
    setRain [];   // reset to the config RainParticles (command DB `rainParams`)
};
