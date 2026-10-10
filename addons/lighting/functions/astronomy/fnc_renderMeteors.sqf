#include "..\..\script_component.hpp"

/*
 * Dynamic meteor renderer (issue #122).
 *
 * Registers the client-side meteor worker once.  On a real shower's active
 * night the worker draws meteors from the shower radiant at the IMO ZHR,
 * reduced by the radiant altitude and the current limiting magnitude.  Each
 * meteor is a local light emitter with a particle trail; the mechanism is
 * copied from the falling-star mod (see fnc_updateMeteors).
 *
 * Registered once, idempotently (the isNil guard is required by the
 * validate_cba gate).  Client-only: the trail is cosmetic and needs no
 * server authority.
 */

if (!hasInterface) exitWith {};
if (!isNil QGVAR(meteorPFH)) exitWith {};

missionNamespace setVariable [QGVAR(meteors), []];

GVAR(meteorPFH) = [FUNC(updateMeteors), METEOR_TICK] call CBA_fnc_addPerFrameHandler;
AEE_LOG_INFO("meteor: worker PFH registered");
