#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"
#include "initSettings.inc.sqf"

if (is3DEN) exitWith {};

if (hasInterface) then {
    [{
        [] call FUNC(integrateKAT);
    }, 5] call CBA_fnc_addPerFrameHandler;

    // KAT overwrites kat_circulation_bloodGas every ~1 s vitals tick.
    // The ace_medical_handleUnitVitals event fires after each write, so
    // re-applying here keeps AEE's SpO2/PaO2 from being clobbered.  The
    // event fires only for local units, matching AEE's local player.
    ["ace_medical_handleUnitVitals", {
        params ["_unit"];
        if (_unit != player) exitWith {};
        [] call FUNC(integrateKAT);
    }] call CBA_fnc_addEventHandler;
};

ADDON = true;
