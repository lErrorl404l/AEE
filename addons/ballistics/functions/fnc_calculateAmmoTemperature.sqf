#include "..\script_component.hpp"

/*
ACE3 ammunition temperature is per-weapon per-unit, not a global mission variable:
  unit getVariable ["ace_overheating_weapon_ammoTemp", ambientTemperature select 0]
Setting ace_weather_ammoTemp as a global has no effect on ACE3.
This function is retained as a no-op stub in case a future integration path emerges.
*/
