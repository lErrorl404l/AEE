#include "script_component.hpp"
#include "\z\aee\addons\lib\script_debug.hpp"

AEE_MODULE_POST_INIT

// ─── Aircraft systems driver ────────────────────────────────────────────
// ONE per-frame handler schedules the fuel, engine, damage and status
// kernels. It runs on the machine that owns each airframe, INCLUDING the
// server, so a server-owned AI airframe burns fuel and never has infinite
// fuel. The handler passes the elapsed MISSION TIME since the last tick,
// not a client-local tick count, so every machine that owns the airframe
// computes the same burn from the same systems row. This block sits ABOVE
// the hasInterface guard on purpose: the driver must run on the dedicated
// server too.
GVAR(aircraftSystemsLastTime) = -1;
GVAR(aircraftSystemsPFH) = [{
    private _now = time;
    private _last = GVAR(aircraftSystemsLastTime);
    if (_last < 0) then { _last = _now; };
    private _delta = _now - _last;
    GVAR(aircraftSystemsLastTime) = _now;
    if (_delta > 0) then {
        BEGIN_COUNTER(updateAircraftSystems);
        [_delta] call FUNC(updateAircraftSystems);
        END_COUNTER(updateAircraftSystems);
    };
}, 1.0] call CBA_fnc_addPerFrameHandler;

AEE_LOG_INFO("aircraft systems PFH started");

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

// The applied airframe penalties were published with no consumer.  This state
// line is the consumer: it reports the four applied values under the flight
// debug gate, which the operator forces with aee_flight_logDebug or the
// global aee_core_logDebug.  It runs at 1 Hz, not the 20 Hz load rate, so a
// forced trace does not flood the RPT.  The file already returned on a
// dedicated server, so this block is client-only like the load loop.
if (GVAR(flightAeroPenalty)) then {
    [{
        [] call FUNC(logAirframeState);
    }, 1.0] call CBA_fnc_addPerFrameHandler;
};
