#include "script_component.hpp"

// Standalone access to the AEE actions. The same actions are exposed to the
// ACE3 interaction menu by compat_ace3; these keybinds work without ACE3.
["AEE", "WeatherReport", [LLSTRING(WeatherReport), "Show the AEE weather report"], {
    call FUNC(openWeatherReport);
}, {}] call CBA_fnc_addKeybind;

["AEE", "Altimeter", [LLSTRING(Altimeter), "Show the AEE altimeter"], {
    call FUNC(openAltimeter);
}, {}] call CBA_fnc_addKeybind;
