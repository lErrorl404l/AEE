#include "..\script_component.hpp"

/*
Author: AEE
Description: Computes atmospheric haze from relative humidity and dust suppression. High humidity adds haze; dust suppression removes it.
Arguments: None
Return Value: NUMBER: haze 0..1
Example: [] call aee_atmos_fnc_calculateHaze
Public: No
*/

private _humidity = missionNamespace getVariable [QEGVAR(core,currentHumidity), 50];
private _dustSuppression = missionNamespace getVariable [QEGVAR(core,dustSuppression), 0];

private _haze = 0.05 + ((_humidity / 100) * 0.3) - (_dustSuppression * 0.15);
_haze = _haze max 0 min 1;

missionNamespace setVariable [QEGVAR(core,currentHaze), _haze];

_haze
