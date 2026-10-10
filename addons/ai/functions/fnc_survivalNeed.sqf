#include "..\script_component.hpp"

/*
Survival need bridge (will to live).

Reads the survival pressure the physiology model publishes and writes it as
the agent's substrate need.  The reusable substrate already reads the anchor
variable QGVAR(need) in fnc_aiTick, so this bridge reuses that decision path
rather than adding a second decision model.

The substrate calls this only for an agent that carries the
QGVAR(survivalDriven) flag, so the bridge is inert until a caller marks the
agent.  This mirrors the QGVAR(ecologyDriven) flag the wildlife ecology uses.

Reads:   QEGVAR(physiology,survivalPressure)  0..1
Writes:  QGVAR(need) on the anchor
Returns: Number - the survival pressure, 0..1
*/

params [["_anchor", objNull, [objNull, []]]];

private _pressure = missionNamespace getVariable [QEGVAR(physiology,survivalPressure), 0];
if !(_pressure isEqualType 0) then { _pressure = 0; };
_pressure = (_pressure max 0) min 1;

if ((_anchor isEqualType objNull) && {!isNull _anchor}) then {
    _anchor setVariable [QGVAR(need), _pressure];
};

_pressure
