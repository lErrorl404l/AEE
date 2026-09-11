#include "script_component.hpp"

ADDON = false;

#include "XEH_PREP.hpp"

if (is3DEN) exitWith {};

[] call FUNC(integrateACRE2);

ADDON = true;
