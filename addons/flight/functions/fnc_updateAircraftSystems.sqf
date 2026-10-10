#include "..\script_component.hpp"

/*
Schedule the four aircraft systems kernels for one elapsed mission-time
interval, on every local airframe.

WHY THIS FUNCTION EXISTS.  The fuel, engine, damage and status kernels each
manage one airframe for one interval.  Nothing called them, so the sourced
fuel rate never burned, the scripted engine readout never updated, the
damage layer never advanced and the status state was never published.  This
driver is the ONE scheduler.  It calls all four kernels for every local
airframe, once per handler tick.

THE ONE HANDLER.  XEH_postInit registers exactly ONE per-frame handler, and
that handler calls this driver.  There is no second handler and no per-kernel
handler.

LOCALITY, INCLUDING THE SERVER.  The driver runs on the machine that owns
each airframe.  The local test is true on the server for a server-owned AI
airframe, so a server-owned airframe burns fuel and never has infinite fuel.
This is the coupling that makes fuelConsumptionRate = 0 safe (the config
zero is emitted only for a class this driver covers).  A remote client never
writes another machine's state.  The binding locality is: run on local _veh
INCLUDING the server.  A dedicated server owns its AI airframes, so the
local test is true there and a server-owned airframe still burns fuel.

DETERMINISM.  The burn is a function of ELAPSED MISSION TIME, not of a
client-local tick count.  XEH_postInit passes the elapsed mission time since
the last tick (time - last time).  Mission time is synchronised, so every
machine that owns the same airframe computes the same burn from the same
systems row and the same elapsed interval.  The handler interval is
therefore free: it changes how often the state is written, never the total.

THE ENGINE COMMAND.  The commanded band follows the engine state: the
governed speed while airborne, idle on the ground.  The driver reads
isEngineOn and isTouchingGround and never feeds the kernel its own last
output.

Guards, each explicit:
  - A non-positive interval is refused.
  - The four kernels must be present, so a build without them does nothing.
  - Only a local Air object is scheduled.  A parachute is an Air object with
    no engine, tank or rotor, so it is refused.

Arguments:
  0:  _deltaTimeS (NUMBER) elapsed mission time since the last tick, s

Return Value: BOOL - true when the driver ran
Example: [1] call aee_flight_fnc_updateAircraftSystems
Public: No
*/

params [["_deltaTimeS", 0, [0]]];

if (_deltaTimeS <= 0) exitWith { false };

// The four kernels must be present. A build without them does nothing.
if (isNil QFUNC(updateFuelSystem) || {isNil QFUNC(updateEngineSystem)} || {isNil QFUNC(updateDamageSystem)} || {isNil QFUNC(updateStatusSystems)}) exitWith { false };

// Every local airframe, INCLUDING a server-owned AI airframe. The local test
// is the gate, and it is true on the server for a server-owned airframe.
private _aircraft = vehicles select {
    (alive _x) && {(_x isKindOf "Air")} && {!(_x isKindOf "ParachuteBase")} && {local _x}
};

{
    // The commanded band follows the engine state: the governed speed while
    // airborne, idle on the ground. The driver never feeds the kernel its own
    // last output.
    private _wanted = 0;
    if (isEngineOn _x) then {
        _wanted = if (isTouchingGround _x) then { 0 } else { 1 };
    };

    [_x, _deltaTimeS] call FUNC(updateFuelSystem);
    [_x, _wanted, _deltaTimeS] call FUNC(updateEngineSystem);
    [_x, _deltaTimeS] call FUNC(updateDamageSystem);
    [_x, _deltaTimeS] call FUNC(updateStatusSystems);
} forEach _aircraft;

true
