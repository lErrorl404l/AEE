#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

// The per-frame loops below are client-side effects. The dedicated server
// has no local player and must not run them.
if (!hasInterface) exitWith {};

// Per-frame flight turbulence: a client-side force loop on nearby aircraft.
if (GVAR(flightTurbulence)) then {
    // 20 Hz, not every frame.  These were interval 0, so they ran on every
    // rendered frame (60+ Hz) doing engine calls (getPosATL, velocity,
    // vectorUp, surfaceType) and missionNamespace writes per vehicle.  A force
    // loop integrates fine at 20 Hz, and per-frame setVelocity is the jitter
    // case the terrain-drag doc warns about.
    GVAR(turbulencePFH) = [{
        BEGIN_COUNTER(applyFlightTurbulence);
call FUNC(applyFlightTurbulence);
END_COUNTER(applyFlightTurbulence);
    }, 0.05] call CBA_fnc_addPerFrameHandler;

    AEE_LOG_INFO("flight turbulence PFH started");
};

// Per-frame airframe density and icing load: the published lift ratio and the
// FAR 25 App C icing state become bounded lift/drag forces and an ice-mass
// delta.  The candidate list is cached on the same 1 s refresh the other
// loops use.  The applied function gates on local ownership.
if (GVAR(flightAeroPenalty)) then {
    GVAR(airframeVehicles) = [];
    GVAR(airframeRefresh) = -1;

    GVAR(airframeLoadPFH) = [{
        private _ref = [worldSize / 2, worldSize / 2, 0];
        private _player = call CBA_fnc_currentUnit;
        if (!isNil "_player" && {!isNull _player}) then {
            _ref = getPosATL _player;
        };

        if ((time - GVAR(airframeRefresh)) > 1) then {
            GVAR(airframeVehicles) = vehicles select {
                (alive _x) && {(_x isKindOf "Air")} && {!(_x isKindOf "ParachuteBase")} && {(_x distance _ref) < GVAR(airframeRadius)}
            };
            GVAR(airframeRefresh) = time;
        };

        {
            BEGIN_COUNTER(applyAirframeLoad);
            [_x] call FUNC(applyAirframeLoad);
            END_COUNTER(applyAirframeLoad);
        } forEach GVAR(airframeVehicles);
    }, 0.05] call CBA_fnc_addPerFrameHandler;

    AEE_LOG_INFO("airframe density/icing PFH started");
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

        // The distance test belongs HERE, not in the per-frame loop.  A list
        // built from `vehicles` with no radius holds every ground vehicle in
        // the world, so testing distance per frame ran a world scan every
        // frame.  Filtering at refresh leaves the loop below holding only
        // what is in range, and the refresh drops to 1 s so a vehicle that
        // arrives is picked up quickly.
        if ((time - GVAR(rolloverRefresh)) > 1) then {
            GVAR(rolloverVehicles) = vehicles select {
                (alive _x) && {!(_x isKindOf "Air")} && {(_x distance _ref) < GVAR(rolloverRadius)}
            };
            GVAR(rolloverRefresh) = time;
        };

        {
            BEGIN_COUNTER(applyRollover);
[_x] call FUNC(applyRollover);
END_COUNTER(applyRollover);
        } forEach GVAR(rolloverVehicles);
    }, 0.05] call CBA_fnc_addPerFrameHandler;

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

        // Same fix as the rollover loop above: the radius belongs in the
        // refresh, not in the per-frame test.
        if ((time - GVAR(terrainRefresh)) > 1) then {
            GVAR(terrainVehicles) = vehicles select {
                (alive _x) && {!(_x isKindOf "Air")} && {(_x distance _ref) < GVAR(terrainRadius)}
            };
            GVAR(terrainRefresh) = time;
        };

        {
            BEGIN_COUNTER(applyTerrainDrag);
[_x] call FUNC(applyTerrainDrag);
END_COUNTER(applyTerrainDrag);
        } forEach GVAR(terrainVehicles);
    }, 0.05] call CBA_fnc_addPerFrameHandler;

    AEE_LOG_INFO("terrain drag PFH started");
};

// Runtime vehicle coupling (W2): the computed surface physics drives the
// engine. Snow load changes the mass through setMass. A wet or icy surface
// removes grip through a force. Both run on the machine that owns the
// vehicle. The accretion mass changes slowly, so it runs on a 1 s tick. The
// grip force must be re-applied every frame, because addForce clears after
// each simulation step. The candidate list is cached and refreshed every
// second, like the loops above.
if (GVAR(vehicleCouplingEnabled)) then {
    GVAR(couplingVehicles) = [];
    GVAR(couplingRefresh) = -1;
    GVAR(couplingMassTick) = -1;

    GVAR(couplingPFH) = [{
        private _ref = [worldSize / 2, worldSize / 2, 0];
        private _player = call CBA_fnc_currentUnit;
        if (!isNil "_player" && {!isNull _player}) then {
            _ref = getPosATL _player;
        };

        if ((time - GVAR(couplingRefresh)) > 1) then {
            GVAR(couplingVehicles) = vehicles select {
                (alive _x) && {!(_x isKindOf "Air")} && {(_x distance _ref) < GVAR(terrainRadius)}
            };
            GVAR(couplingRefresh) = time;
        };

        private _applyMass = (time - GVAR(couplingMassTick)) > 1;
        if (_applyMass) then { GVAR(couplingMassTick) = time; };

        {
            if (_applyMass) then {
                BEGIN_COUNTER(applyAccretionMass);
                [_x] call FUNC(applyAccretionMass);
                END_COUNTER(applyAccretionMass);
            };
            BEGIN_COUNTER(applyGripLoss);
            [_x] call FUNC(applyGripLoss);
            END_COUNTER(applyGripLoss);
        } forEach GVAR(couplingVehicles);
    }, 0.05] call CBA_fnc_addPerFrameHandler;

    AEE_LOG_INFO("vehicle coupling PFH started");
};

// The applied airframe penalties were published with no consumer.  This state
// line is the consumer: it reports the four applied values under the mobility
// debug gate, which the operator forces with aee_mobility_logDebug or the
// global aee_core_logDebug.  It runs at 1 Hz, not the 20 Hz load rate, so a
// forced trace does not flood the RPT.  The file already returned on a
// dedicated server, so this block is client-only like the load loop.
if (GVAR(flightAeroPenalty)) then {
    [{
        [] call FUNC(logAirframeState);
    }, 1.0] call CBA_fnc_addPerFrameHandler;
};
