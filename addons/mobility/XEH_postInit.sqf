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

// Per-frame off-road terrain drag (#117): slow a vehicle on rough or soft
// ground with a force opposing its motion.  The terrain factor is a pure
// function of the surface and the shared ground state, so every machine
// computes the same value; the force is applied on the machine that owns
// the vehicle.  The candidate list is shared with the rollover loop.
if (GVAR(terrainDragEnabled)) then {
    GVAR(terrainVehicles) = [];
    GVAR(terrainRefresh) = -1;

    GVAR(terrainDragPFH) = [{
        private _ref = [worldSize / 2, worldSize / 2, 0];
        private _player = call CBA_fnc_currentUnit;
        if (!isNil "_player" && {!isNull _player}) then {
            _ref = getPosATL _player;
        };

        if ((time - GVAR(terrainRefresh)) > 5) then {
            GVAR(terrainVehicles) = vehicles select {
                (alive _x) && {!(_x isKindOf "Air")}
            };
            GVAR(terrainRefresh) = time;
        };

        {
            if ((_x distance _ref) < GVAR(terrainRadius)) then {
                [_x] call FUNC(applyTerrainDrag);
            };
        } forEach GVAR(terrainVehicles);
    }, 0] call CBA_fnc_addPerFrameHandler;

    AEE_LOG_INFO("terrain drag PFH started");
};
