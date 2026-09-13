#include "script_component.hpp"

// Per-frame flight turbulence is a client-side effect. The dedicated server
// has no local player and must not run the force loop.
if (!hasInterface) exitWith {};
if (!GVAR(flightTurbulence)) exitWith {};

GVAR(turbulencePFH) = [{
    call FUNC(applyFlightTurbulence);
}, 0] call CBA_fnc_addPerFrameHandler;

AEE_LOG_INFO("flight turbulence PFH started");
