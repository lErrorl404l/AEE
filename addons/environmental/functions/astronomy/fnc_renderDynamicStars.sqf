#include "..\..\script_component.hpp"

/*
 * Dynamic starfield renderer (issue #122).
 *
 * Registers the client-side starfield worker once.  Arma's night sky is a
 * static baked texture; the worker draws the computed star catalog
 * (aee_environmental_visibleStars: [name, altDeg, azDeg, vmag], altitude-sorted
 * and NELM-gated by fnc_getStarCatalog) so the field follows the same
 * physics as the rest of the optics chain.
 *
 * Each star is a local "#lightpoint" whose FLARE is the visible point
 * (BIKI Light Source Tutorial): setLightUseFlare + setLightFlareSize +
 * setLightFlareMaxDistance + a non-black setLightColor.  setLightAmbient
 * stays black so the field does not illuminate the ground.  fnc_starLightsSync
 * owns the per-tick reconcile.
 *
 * Registered once, idempotently (the isNil guard is required by the
 * validate_cba gate).
 */

if (!hasInterface) exitWith {};
if (!isNil QGVAR(dynamicStarsPFH)) exitWith {};

missionNamespace setVariable [QGVAR(starLights), []];
missionNamespace setVariable [QGVAR(faintStarCount), 0];

GVAR(dynamicStarsPFH) = [FUNC(starLightsSync), 0.25] call CBA_fnc_addPerFrameHandler;
// The faint bulk (stars the light-emitter cap drops) is drawn by a separate
// Draw3D handler, so the light budget is not consumed.
if (isNil QGVAR(faintStarsEH)) then {
    GVAR(faintStarsEH) = addMissionEventHandler ["Draw3D", { call FUNC(drawFaintStars) }];
};
AEE_LOG_INFO("starfield: light-emitter PFH registered");
