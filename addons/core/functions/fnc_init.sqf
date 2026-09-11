#include "..\script_component.hpp"

params [["_enabled", true, [true]]];

if (is3DEN) exitWith {};
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

// Detect base map biome once (first call caches in GVAR(biome))
[] call EFUNC(environmental,getBiome);

// Register the local environment PFH.
// Runs on every machine. Core atmospheric state is deterministic (position,
// mission time, engine weather), so all machines agree without publicVariable
// broadcast. Event FX vary cosmetically per machine.
private _interval = GVAR(updateInterval);
GVAR(updatePFH) = [{
    // Resolve position once so temp, pressure, and humidity all use the
    // exact same location — deterministic, communicable between players.
    private _player = call CBA_fnc_currentUnit;
    private _pos = if (isNil "_player") then { [] } else { getPosASL _player };
    [_pos] call FUNC(updateEnvironment);
}, _interval] call CBA_fnc_addPerFrameHandler;

diag_log format ["[AEE] Local environment PFH started. Base biome: %1", GVAR(biomeName)];
