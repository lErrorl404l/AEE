#include "script_component.hpp"

if (!isServer) exitWith {};

// Check if AEE is enabled
if (!GVAR(enabled)) exitWith {};

// Get current month (1-12) from system date
private _month = date select 1;

// Get biome code
private _biome = GVAR(biome);
if (isNil "_biome" || _biome == "") then {
    call FUNC(getBiome);
    _biome = GVAR(biome);
};

// Run individual updates
[_biome, _month] call FUNC(updateTemperature);
[_biome, _month] call FUNC(updatePressure);
[_biome, _month] call FUNC(updateHumidity);
[] call FUNC(updateWind);

// Calculate air density from the current state
call FUNC(calculateAirDensity);

// Diagnostic logging
if (GVAR(diagnostic)) then {
    [] call FUNC(diagnostic);
};
