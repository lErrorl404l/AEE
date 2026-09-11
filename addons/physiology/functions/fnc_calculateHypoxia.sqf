#include "..\script_component.hpp"

/*
Author: AEE
Description: Computes hypoxia risk from altitude above sea level. Risk starts at 3000 m and reaches 1.0 at 7000 m.
Arguments: None
Return Value: NUMBER: hypoxia risk 0..1
Example: [] call aee_physiology_fnc_calculateHypoxia
Public: No
*/

private _altASL = 0;
private _player = call CBA_fnc_currentUnit;
if (!isNil "_player") then {
    _altASL = (getPosASL _player) select 2;
};

private _risk = ((_altASL - 3000) / 4000) max 0 min 1;

missionNamespace setVariable [QEGVAR(core,currentHypoxiaRisk), _risk];

_risk
