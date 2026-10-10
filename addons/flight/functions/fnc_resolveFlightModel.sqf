#include "..\script_component.hpp"

/*
Resolve an airframe to the path its turbulence takes.

The engine has no "AdvancedFlightModel" class.  A vanilla config has zero
hits for that name, so the old gate in fnc_applyFlightTurbulence never
matched and the addForce branch was dead code.  The engine exposes the
advanced model two ways:

  - difficultyEnabledRTD — the scenario-global real-time-data flag.  It is
    true when the advanced model is forced (forceRotorLibSimulation) or the
    client option selects it.
  - RotorLibHelicopterProperties — the class a rotor-lib airframe carries.
    It is present whenever the airframe runs the rotor-lib model, whatever
    the scenario flag says.

This kernel is a pure truth table over those two booleans, so the test
harness can execute it.  The caller owns the two engine reads.  A force is
a PhysX change and only integrates on the advanced or rotor-lib model; the
simple model keeps the velocity-delta path.

Arguments:
  0: BOOL - difficultyEnabledRTD
  1: BOOL - the airframe has RotorLibHelicopterProperties

Return Value: NUMBER - 1 when the physical force path applies, 0 otherwise
Example: [difficultyEnabledRTD, true] call aee_flight_fnc_resolveFlightModel
Public: No
*/

params [
    ["_rtd", false, [false]],
    ["_rotorLib", false, [false]]
];

// Either the scenario forced the advanced model, or the airframe is a
// rotor-lib helicopter.  The physical path applies in both cases.
if (_rtd || _rotorLib) exitWith { 1 };

0
