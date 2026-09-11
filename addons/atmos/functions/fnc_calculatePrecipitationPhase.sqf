#include "..\script_component.hpp"

/*
Author: AEE
Description: Determines the precipitation phase (rain, sleet, snow, freezing rain) from air and surface temperature, and derives a snowfall rate from the engine rain rate.
Arguments: None
Return Value: STRING: precipitation phase ("rain", "sleet", "snow", "freezing_rain")
Example: [] call aee_atmos_fnc_calculatePrecipitationPhase
Public: No
*/

private _T = missionNamespace getVariable [QEGVAR(core,currentTemperature), 15];
private _surfaceT = missionNamespace getVariable [QEGVAR(core,surfaceTemperature), _T];
private _rainRate = rain;

// Freezing rain: warm air aloft, frozen surface
private _phase = switch (true) do {
    case ((_T > 0) && (_surfaceT < 0)): { "freezing_rain" };
    case (_T > 2):                       { "rain" };
    case (_T >= 0):                      { "sleet" };
    default                              { "snow" };
};

private _snowfallRate = if (_phase in ["snow", "sleet", "freezing_rain"]) then { _rainRate min 1 } else { 0 };

missionNamespace setVariable [QEGVAR(core,precipitationPhase), _phase];
missionNamespace setVariable [QEGVAR(core,snowfallRate), _snowfallRate];

_phase
