#include "..\script_component.hpp"

/*
Player-initiated weather report — called from ACE3 interaction menu.
Delegates to calculateWeatherReport for the formatted string and renders
it via hintSilent.
*/

private _reportText = call FUNC(calculateWeatherReport);
if (isNil "_reportText") then {
    _reportText = "Weather data not available.";
};

hintSilent _reportText;
