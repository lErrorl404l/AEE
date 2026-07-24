#include "script_component.hpp"

params [["_enabled", true, [true]]];

if (!isServer) exitWith {};
if (!_enabled) exitWith {
    if (!isNil QGVAR(updatePFH)) then {
        [GVAR(updatePFH)] call CBA_fnc_removePerFrameHandler;
        GVAR(updatePFH) = nil;
    };
};

// Remove existing PFH first
if (!isNil QGVAR(updatePFH)) then {
    [GVAR(updatePFH)] call CBA_fnc_removePerFrameHandler;
};

// Detect biome on init
call FUNC(getBiome);

// Register the update PFH
private _interval = GVAR(updateInterval);
GVAR(updatePFH) = [{
    [] call FUNC(updateEnvironment);
}, _interval] call CBA_fnc_addPerFrameHandler;

diag_log text "[AEE] Core initialized. Biome: " + (GVAR(biomeName));
