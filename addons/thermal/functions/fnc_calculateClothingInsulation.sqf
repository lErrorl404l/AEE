#include "..\script_component.hpp"

/*
Author: AEE
Description: Publishes the clothing insulation factor from the aee_core_clothingInsulation CBA setting. Consumed by hypothermia and heat-stress models.
Arguments: None
Return Value: NUMBER: insulation factor 0.5..2.0
Example: [] call aee_thermal_fnc_calculateClothingInsulation
Public: No
*/

private _factor = missionNamespace getVariable [QEGVAR(core,clothingInsulation), 1.0];

missionNamespace setVariable [QEGVAR(core,clothingInsulationFactor), _factor];

_factor
