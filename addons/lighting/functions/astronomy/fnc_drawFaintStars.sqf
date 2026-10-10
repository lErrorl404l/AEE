#include "..\..\script_component.hpp"

/*
Faint star bulk Draw3D worker.

The light-emitter path renders only the bright stars, because the engine caps
concurrent dynamic lights; STAR_LIGHT_MAX_MAG is that ceiling.  This worker
draws the catalogued stars fainter than the ceiling with drawLine3D, so the
faint field appears without consuming a dynamic light.  The count is capped at
FAINT_STAR_MAX to bound the per-frame draw calls.

fnc_getStarCatalog already excludes stars below the horizon and fainter than
the NELM, and fnc_starLightsSync bypasses this layer on disable, daylight or
solid overcast by leaving the visible set empty.
*/

private _stars = missionNamespace getVariable [QGVAR(visibleStars), []];
private _nelm = missionNamespace getVariable [QGVAR(effectiveNelm), 6.5];
if !(_nelm isEqualType 0) then { _nelm = 6.5; };

private _eyePos = ((call CBA_fnc_currentUnit) call EFUNC(core,getEyeState)) select 0;
private _drawn = 0;

// The star brightness model publishes a 0..1 render scale; it multiplies each
// star's alpha in fnc_starMagnitude.
private _brightnessScale = missionNamespace getVariable [QGVAR(starBrightnessCoefficient), 1];
if !(_brightnessScale isEqualType 0) then { _brightnessScale = 1; };

{
    if (_drawn >= FAINT_STAR_MAX) exitWith {};
    private _altDeg = _x select 1;
    private _azDeg = _x select 2;
    private _vmag = _x select 3;
    if (_vmag <= STAR_LIGHT_MAX_MAG) then { continue; };
    if (_vmag > _nelm) then { continue; };
    if (_altDeg < 0) then { continue; };
    private _dir = [_altDeg, _azDeg] call FUNC(starDirection);
    private _mag = [_vmag, _brightnessScale] call FUNC(starMagnitude);
    private _p1 = _eyePos vectorAdd (_dir vectorMultiply FAINT_STAR_RADIUS);
    private _p2 = _eyePos vectorAdd (_dir vectorMultiply (FAINT_STAR_RADIUS + 1));
    drawLine3D [_p1, _p2, [0.85, 0.88, 1.0, (_mag select 1) * 0.8]];
    _drawn = _drawn + 1;
} forEach _stars;

missionNamespace setVariable [QGVAR(faintStarCount), _drawn];
