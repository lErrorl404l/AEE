#include "script_component.hpp"

// The per-frame loops below are client-side effects. The dedicated server
// has no local player and must not run them.
if (!hasInterface) exitWith {};

// Per-frame flight turbulence: a client-side force loop on nearby aircraft.
if (GVAR(flightTurbulence)) then {
    GVAR(turbulencePFH) = [{
        call FUNC(applyFlightTurbulence);
    }, 0] call CBA_fnc_addPerFrameHandler;

    AEE_LOG_INFO("flight turbulence PFH started");
};

// Per-frame vehicle rollover: tips a vehicle whose sustained lateral
// acceleration exceeds its Static Stability Factor threshold (#108).  The
// vehicle list is cached and refreshed, so the loop does not scan the world
// every frame.
if (GVAR(rolloverEnabled)) then {
    GVAR(rolloverVehicles) = [];
    GVAR(rolloverRefresh) = -1;

    GVAR(rolloverPFH) = [{
        private _ref = [worldSize / 2, worldSize / 2, 0];
        private _player = call CBA_fnc_currentUnit;
        if (!isNil "_player" && {!isNull _player}) then {
            _ref = getPosATL _player;
        };

        // Refresh the candidate list every 5 s, as the turbulence loop does.
        if ((time - GVAR(rolloverRefresh)) > 5) then {
            GVAR(rolloverVehicles) = vehicles select {
                (alive _x) && {!(_x isKindOf "Air")}
            };
            GVAR(rolloverRefresh) = time;
        };

        {
            if ((_x distance _ref) < GVAR(rolloverRadius)) then {
                [_x] call FUNC(applyRollover);
            };
        } forEach GVAR(rolloverVehicles);
    }, 0] call CBA_fnc_addPerFrameHandler;

    AEE_LOG_INFO("vehicle rollover PFH started");
};
