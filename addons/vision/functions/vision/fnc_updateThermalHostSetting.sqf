#include "..\..\script_component.hpp"

/*
Reconcile the DTV host driver with the current base channel setting.

Started at postInit and called from the setting's change callback.  Keeping
the branch in one place means postInit and a later setting change cannot
differ.
*/
if ((missionNamespace getVariable [QEGVAR(thermal,thermalBaseChannel), 0]) == 1) then {
    [] call FUNC(dtvHostStart);
} else {
    [] call FUNC(dtvHostStop);
};
